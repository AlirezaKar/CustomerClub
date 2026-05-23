# NFC-based login

This project supports logging in by tapping an NFC card. Because the browser cannot access the NFC reader directly (e.g. COM port), a **bridge script** runs on the PC and forwards the card UID to the Django backend.

## Architecture

1. **NFC reader** → connected to PC (e.g. COM9).
2. **Bridge script** (`nfc_bridge.py`) → reads UID from serial port, POSTs to Django.
3. **Django** → finds user by `card_uid`, creates a one-time token, returns a login URL.
4. **Bridge** → opens that URL in the browser.
5. **Frontend** → sees `?nfc_token=...` in the URL, exchanges token for user profile and logs in.

## Setup

### 1. Register the card in Django

Ensure the user has a `card_uid` set (same as the UID your reader sends). You can set it in signup or later in admin / “update user properties”. The backend matches `User.card_uid` to the UID from the reader.

### 2. Backend (Django)

- Endpoints are already mounted:
  - `POST /api/v1/nfc-login/` — called by the bridge with `uid` (and optional `secret`).
  - `POST /api/v1/nfc-complete/` — called by the frontend with `token` to get the user profile.
- Optional in `.env`:
  - `NFC_BRIDGE_SECRET` — if set, the bridge must send this (body `secret` or header `X-NFC-Bridge-Secret`).
  - `NFC_LOGIN_TOKEN_TTL` — lifetime of the one-time token in seconds (default 60).
  - `FRONTEND_BASE_URL` — base URL of the React app (default `http://127.0.0.1:5002`).

### 3. Bridge script

From the project root:

```bash
pip install -r requirements-nfc.txt
# Set port if not COM9 (e.g. Linux: NFC_PORT=/dev/ttyUSB0)
python nfc_bridge.py
```

Options:

- `--port` / `-p` — serial port (default: COM9, or `NFC_PORT` env).
- `--baud` / `-b` — baud rate (default: 9600).
- `--url` — Django NFC login URL (default: `http://127.0.0.1:8001/api/v1/nfc-login/`).
- `--secret` / `-s` — bridge secret (or set `NFC_BRIDGE_SECRET`).
- `--no-browser` — do not open the browser after a successful login.

Example with secret:

```bash
python nfc_bridge.py --port COM9 --secret "your-secret"
```

### 4. Frontend

No extra setup. When the user is sent to the app with `?nfc_token=...`, the app exchanges it for the user profile and redirects to the products screen.

## Flow summary

1. User opens the web app (optional: can stay on landing).
2. User taps the NFC card on the reader.
3. Bridge reads UID, POSTs to `/api/v1/nfc-login/`.
4. Backend validates UID (and optional secret), creates a one-time token, returns `login_url`.
5. Bridge opens `login_url` in the browser (e.g. `http://127.0.0.1:5002/?nfc_token=...`).
6. Frontend exchanges the token with `POST /api/v1/nfc-complete/`, gets user, sets session and goes to products.

## Security note

Using only the card UID is like using a username without a password — UIDs can be cloned. For higher security, use a card that stores an encrypted secret and verify that instead of (or in addition to) the UID. For production, set `NFC_BRIDGE_SECRET` and keep it only on the machine running the bridge.
