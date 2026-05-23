import { useEffect, useRef, useState } from "react";
import { loginByCard, type AuthSession } from "./api";
import { deriveCardUidCode } from "./utils/cardUid";
import {
  disconnectMifareReader,
  isMifareInternalError,
  isMifareSerialAvailable,
  mifareAnticollision,
} from "./utils/services/mifareHardware";

type Props = {
  shopId: number | null;
  disabled?: boolean;
  onLoginSuccess: (session: AuthSession) => void;
};

const RETRY_DELAY_MS = 500;
const CARD_NOT_REGISTERED = "این کارت ثبت نشده است";

type ScanPhase = "idle" | "connecting" | "scanning" | "logging_in";

export function NFCLoginScan({ shopId, disabled, onLoginSuccess }: Props) {
  const mountedRef = useRef(true);
  const scanBusyRef = useRef(false);
  const loopGenerationRef = useRef(0);
  const [phase, setPhase] = useState<ScanPhase>("idle");
  const [errorText, setErrorText] = useState("");
  const [needsConnect, setNeedsConnect] = useState(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      stopScan();
    };
  }, []);

  useEffect(() => {
    if (!shopId || disabled) {
      return;
    }
    void startScan();
    return () => {
      stopScan();
    };
  }, [shopId, disabled]);

  function stopScan() {
    loopGenerationRef.current += 1;
    scanBusyRef.current = false;
    if (mountedRef.current) {
      setPhase("idle");
    }
    void disconnectMifareReader();
  }

  async function loginWithUid(uid: string): Promise<boolean> {
    if (!shopId) {
      setErrorText("لطفاً ابتدا فروشگاه را انتخاب کنید.");
      return false;
    }
    setPhase("logging_in");
    try {
      const session = await loginByCard(uid, shopId);
      if (!mountedRef.current) {
        return true;
      }
      onLoginSuccess(session);
      setErrorText("");
      return true;
    } catch (err) {
      if (!mountedRef.current) {
        return true;
      }
      const message = err instanceof Error ? err.message : "";
      if (
        message.includes(CARD_NOT_REGISTERED) ||
        message.includes("card_uid") ||
        message.includes("404")
      ) {
        setErrorText(CARD_NOT_REGISTERED);
      } else {
        setErrorText(message || "ورود با NFC ناموفق بود.");
      }
      return false;
    }
  }

  async function readOnce(): Promise<"done" | "retry" | "stop"> {
    const response = await mifareAnticollision();
    if (!mountedRef.current) {
      return "stop";
    }
    if (response.error === "access_denied") {
      setNeedsConnect(true);
      setPhase("idle");
      return "stop";
    }
    setNeedsConnect(false);
    if (response.is_done && response.data) {
      const uidCode = await deriveCardUidCode(response.data);
      if (!uidCode) {
        setErrorText("شناسه کارت نامعتبر است.");
        return "stop";
      }
      const loggedIn = await loginWithUid(uidCode);
      return loggedIn ? "done" : "stop";
    }
    if (response.error && !isMifareInternalError(response.error)) {
      setErrorText(String(response.error));
    }
    return "retry";
  }

  async function startScan() {
    if (disabled || scanBusyRef.current || !shopId) {
      if (!shopId) {
        setErrorText("لطفاً ابتدا فروشگاه را انتخاب کنید.");
      }
      return;
    }

    const enabled = (import.meta.env.VITE_NFC_ENABLED ?? "true").toLowerCase() !== "false";
    if (!enabled || !isMifareSerialAvailable()) {
      setErrorText("اسکنر سریال در این مرورگر پشتیبانی نمی‌شود.");
      return;
    }

    scanBusyRef.current = true;
    loopGenerationRef.current += 1;
    const generation = loopGenerationRef.current;
    setErrorText("");
    setNeedsConnect(false);
    setPhase("connecting");

    try {
      while (mountedRef.current && generation === loopGenerationRef.current) {
        if (mountedRef.current && generation === loopGenerationRef.current) {
          setPhase("scanning");
        }
        try {
          const outcome = await readOnce();
          if (outcome === "done" || outcome === "stop") {
            return;
          }
        } catch (err) {
          if (!mountedRef.current || generation !== loopGenerationRef.current) {
            return;
          }
          const message = err instanceof Error ? err.message : "خطا در خواندن کارت";
          if (message.toLowerCase().includes("denied")) {
            setNeedsConnect(true);
            setPhase("idle");
            return;
          }
          setErrorText(message);
          setPhase("idle");
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
      }
    } finally {
      if (generation === loopGenerationRef.current) {
        scanBusyRef.current = false;
        if (mountedRef.current) {
          setPhase("idle");
        }
      }
    }
  }

  function handleReset() {
    stopScan();
    setErrorText("");
    setNeedsConnect(false);
  }

  const scanning = phase === "connecting" || phase === "scanning" || phase === "logging_in";

  return (
    <div className="nfc-login panel">
      <h3>ورود با NFC</h3>

      {needsConnect ? (
        <p className="register-nfc-prompt">لطفا کارت خود را روی اسکنر قرار دهید</p>
      ) : scanning ? (
        <p className="register-nfc-prompt">
          {phase === "logging_in" ? "در حال ورود…" : "کارت را نزدیک سنسور قرار بده"}
        </p>
      ) : null}

      {errorText ? <p className="error-box nfc-registration__error">{errorText}</p> : null}

      <div className="row-actions">
        <button
          type="button"
          className="action-button"
          onClick={() => void startScan()}
          disabled={disabled || scanning || !shopId}
        >
          {scanning ? "در حال اسکن…" : "ورود با NFC"}
        </button>
        <button
          type="button"
          className="outline-button"
          onClick={handleReset}
          disabled={disabled || phase === "logging_in"}
        >
          ریست
        </button>
        {needsConnect ? (
          <button
            type="button"
            className="outline-button small"
            onClick={() => void startScan()}
            disabled={disabled}
          >
            اتصال به اسکنر
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default NFCLoginScan;
