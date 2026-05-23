# serial_reader_debug.py
import argparse
import sys
import time
from datetime import datetime

try:
    import serial
    from serial.tools import list_ports
except ImportError as e:
    print("Missing dependency. Install with: pip install pyserial", file=sys.stderr)
    raise SystemExit(1) from e


def now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def hex_dump(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def safe_text(b: bytes) -> str:
    # Show both UTF-8 best-effort and a latin-1 fallback style
    try:
        return b.decode("utf-8", errors="replace")
    except Exception:
        return b.decode("latin-1", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(description="Debug a USB-Serial NFC UID reader (prints raw bytes).")
    parser.add_argument("--port", "-p", default="COM9", help="Serial port (e.g. COM9)")
    parser.add_argument("--baud", "-b", type=int, default=9600, help="Baud rate (e.g. 9600 or 115200)")
    parser.add_argument("--timeout", "-t", type=float, default=0.2, help="Read timeout in seconds")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List detected serial ports and exit.",
    )
    args = parser.parse_args()

    if args.list:
        print(f"[{now_ts()}] Detected serial ports:")
        ports = list(list_ports.comports())
        if not ports:
            print("  (none)")
            return
        for p in ports:
            # p.device like "COM9"
            print(f"  - {p.device}: {p.description} (hwid={p.hwid})")
        return

    print(f"[{now_ts()}] Opening {args.port} @ {args.baud} baud (timeout={args.timeout}s)")
    print(f"[{now_ts()}] Tap a card. Press Ctrl+C to exit.\n")

    buf = bytearray()
    last_print = time.time()

    # On Windows, some setups prefer the explicit device path: \\\\.\\COM9
    port_candidates = [args.port]
    if args.port.upper().startswith("COM"):
        port_candidates.append(rf"\\.\{args.port.upper()}")

    ser = None
    last_err = None
    for candidate in port_candidates:
        try:
            ser = serial.Serial(candidate, args.baud, timeout=args.timeout)
            break
        except Exception as exc:
            last_err = exc

    if ser is None:
        msg = str(last_err) if last_err else "Unknown error"
        print(f"[{now_ts()}] ERROR: could not open port {args.port!r}")
        print(f"[{now_ts()}] DETAILS: {msg}\n")
        if "Access is denied" in msg or "PermissionError" in msg:
            print("Likely causes:")
            print("- Another app is using the port (Chrome/Edge Web Serial, nfc_bridge.py, Arduino Serial Monitor, etc.)")
            print("- The port is still held after a crash; unplug/replug the reader")
            print("\nFix steps:")
            print("1) Close Chrome/Edge tabs that used the scanner and restart the browser.")
            print("2) Stop any running scripts that access COM9 (e.g. nfc_bridge.py).")
            print("3) Unplug the reader, wait 3 seconds, plug it back in.")
            print("4) Run: python serial_reader_debug.py --list (confirm which COM port it is now).")
            print("5) Try running your terminal as Administrator.")
        raise SystemExit(2)

    # Use context manager style manual close to ensure release
    try:
        while True:
            chunk = ser.read(ser.in_waiting or 1)
            if chunk:
                buf.extend(chunk)

                # Print immediately on newline/CR (common readers)
                if b"\n" in chunk or b"\r" in chunk:
                    data = bytes(buf)
                    buf.clear()
                    print(f"[{now_ts()}] RX {len(data)} bytes")
                    print(f"HEX : {hex_dump(data)}")
                    print(f"TEXT: {safe_text(data)!r}\n")
                    last_print = time.time()
                    continue

                # Also print periodically if data is coming without newlines
                if time.time() - last_print > 0.5 and len(buf) > 0:
                    data = bytes(buf)
                    buf.clear()
                    print(f"[{now_ts()}] RX {len(data)} bytes (no newline)")
                    print(f"HEX : {hex_dump(data)}")
                    print(f"TEXT: {safe_text(data)!r}\n")
                    last_print = time.time()
            else:
                # No data; if buffer has stale bytes, flush them
                if buf and (time.time() - last_print) > 1.0:
                    data = bytes(buf)
                    buf.clear()
                    print(f"[{now_ts()}] RX {len(data)} bytes (flush)")
                    print(f"HEX : {hex_dump(data)}")
                    print(f"TEXT: {safe_text(data)!r}\n")
                    last_print = time.time()
    finally:
        try:
            ser.close()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{now_ts()}] Exiting.")