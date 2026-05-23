import { useEffect, useMemo, useRef, useState } from "react";
import { NFCHandler } from "./utils/services/nfcHandler";
import { deriveCardUidCode } from "./utils/cardUid";
import { nfcJwtLogin, NfcLockedError, nfcRegisterTag, type AuthSession } from "./api";

type Mode = "login" | "register";

type Props = {
  /**
   * If provided, enables the "Link NFC Tag" flow.
   * Backend requires JWT auth for linking.
   */
  accessToken?: string | null;

  /**
   * Called after NFC login succeeds (JWT tokens + user profile).
   */
  onLoginSuccess?: (session: AuthSession) => void;

  /**
   * Called after NFC tag linking succeeds.
   */
  onRegisterSuccess?: (tag: { uid: string; tag_id: number }) => void;

  /**
   * UI mode (login or register). If not provided, the component renders both actions.
   */
  mode?: Mode;

  /** Required for NFC login so offers sync for the selected shop. */
  shopId?: number | null;
};

type UiStatus =
  | "checking"
  | "unsupported"
  | "idle"
  | "connecting"
  | "ready"
  | "scanning"
  | "tagDetected"
  | "submitting"
  | "success"
  | "error";

function maskUidForUi(uid: string): string {
  const normalized = uid.trim().toUpperCase();
  if (!normalized) return "XXXX";
  const last4 = normalized.slice(-4);
  const masked = `${"X".repeat(Math.max(0, normalized.length - 4))}${last4}`;
  return masked.replace(/(.{4})/g, "$1-").replace(/-$/, "");
}

function mapErrorToMessage(error: unknown): { title: string; message: string } {
  if (error instanceof NfcLockedError) {
    const minutes =
      error.retryAfterSeconds != null
        ? Math.max(1, Math.ceil(error.retryAfterSeconds / 60))
        : null;
    return {
      title: "Too many attempts",
      message: minutes ? `Try again in ${minutes} minutes.` : "Try again later.",
    };
  }

  const message = error instanceof Error ? error.message : "Unknown error";
  const status = error instanceof Error ? ((error as any).status as number | undefined) : undefined;

  if (/[\u0600-\u06FF]/.test(message)) {
    return { title: "خطا", message };
  }

  if (status === 0) {
    return { title: "Network error", message };
  }
  if (status && status >= 500) {
    return { title: "Server error", message: "Something went wrong. Please try again." };
  }
  if (status === 429) {
    const retryAfter = (error as any).retry_after as number | undefined;
    return {
      title: "Too many requests",
      message: retryAfter ? `Try again in ${Math.ceil(retryAfter / 60)} minutes.` : "Please try again later.",
    };
  }

  if (message === "shop_not_selected") {
    return { title: "Shop required", message: "Please select a shop on the home screen first." };
  }
  if (message === "invalid credentials") {
    return { title: "Tag not found", message: "This tag is not registered." };
  }
  if (message === "invalid uid format" || message === "uid required") {
    return { title: "Invalid tag", message: "Could not read this tag. Please try again." };
  }
  if (message === "uid already linked") {
    return { title: "خطا", message: "کارت قبلا ثبت شده است" };
  }

  return { title: "Error", message };
}

/**
 * NFCAuth
 *
 * UI component for NFC authentication + optional tag linking.
 * Uses the framework-agnostic NFCHandler and the backend NFC endpoints.
 */
