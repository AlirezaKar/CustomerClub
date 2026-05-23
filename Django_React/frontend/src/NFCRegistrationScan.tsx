import { useEffect, useRef, useState } from "react";
import { deriveCardUidCode } from "./utils/cardUid";
import {
  disconnectMifareReader,
  isMifareInternalError,
  isMifareSerialAvailable,
  mifareAnticollision,
} from "./utils/services/mifareHardware";

type Props = {
  capturedUid: string;
  onUidCaptured: (uid: string) => void;
  onClear?: () => void;
};

const RETRY_DELAY_MS = 500;

/**
 * Registration NFC scanner — mirrors flutter_frontend signup_page.dart:
 * one scan at a time, auto-retry loop, card_uid held until signup.
 */
export function NFCRegistrationScan({ capturedUid, onUidCaptured, onClear }: Props) {
  const mountedRef = useRef(true);
  const capturedRef = useRef(capturedUid);
  const scanBusyRef = useRef(false);
  const loopGenerationRef = useRef(0);
  const [errorText, setErrorText] = useState("");
  const [needsConnect, setNeedsConnect] = useState(false);

  useEffect(() => {
    capturedRef.current = capturedUid;
  }, [capturedUid]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      loopGenerationRef.current += 1;
      scanBusyRef.current = false;
      void disconnectMifareReader();
    };
  }, []);

  async function readOnce(): Promise<"captured" | "retry" | "stop"> {
    const response = await mifareAnticollision();
    if (!mountedRef.current) {
      return "stop";
    }
    if (response.error === "access_denied") {
      setNeedsConnect(true);
      return "stop";
    }
    setNeedsConnect(false);
    if (response.is_done && response.data) {
      const uidCode = await deriveCardUidCode(response.data);
      if (!uidCode) {
        setErrorText("شناسه کارت نامعتبر است.");
        return "retry";
      }
      onUidCaptured(uidCode);
      setErrorText("");
      return "captured";
    }
    if (response.error && !isMifareInternalError(response.error)) {
      setErrorText(String(response.error));
    } else {
      setErrorText("");
    }
    return "retry";
  }

  async function scanLoop() {
    if (scanBusyRef.current) {
      return;
    }
    scanBusyRef.current = true;
    const generation = loopGenerationRef.current;

    try {
      while (
        mountedRef.current &&
        generation === loopGenerationRef.current &&
        !capturedRef.current
      ) {
        try {
          const outcome = await readOnce();
          if (outcome === "captured" || outcome === "stop") {
            return;
          }
        } catch (err) {
          if (!mountedRef.current || generation !== loopGenerationRef.current) {
            return;
          }
          const message = err instanceof Error ? err.message : "خطا در خواندن کارت";
          if (message.toLowerCase().includes("denied")) {
            setNeedsConnect(true);
            return;
          }
          setErrorText(message);
        }
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
      }
    } finally {
      if (generation === loopGenerationRef.current) {
        scanBusyRef.current = false;
      }
    }
  }

  useEffect(() => {
    const enabled = (import.meta.env.VITE_NFC_ENABLED ?? "true").toLowerCase() !== "false";
    if (!enabled || !isMifareSerialAvailable() || capturedUid) {
      return;
    }
    void scanLoop();
  }, [capturedUid]);

  function handleRescan() {
    onClear?.();
    setErrorText("");
    setNeedsConnect(false);
    void scanLoop();
  }

  const enabled = (import.meta.env.VITE_NFC_ENABLED ?? "true").toLowerCase() !== "false";
  const supported = enabled && isMifareSerialAvailable();

  const message = capturedUid
    ? "کارت شما ثبت شد"
    : needsConnect
      ? "لطفا کارت خود را روی اسکنر قرار دهید"
      : supported
        ? "کارت را نزدیک سنسور قرار بده"
        : "اسکنر سریال در این مرورگر پشتیبانی نمی‌شود";

  const boxClass = capturedUid
    ? "nfc-scan-box nfc-scan-box--success"
    : supported
      ? "nfc-scan-box nfc-scan-box--active"
      : "nfc-scan-box nfc-scan-box--error";

  return (
    <div className="nfc-registration">
      <div className={boxClass} aria-live="polite">
        {capturedUid ? (
          <span className="nfc-scan-box__icon" aria-hidden="true">
            ✓
          </span>
        ) : null}
        <span className="nfc-scan-box__text">{message}</span>
      </div>

      {errorText ? <p className="error-box nfc-registration__error">{errorText}</p> : null}

      {needsConnect && !capturedUid ? (
        <button type="button" className="outline-button small" onClick={() => void scanLoop()}>
          اتصال به اسکنر
        </button>
      ) : null}

      {capturedUid ? (
        <button type="button" className="outline-button small" onClick={handleRescan}>
          اسکن مجدد کارت
        </button>
      ) : null}
    </div>
  );
}

export default NFCRegistrationScan;
