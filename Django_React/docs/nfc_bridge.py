"""
NFC Bridge: reads UID from a serial NFC reader and sends it to the Django backend.
The backend returns a one-time login URL; this script can open it in the browser
so the user is logged in on the web app.

Usage:
  1. Install: pip install pyserial requests
  2. Set PORT (e.g. COM9 on Windows, /dev/ttyUSB0 on Linux) and LOGIN_URL if needed.
  3. Run: python nfc_bridge.py
  4. Keep the script running; tap a card to trigger login.

For production, set NFC_BRIDGE_SECRET in Django .env and pass it via --secret or
NFC_BRIDGE_SECRET env var so the backend accepts requests only from this bridge.
"""

import argparse
import os
import sys
import webbrowser

try:
    import serial
    import requests
except ImportError as e:
    print("Install dependencies: pip install pyserial requests", file=sys.stderr)
    raise SystemExit(1) from e

# Configure from env or defaults
PORT = os.environ.get("NFC_PORT", "COM9")
BAUD_RATE = int(os.environ.get("NFC_BAUD", "9600"))
LOGIN_URL = os.environ.get(
    "NFC_LOGIN_URL",
    "http://127.0.0.1:8001/api/v1/nfc-login/",
)
OPEN_BROWSER = os.environ.get("NFC_OPEN_BROWSER", "true").lower() in ("1", "true", "yes", "on")


def listen_nfc(port: str, baud_rate: int, login_url: str, secret: str | None, open_browser: bool) -> None:
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-NFC-Bridge-Secret"] = secret

    with serial.Serial(port, baud_rate, timeout=1) as ser:
        print(f"Listening for NFC cards on {port} (baud={baud_rate})...")
        print("Tap a card to log in. Ctrl+C to exit.")
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            print(f"Card detected! UID: {line}")
            try:
                payload = {"uid": line}
                if secret:
                    payload["secret"] = secret
                response = requests.post(
                    login_url,
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
                data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                if response.ok and data.get("status") == "success":
                    print(f"Server response: {response.status_code} – user: {data.get('user', '?')}")
                    login_url_front = data.get("login_url")
                    if open_browser and login_url_front:
                        webbrowser.open(login_url_front)
                        print("Opened login URL in browser.")
                else:
                    print(f"Server response: {response.status_code} – {data.get('message', response.text)}")
            except requests.RequestException as e:
                print(f"Error connecting to Django: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="NFC bridge: read card UID and send to web app for login.")
    parser.add_argument("--port", "-p", default=PORT, help=f"Serial port (default: {PORT})")
    parser.add_argument("--baud", "-b", type=int, default=BAUD_RATE, help=f"Baud rate (default: {BAUD_RATE})")
    parser.add_argument("--url", "-u", default=LOGIN_URL, help="Django NFC login API URL")
    parser.add_argument("--secret", "-s", default=os.environ.get("NFC_BRIDGE_SECRET"), help="Bridge secret (or NFC_BRIDGE_SECRET env)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser after successful login")
    args = parser.parse_args()

    listen_nfc(
        port=args.port,
        baud_rate=args.baud,
        login_url=args.url,
        secret=args.secret,
        open_browser=not args.no_browser and OPEN_BROWSER,
    )


if __name__ == "__main__":
    main()
