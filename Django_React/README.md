# CustomerClub — Kiosk (Django + React)

Public in-store app: Django REST API (`backend/`) and React (Vite) touchscreen UI (`frontend/`).

Monorepo root docs: [../README.md](../README.md) · [../docs/DOCUMENTATION.md](../docs/DOCUMENTATION.md) · [../docs/DATABASE.md](../docs/DATABASE.md)

**Management** (catalog, offers, staff UI) lives in `../Django_React_management/`. The kiosk reads business data from the management integration API when `STATELESS_KIOSK=true` (default).

## NFC Authentication Setup

This project supports **NFC-based authentication** in two ways:

- **Browser-based NFC/Serial scanning** (recommended for most use-cases)
  - **Web NFC** (`NDEFReader`) on Android Chrome
  - **Web Serial** (`navigator.serial`) on Desktop Chrome/Edge + USB/COM NFC readers
  - Backend endpoints:
    - `POST /api/v1/user/nfc/login/` → returns JWT tokens + user profile
    - `POST /api/v1/user/nfc/register/` → links a tag to an authenticated user
    - `POST /api/v1/user/nfc/unlink/` → deactivates a tag
    - `GET /api/v1/user/nfc/status/` → returns tag list/status

- **Bridge script flow** (for readers that only expose a COM port to the OS)
  - See `docs/NFC_LOGIN.md` and `nfc_bridge.py`.
  - Backend endpoints:
    - `POST /api/v1/nfc-login/` → one-time token + login URL
    - `POST /api/v1/nfc-complete/` → exchanges one-time token for user profile

### System requirements

#### Windows (USB Serial readers)
- Many USB serial readers require drivers (depending on the USB-UART chip):
  - **CH340/CH341**: WCH CH341/CH340 serial driver (often used by low-cost readers) — `https://www.wch.cn/downloads/CH341SER_EXE.html`
  - **CP2102**: Silicon Labs CP210x driver — `https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers`
- Verify in **Device Manager** that a COM port is created (e.g. `COM9`).

#### macOS
- Most USB CDC ACM devices work without extra drivers.
- If the device does not appear, check **System Information → USB** and vendor driver notes.

#### Linux
- Packages that are commonly needed for smartcard/NFC stacks:

```bash
sudo apt install libusb-1.0-0 pcscd pcsc-tools
```

- Check devices with:

```bash
lsusb
```

### Supported NFC readers (examples)
- **ACR122U** (PC/SC)
- **PN532-based** USB/UART modules (commonly used in kiosks)
- USB/Serial “UID-only” readers that output tag UID over COM/tty

### Supported tag types (examples)
- MIFARE Classic (1K/4K)
- NTAG21x (e.g. NTAG213 / NTAG215 / NTAG216)

### UID format expectations
- The system expects a **hex string UID** in one of these lengths:
  - **8** hex chars (4 bytes)
  - **14** hex chars (7 bytes)
  - **20** hex chars (10 bytes)

Example: `04a1b2c3` or `04a1b2c3d4e5f6` (case-insensitive).

> Note: the backend **stores a hashed UID** (SHA256) in `NFCTag.uid`. The raw UID is never stored.

## Environment Variables

### Backend (Django)
These are the NFC-related settings used by the backend.

#### Feature/runtime settings
- **Requested (human-friendly) names**
  - `NFC_ENABLED=true`
  - `NFC_SCAN_TIMEOUT=30` (seconds)
  - `NFC_MAX_FAILED_ATTEMPTS=5`
  - `NFC_LOCKOUT_DURATION=30` (minutes)
  - `NFC_SERIAL_BAUD_RATE=9600`

#### Current Django settings keys (implementation details)
The current implementation uses the following setting names internally:
- **Tag lockout**
  - `NFC_TAG_MAX_FAILED_ATTEMPTS` (default: `5`)
  - `NFC_TAG_LOCK_SECONDS` (default: `1800` recommended for 30 minutes)
