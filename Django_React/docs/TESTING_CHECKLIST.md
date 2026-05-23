# NFC Authentication — Testing Checklist

Use this checklist for final verification. Mark each item as you test.

Legend: ☐ not tested, ✅ pass, ❌ fail

---

## Backend verification

### Migrations

- ☐ **Migrations exist**: `backend/module_account/migrations/0010_nfctag.py` present
  **How**: check file exists and is committed.  
  **Expected**: file present.

- ☐ **Migrations apply cleanly**
  **How**:

```bash
cd backend
python manage.py migrate --plan
python manage.py migrate
```

  **Expected**: no pending operations; no errors.

### URL routing

- ☐ **NFC URLs present in `api/v1/`**
  **How**: inspect `backend/module_api_v1/urls.py`.  
  **Expected**: paths exist: `user/nfc/login/`, `user/nfc/register/`, `user/nfc/unlink/`, `user/nfc/status/`, bridge flow `nfc-login/` and `nfc-complete/`.

### Endpoint access controls

- ☐ **NFC login accessible without auth**
  **How**:

```bash
curl -i -X POST "http://127.0.0.1:8001/api/v1/user/nfc/login/" \
  -H "Content-Type: application/json" \
  -d "{\"uid\":\"04a1b2c3\"}"
```

  **Expected**: If tag exists → **200** with `access`, `refresh`, `user`. If tag does not exist → **401** `{"error":"invalid credentials"}`.

- ☐ **NFC register requires auth**
  **How**: call without Authorization header.  
  **Expected**: **401** `{"error":"authentication required"}`.

- ☐ **NFC unlink requires auth**
  **How**: call without Authorization header.  
  **Expected**: **401** `{"error":"authentication required"}`.

- ☐ **NFC unlink requires ownership**
  **How**: link a tag to user A, then unlink using user B token.  
  **Expected**: **403** `{"error":"forbidden"}`.

### Error response format + status codes

- ☐ **Missing uid** → 400 with field name
  **How**: `POST /user/nfc/login/` with `{}` or omit `uid`.  
  **Expected**: **400** with `{"error": "...", "field": "uid"}`.

- ☐ **Whitespace-only uid** → 400
  **How**: `{"uid":"   "}`.  
  **Expected**: **400** with `field:"uid"`.

- ☐ **Invalid uid format** → 400 with hint
  **How**: `{"uid":"xyz"}`.  
  **Expected**: **400** with `{"error":"invalid uid format","field":"uid","hint":"..."}`.

- ☐ **Register UID already linked** → 409
  **How**: link UID to user A, then attempt register with user B token.  
  **Expected**: **409** `{"error":"uid already linked","field":"uid"}`.

- ☐ **Locked tag** → 423 with retry-after
  **How**: force lock in DB or trigger lockout.  
  **Expected**: **423** with `retry_after` and `Retry-After` header.

- ☐ **Rate limit exceeded** → 429 with retry-after
  **How**: spam `POST /user/nfc/login/` > `NFC_LOGIN_RATE_MAX` in one minute.  
  **Expected**: **429** with `retry_after` and `Retry-After` header.

### Lockout tests

- ☐ **5 consecutive failures → lock**
  **How**: ensure a tag exists and is active, then trigger failures that increment failed attempts.  
  **Expected**: locked response after threshold; `locked_until` set.

### Admin verification

- ☐ **Admin shows NFC tags**
  **How**: Django admin → `NFCTag`.  
  **Expected**: list displays masked UID + fields, search works by phone number, UID is read-only.

---

## Frontend verification

### Build + render

- ☐ **Frontend builds**
  **How**:

```bash
cd frontend
npm run build
```

  **Expected**: build succeeds.

- ☐ **NFCAuth renders in Login screen**
  **How**: open app → go to Login → expand “ورود با NFC”.  
  **Expected**: component displays “Connect reader” flow and does not crash.

### NFCHandler detection

- ☐ **Browser without NFC/Serial** shows unsupported message
  **How**: test on unsupported browser.  
  **Expected**: “NFC not supported…” guidance displayed.

- ☐ **Web Serial available** on desktop Chrome/Edge
  **How**: `navigator.serial` supported browser.  
  **Expected**: connect prompts for serial device permission.

- ☐ **Web NFC available** on Android Chrome
  **How**: device with NFC; Chrome.  
  **Expected**: scan permission prompt / scan works.

### Connection lifecycle

- ☐ **Connect → scan → disconnect**
  - **How**:
    - click Connect
    - click Start scanning
    - scan tag
    - click Disconnect
  - **Expected**:
    - clear status transitions
    - errors are shown inline (and logged to console)

### Cleanup

- ☐ **Unmount during scan does not throw**
  - **How**: start scanning then navigate away/back
  - **Expected**: no React warnings; scan aborts cleanly

### Auth state integration

- ☐ **NFC login updates auth state**
  - **How**: scan registered tag on login screen
  - **Expected**:
    - tokens stored in `localStorage` (`access`, `refresh`)
    - user state populated
    - redirect to `products`

- ☐ **Phone login still works**
  - **How**: SMS flow (send + verify)
  - **Expected**: still reaches products; tokens stored; no behavior regression

- ☐ **Switch between phone and NFC login**
  - **How**: back to landing/login; try both methods
  - **Expected**: both work; no stuck state

### User-friendly errors

- ☐ Network error → friendly message
  - **How**: disconnect internet then attempt NFC login
  - **Expected**: “Network error…” shown

- ☐ Server 500 → friendly message
  - **How**: simulate backend 500 then attempt NFC login
  - **Expected**: “Something went wrong…” shown with retry option

- ☐ Permission denied → instructions shown
  - **How**: deny Serial/NFC permission prompt
  - **Expected**: guidance text displayed

- ☐ Timeout → “No tag detected”
  - **How**: start scanning and wait for timeout
  - **Expected**: timeout message displayed

---

## Integration verification

- ☐ **Phone login and NFC login produce the same auth state**
  - **Expected**: both result in:
    - `localStorage.access` + `localStorage.refresh`
    - `user` set in React state
    - products screen loaded

- ☐ **NFC tag management screen is protected**
  - **How**: reach products then click “مدیریت NFC”
  - **Expected**: only reachable when logged in; shows token missing error if tokens cleared

---

## Notes / issues found during testing

- Result: ☐ ✅ ❌
- Notes:
