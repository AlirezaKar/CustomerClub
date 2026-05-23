# CustomerClub Frontend (React + TypeScript)

CustomerClub frontend is a kiosk-oriented web app for physical shops using NFC and phone-based authentication.

## Features Implemented

- Landing page with two entry paths:
  - Login by phone number (SMS verification flow)
  - Login by NFC card UID (direct login)
- Registration page with numeric keypad:
  - Phone number
  - Age (required by current backend API)
  - Gender
  - Optional NFC card UID
- SMS verification screen:
  - 4-digit code input using keypad
  - 60-second frontend timeout
  - Wrong/expired error messages
  - Resend option
- Product selection page:
  - Category tabs
  - Product cards with image, title, price
  - Cart summary with selected count and totals
- User-specific offers/deals panel:
  - Loaded from backend `useroffer_set`
  - Offer add-to-cart support
- Finalization page:
  - Itemized summary
  - Subtotal, discount, tax, final payable
  - Auto-exit countdown
- Receipt generation:
  - Downloads a printable PDF file

## Tech Stack

- React 19
- TypeScript
- Vite
- Native Fetch API for backend requests

## Project Structure

- `src/App.tsx`: main flow and UI
- `src/api.ts`: backend HTTP client calls
- `src/types.ts`: shared TypeScript types
- `src/pdf.ts`: simple PDF receipt builder
- `src/index.css`: kiosk-focused RTL styles

## Backend API Endpoints Used

Base URL default:

`http://127.0.0.1:8001/api/v1`

Used endpoints:

- `POST /user/signup/`
- `POST /user/login/`
- `POST /user/submit-offer/`
- `GET /shop/settings/categories/?shop_id=<id>`

## Configuration

Create `.env` in `frontend/` if needed:

```env
VITE_API_BASE_URL=http://127.0.0.1:8001/api/v1
VITE_SHOP_ID=1
```

## Run

1. Install dependencies:

```bash
npm install
```

2. Start dev server (Vite is configured for port **5002**):

```bash
npm run dev
```

3. Build for production:

```bash
npm run build
```

## Notes

- Current backend signup requires `age`; this frontend captures it to stay compatible.
- SMS validation on backend is still authoritative. Frontend enforces a 60-second UX timeout for kiosk security.
- NFC integration is represented using card UID input (compatible with scanner/keyboard-wedge workflows).



curl -i http://127.0.0.1:8001/api/v1/schema/


curl -i -X POST "http://127.0.0.1:8001/api/v1/user/login/" -H "Content-Type: application/json" -d "{\"phone_number\":\"09120000000\",\"send_login_verification_code\":true}"