- **Login rate limit**
  - `NFC_LOGIN_RATE_WINDOW` (seconds, default: `60`)
  - `NFC_LOGIN_RATE_MAX` (requests per window, default: `30`)
- **Bridge script**
  - `NFC_BRIDGE_SECRET`
  - `NFC_LOGIN_TOKEN_TTL` (seconds)
  - `FRONTEND_BASE_URL`

If you set the user-facing variables (`NFC_MAX_FAILED_ATTEMPTS`, `NFC_LOCKOUT_DURATION`, etc.), make sure you map them into the Django settings (or add a mapping layer) so the backend uses them.

### Frontend (Vite)
See `frontend/.env.example`:
- `VITE_NFC_ENABLED=true`
- `VITE_NFC_TIMEOUT_MS=30000`
- `VITE_NFC_MAX_RETRIES=2`
- `VITE_NFC_SERIAL_BAUD=9600`

## Installation Steps

1. Start **management** API first and align `MANAGEMENT_SERVICE_API_KEY` in both `.env` files (see root documentation).
2. **Install OS-specific NFC drivers** if using USB readers (Windows: CH340/CP2102 if required).
3. **Backend**:

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 8001
```

   For faster local boot, keep `ENABLE_OPENAPI=false` in `.env` (default). OpenAPI/Swagger: set `ENABLE_OPENAPI=true` and visit `/api/v1/schema/swagger/`.

4. **Frontend**:

```bash
cd frontend
npm install
npm run dev
```

   Dev URLs: API `http://127.0.0.1:8001/`, SPA `http://127.0.0.1:5002/` (Vite port in `frontend/vite.config.js`).

5. **Configure environment variables**
   - Backend: `backend/.env` (see `backend/.env.example`)
   - Frontend: `frontend/.env` (see `frontend/.env.example`)

6. **Browser setup notes**
   - **Android**: Chrome with NFC enabled (Web NFC support)
   - **Desktop**: Chrome/Edge with Web Serial support
   - Production typically requires **HTTPS** for Web NFC/Web Serial permissions.

### UI note

NFC login/register is on the **auth screens**. The **products / offers** screen does not include an NFC management button; use login flow or API endpoints to link tags.

## Testing

### Test tags / scenarios
- Valid UID (8/14/20 hex)
- Unknown UID (should return generic invalid credentials)
- Locked tag (5 consecutive failures → locked response)
- Rate limit exceeded (429)
- Register/link a tag (authenticated)
- Unlink a tag (authenticated, owned vs not owned)

### Backend endpoint testing (curl examples)

#### NFC login (no auth)

```bash
curl -X POST "http://127.0.0.1:8001/api/v1/user/nfc/login/" \
  -H "Content-Type: application/json" \
  -d "{\"uid\":\"04a1b2c3\"}"
```

#### NFC status (auth required)

```bash
curl "http://127.0.0.1:8001/api/v1/user/nfc/status/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Testing without hardware
- You can still test backend endpoints by manually providing `uid` values (as hex strings).
- If you need a mock scanning mode, you can temporarily type UIDs into the legacy manual UID input (still present in the login screen).

## Troubleshooting

- **Scanner not detected**
  - Windows: Device Manager → Ports (COM & LPT)
  - Linux: `lsusb`
- **Permission denied**
  - Browser site settings → allow NFC/Serial
  - Web Serial requires a user gesture (button click) to request the port
- **Tag not reading**
  - Verify tag type compatibility (NTAG vs MIFARE)
  - Try a different tag or reader
- **CORS errors**
  - Backend uses `django-cors-headers` and currently allows all origins in settings; verify this for production.

### Common error codes
- **400** `invalid uid format` → UID must be hex length 8/14/20
- **401** `invalid credentials` → unknown/inactive tag (generic, no enumeration)
- **401** `authentication required` → login/register/status/unlink requires JWT
- **409** `uid already linked` → tag belongs to another account
- **423** `nfc_tag_locked` → too many attempts; check `retry_after`
- **429** `rate_limited` → too many requests; check `retry_after`