export function NFCAuth({
  accessToken,
  onLoginSuccess,
  onRegisterSuccess,
  mode: modeProp,
  shopId,
}: Props) {
  const handlerRef = useRef<NFCHandler | null>(null);
  const mountedRef = useRef(true);

  const [mode, setMode] = useState<Mode>(modeProp ?? "login");
  const [uiStatus, setUiStatus] = useState<UiStatus>("checking");
  const [statusText, setStatusText] = useState("");
  const [errorText, setErrorText] = useState("");
  const [lastUid, setLastUid] = useState("");

  const canRegister = Boolean(accessToken);

  const maskedUid = useMemo(() => (lastUid ? maskUidForUi(lastUid) : ""), [lastUid]);

  useEffect(() => {
    mountedRef.current = true;
    const enabled = (import.meta.env.VITE_NFC_ENABLED ?? "true").toLowerCase() !== "false";
    if (!enabled) {
      setUiStatus("unsupported");
      setStatusText("");
      return;
    }

    const timeoutMs = Number(import.meta.env.VITE_NFC_TIMEOUT_MS ?? "30000");
    const maxRetries = Number(import.meta.env.VITE_NFC_MAX_RETRIES ?? "2");
    const serialBaudRate = Number(import.meta.env.VITE_NFC_SERIAL_BAUD ?? "9600");

    const handler = new NFCHandler({
      timeoutMs: Number.isFinite(timeoutMs) ? timeoutMs : 30_000,
      maxRetries: Number.isFinite(maxRetries) ? maxRetries : 2,
      serialBaudRate: Number.isFinite(serialBaudRate) ? serialBaudRate : 9600,
    });
    handler.onStateChange = () => {};
    handlerRef.current = handler;

    if (!handler.isAvailable()) {
      setUiStatus("unsupported");
      setStatusText("");
      return () => {
        void handler.disconnect();
      };
    }

    setUiStatus("idle");
    setStatusText("");

    return () => {
      mountedRef.current = false;
      void handler.disconnect();
    };
  }, []);

  useEffect(() => {
    if (mode === "register" && !canRegister) {
      setMode("login");
    }
  }, [mode, canRegister]);

  useEffect(() => {
    if (modeProp) {
      setMode(modeProp);
    }
  }, [modeProp]);

  async function connect() {
    if (!mountedRef.current) return;
    setErrorText("");
    setUiStatus("connecting");
    setStatusText("");
    try {
      await handlerRef.current?.connect();
      if (!mountedRef.current) return;
      setUiStatus("ready");
      setStatusText("");
    } catch (err) {
      if (!mountedRef.current) return;
      console.error("NFC connect failed", err);
      const mapped = mapErrorToMessage(err);
      setUiStatus("error");
      setErrorText(mapped.message);
      setStatusText("");
    }
  }

  async function startScan() {
    if (!mountedRef.current) return;
    setErrorText("");
    setLastUid("");
    setUiStatus("scanning");
    setStatusText("");

    try {
      // One-click flow: connect if needed.
      if (uiStatus === "idle") {
        await handlerRef.current?.connect();
      }
      await handlerRef.current?.startScanning(
        async (uid) => {
          if (!mountedRef.current) return;
          setLastUid(uid);
          setUiStatus("tagDetected");
          setStatusText("");

          // Auto-submit
          setUiStatus("submitting");
          setStatusText("");

          if (mode === "login") {
            if (!shopId) {
              throw new Error("shop_not_selected");
            }
            const uidCode = await deriveCardUidCode(uid);
            if (!uidCode) {
              throw new Error("invalid uid format");
            }
            const session = await nfcJwtLogin(uidCode, shopId);
            if (!mountedRef.current) return;
            onLoginSuccess?.(session);
            setUiStatus("success");
            setStatusText("");
            handlerRef.current?.stopScanning();
            return;
          }

          if (!accessToken) {
            throw new Error("authentication required");
          }
          const tag = await nfcRegisterTag(uid, accessToken);
          if (!mountedRef.current) return;
          onRegisterSuccess?.(tag);
          setUiStatus("success");
          setStatusText("");
          handlerRef.current?.stopScanning();
        },
        (message) => {
          // Scanner errors, timeouts, disconnects, etc.
          if (!mountedRef.current) return;
          console.error("NFC scanner error:", message);
          setUiStatus("error");
          setStatusText("");
          setErrorText(message);
        },
      );
    } catch (err) {
      if (!mountedRef.current) return;
      console.error("NFC scan/login failed", err);
      const mapped = mapErrorToMessage(err);
      setUiStatus("error");
      setStatusText("");
      setErrorText(mapped.message);
    }
  }

  function stopScan() {
    handlerRef.current?.stopScanning();
    if (!mountedRef.current) return;
    setUiStatus("ready");
    setStatusText("");
  }

  async function disconnect() {
    if (!mountedRef.current) return;
    setErrorText("");
    setLastUid("");
    setUiStatus("idle");
    setStatusText("");
    await handlerRef.current?.disconnect();
  }

  return (
    <section aria-label="NFC authentication">
      <div aria-live="polite" aria-atomic="true">
        {statusText ? <p>{statusText}</p> : null}
      </div>

      {uiStatus === "unsupported" && <p className="error-box">NFC is not supported on this device.</p>}
      {errorText && <p className="error-box">{errorText}</p>}

      {maskedUid && (
        <p>
          {maskedUid}
        </p>
      )}

      <div className="row-actions">
        {!modeProp ? (
          <>
            <button
              type="button"
              className={mode === "login" ? "action-button small" : "outline-button small"}
              onClick={() => setMode("login")}
            >
              Login
            </button>
            <button
              type="button"
              className={mode === "register" ? "action-button small" : "outline-button small"}
              onClick={() => setMode("register")}
              disabled={!canRegister}
              aria-disabled={!canRegister}
            >
              Link tag
            </button>
          </>
        ) : null}

        <button
          type="button"
          className="action-button"
          onClick={() => void startScan()}
          aria-label={mode === "login" ? "Scan to login with NFC" : "Scan to link NFC tag"}
          disabled={uiStatus === "connecting" || uiStatus === "submitting"}
        >
          {mode === "login" ? "ورود با NFC" : "لینک کردن NFC"}
        </button>

        <button
          type="button"
          className="outline-button"
          onClick={() => void disconnect()}
          disabled={uiStatus === "submitting"}
        >
          ریست
        </button>

        {uiStatus === "scanning" ? (
          <button type="button" className="outline-button" onClick={stopScan}>
            Stop
          </button>
        ) : null}
      </div>
    </section>
  );
}

export default NFCAuth;

