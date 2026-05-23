type NfcMethod = "web-nfc" | "web-serial" | null;

export type NfcHandlerState = {
  connected: boolean;
  scanning: boolean;
  method: NfcMethod;
  error: string | null;
};

export type ScanCallback = (uid: string) => void;
export type ErrorCallback = (message: string, originalError?: unknown) => void;

const DEFAULT_TIMEOUT_MS = 30_000;
const DEFAULT_MAX_RETRIES = 2;

// Common NFC UID sizes (bytes): 4, 7, 10 => hex chars: 8, 14, 20
const UID_LENGTHS = new Set([8, 14, 20]);

function normalizeUidCandidate(value: unknown): string {
  if (value == null) return "";
  return String(value).trim().toLowerCase();
}

function isHexString(value: string): boolean {
  return /^[0-9a-f]+$/i.test(value);
}

function extractUidFromText(text: string): string | null {
  // Normalize and remove common separators (spaces, colons, dashes)
  const cleaned = normalizeUidCandidate(text).replace(/\s+/g, "").replace(/[:-]/g, "");
  if (!cleaned) return null;

  // Some readers may prefix with "UID:" or similar.
  const withoutPrefix = cleaned.replace(/^uid[:=]/, "");
  if (UID_LENGTHS.has(withoutPrefix.length) && isHexString(withoutPrefix)) {
    return withoutPrefix;
  }

  // Handle common colon-separated formats (e.g. "54:DF:9C:CD" from NFC-A tags)
  const colonLike = normalizeUidCandidate(text).match(
    /\b(?:[0-9a-f]{2}[:\-]){3}[0-9a-f]{2}\b|\b(?:[0-9a-f]{2}[:\-]){6}[0-9a-f]{2}\b|\b(?:[0-9a-f]{2}[:\-]){9}[0-9a-f]{2}\b/i,
  );
  if (colonLike && colonLike[0]) {
    const compact = colonLike[0].replace(/[:-]/g, "");
    if (UID_LENGTHS.has(compact.length) && isHexString(compact)) {
      return compact.toLowerCase();
    }
  }

  // Fallback: find first UID-like hex chunk inside the string.
  const match = withoutPrefix.match(/\b[0-9a-f]{8}\b|\b[0-9a-f]{14}\b|\b[0-9a-f]{20}\b/i);
  if (match && match[0]) {
    return match[0].toLowerCase();
  }

  return null;
}

function safeErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  try {
    return JSON.stringify(err);
  } catch {
    return String(err);
  }
}

/**
 * NFCHandler
 *
 * A framework-agnostic handler that can read NFC tags using:
 * - Web NFC (Android Chrome): NDEFReader
 * - Web Serial (desktop): USB/COM reader that prints UID lines
 *
 * It exposes a simple imperative API (connect/start/stop/disconnect).
 */
export class NFCHandler {
  private state: NfcHandlerState = {
    connected: false,
    scanning: false,
    method: null,
    error: null,
  };

  private timeoutMs: number;
  private maxRetries: number;
  private serialBaudRate: number;

  // Web NFC
  private ndefReader: any | null = null;
  private nfcAbort: AbortController | null = null;
  private nfcTimeoutId: number | null = null;

  // Web Serial
  private port: SerialPort | null = null;
  private serialReader: ReadableStreamDefaultReader<string> | null = null;
  private serialTextDecoderStream: TransformStream<Uint8Array, string> | null = null;
  private serialTimeoutId: number | null = null;
  private serialBuffer = "";

  private currentScanCallback: ScanCallback | null = null;
  private currentErrorCallback: ErrorCallback | null = null;
  private scanRetryCount = 0;

  constructor(options?: { timeoutMs?: number; maxRetries?: number; serialBaudRate?: number }) {
    this.timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.maxRetries = options?.maxRetries ?? DEFAULT_MAX_RETRIES;
    this.serialBaudRate = options?.serialBaudRate ?? 9600;
  }

  /**
   * Returns true if any NFC method is available in the browser.
   */
  isAvailable(): boolean {
    return this.canUseWebNfc() || this.canUseWebSerial();
  }

  /**
   * Returns the currently active method, if connected.
   */
  getActiveMethod(): NfcMethod {
    return this.state.method;
  }

  /**
   * Establishes a connection to the best available method.
   * This may prompt the user for permissions (Web NFC / Web Serial).
   */
  async connect(): Promise<void> {
    this.setError(null);

    if (!this.isAvailable()) {
      throw new Error(
        "This browser does not support NFC. Use Android Chrome (Web NFC) or a compatible desktop browser with Web Serial support.",
      );
    }

    // Prefer Web NFC when available (mobile)
    if (this.canUseWebNfc()) {
      await this.connectWebNfc();
      return;
    }

    await this.connectWebSerial();
  }

  /**
   * Begin listening for tags.
   * - callback(uid): invoked when a UID is read.
   * - errorCallback(message, err): invoked for errors/timeouts.
   */
  async startScanning(callback: ScanCallback, errorCallback?: ErrorCallback): Promise<void> {
    this.currentScanCallback = callback;
    this.currentErrorCallback = errorCallback ?? null;
    this.scanRetryCount = 0;

    if (!this.state.connected) {
      await this.connect();
    }

    if (this.state.scanning) return;

    this.state.scanning = true;
    this.emitState();

    if (this.state.method === "web-nfc") {
      await this.startWebNfcScan();
      return;
    }
    if (this.state.method === "web-serial") {
      await this.startWebSerialScan();
      return;
    }

    throw new Error("No active NFC method. Call connect() first.");
  }

  /**
   * Stop listening for tags but keep the underlying connection.
   */
  stopScanning(): void {
    if (!this.state.scanning) return;
    this.state.scanning = false;
    this.emitState();

    if (this.state.method === "web-nfc") {
      this.stopWebNfcScan();
      return;
    }
    if (this.state.method === "web-serial") {
      this.stopWebSerialScan();
    }
  }

  /**
   * Full cleanup: stop scanning and release hardware resources.
   */
  async disconnect(): Promise<void> {
    this.stopScanning();

    if (this.state.method === "web-nfc") {
      this.cleanupWebNfc();
    } else if (this.state.method === "web-serial") {
      await this.cleanupWebSerial();
    }

    this.state.connected = false;
    this.state.method = null;
    this.emitState();
  }

  /**
   * Optional: observe internal state changes. (Framework-agnostic callback)
   */
  onStateChange?: (state: NfcHandlerState) => void;

  getState(): NfcHandlerState {
    return { ...this.state };
  }

  // -----------------------
  // Web NFC implementation
  // -----------------------

  private canUseWebNfc(): boolean {
    // Some browsers expose NDEFReader but not navigator.nfc.
    return typeof (globalThis as any).NDEFReader !== "undefined";
  }

  private async connectWebNfc(): Promise<void> {
    try {
      const Reader = (globalThis as any).NDEFReader;
      if (!Reader) throw new Error("Web NFC is not available.");

      this.ndefReader = new Reader();
      this.state.connected = true;
      this.state.method = "web-nfc";
      this.emitState();
    } catch (err) {
      const message =
        safeErrorMessage(err) ||
        "Web NFC is not available. Use Android Chrome and enable NFC permissions.";
      this.setError(message);
      throw new Error(message);
    }
  }

  private async startWebNfcScan(): Promise<void> {
    if (!this.ndefReader) {
      await this.connectWebNfc();
    }

    this.stopWebNfcScan();
    this.nfcAbort = new AbortController();

    // Timeout: cancel scanning after timeoutMs
    this.nfcTimeoutId = window.setTimeout(() => {
      this.handleError("No tag detected (timeout).");
      this.stopScanning();
    }, this.timeoutMs);

    try {
      await this.ndefReader.scan({ signal: this.nfcAbort.signal });

      // reading handler (Web NFC provides serialNumber on some platforms)
      this.ndefReader.onreading = (event: any) => {
        try {
          const serialNumber = normalizeUidCandidate(event?.serialNumber);
          const uidFromSerial = extractUidFromText(serialNumber);
          if (uidFromSerial) {
            this.handleUid(uidFromSerial);
            return;
          }

          // Fallback: parse NDEF records; some systems encode UID into a text record.
          const records: any[] = event?.message?.records ?? [];
          for (const record of records) {
            const recordType = normalizeUidCandidate(record?.recordType);
            if (recordType === "text") {
              // Text record: record.data may be DataView; decode as UTF-8 best-effort
              const dataView: DataView | null = record?.data ?? null;
              if (dataView) {
                const bytes = new Uint8Array(dataView.buffer);
                const text = new TextDecoder().decode(bytes);
                const extracted = extractUidFromText(text);
                if (extracted) {
                  this.handleUid(extracted);
                  return;
                }
              }
            }

            if (recordType === "url") {
              const dataView: DataView | null = record?.data ?? null;
              if (dataView) {
                const bytes = new Uint8Array(dataView.buffer);
                const text = new TextDecoder().decode(bytes);
                const extracted = extractUidFromText(text);
                if (extracted) {
                  this.handleUid(extracted);
                  return;
                }
              }
            }
          }

          // If we got here, data was valid but we couldn't extract UID.
          this.handleReadError("Corrupted/unsupported tag data. Please retry.");
        } catch (err) {
          this.handleReadError("Could not read tag. Please retry.", err);
        }
      };

      this.ndefReader.onerror = (err: any) => {
        // A generic read error; allow retries
        this.handleReadError("NFC read error. Please retry.", err);
      };
    } catch (err) {
      // Permission denied or not allowed.
      const raw = safeErrorMessage(err);
      const denied =
        raw.toLowerCase().includes("notallowed") ||
        raw.toLowerCase().includes("permission") ||
        raw.toLowerCase().includes("denied");
      if (denied) {
        this.handleError(
          "NFC permission denied. Please allow NFC permission in your browser settings and try again.",
          err,
        );
      } else {
        this.handleError("Could not start NFC scanning.", err);
      }
      this.stopScanning();
    }
  }

  private stopWebNfcScan(): void {
    if (this.nfcTimeoutId != null) {
      window.clearTimeout(this.nfcTimeoutId);
      this.nfcTimeoutId = null;
    }
    if (this.nfcAbort) {
      try {
        this.nfcAbort.abort();
      } catch {
        // ignore
      }
      this.nfcAbort = null;
    }
    if (this.ndefReader) {
      this.ndefReader.onreading = null;
      this.ndefReader.onerror = null;
    }
  }

  private cleanupWebNfc(): void {
    this.stopWebNfcScan();
    this.ndefReader = null;
  }

  // --------------------------
  // Web Serial implementation
  // --------------------------

  private canUseWebSerial(): boolean {
    return "serial" in navigator;
  }

  private async connectWebSerial(): Promise<void> {
    if (!this.canUseWebSerial()) {
      throw new Error(
        "Web Serial is not available in this browser. Use a Chromium-based browser (e.g. Chrome/Edge) and enable Web Serial.",
      );
    }

    try {
      // User gesture required (must be called from a click/tap handler)
      const nav = navigator as unknown as { serial: Serial };

      // If the user already granted permission before, re-use that port (no prompt).
      const existingPorts = await nav.serial.getPorts();
      this.port = existingPorts[0] ?? (await nav.serial.requestPort());

      // Default baud is device-specific; 9600 is common for many UID readers.
      // Use 115200 if your device requires it.
      try {
        await this.port.open({ baudRate: this.serialBaudRate });
      } catch (err) {
        // Some readers default to 115200; try a fallback once.
        if (this.serialBaudRate !== 115200) {
          await this.port.open({ baudRate: 115200 });
        } else {
          throw err;
        }
      }

      this.state.connected = true;
      this.state.method = "web-serial";
      this.emitState();

      // Listen to disconnects
      (navigator as any).serial.addEventListener?.("disconnect", (event: any) => {
        if (event?.target === this.port) {
          this.handleError("Scanner disconnected. Please reconnect the device and try again.");
          void this.disconnect();
        }
      });
    } catch (err) {
      const raw = safeErrorMessage(err);
      const denied =
        raw.toLowerCase().includes("notallowed") ||
        raw.toLowerCase().includes("permission") ||
        raw.toLowerCase().includes("denied");

      if (denied) {
        throw new Error(
          "Serial permission denied. Please allow access to the scanner device and try again.",
        );
      }
      if (raw.toLowerCase().includes("busy")) {
        throw new Error("Serial port busy. Please close other apps using the scanner and retry.");
      }

      throw new Error(raw || "No reader device found. Please connect a scanner and try again.");
    }
  }

  private async startWebSerialScan(): Promise<void> {
    if (!this.port) {
      await this.connectWebSerial();
    }
    if (!this.port || !this.port.readable) {
      this.handleError("No reader device found. Please connect a scanner and try again.");
      this.stopScanning();
      return;
    }

    this.stopWebSerialScan();
    this.serialBuffer = "";

    // Timeout if no tag is read
    this.serialTimeoutId = window.setTimeout(() => {
      this.handleError("No tag detected (timeout).");
      this.stopScanning();
    }, this.timeoutMs);

    try {
      // Decode bytes into text lines
      this.serialTextDecoderStream = new TextDecoderStream();
      const readableStreamClosed = this.port.readable.pipeTo(this.serialTextDecoderStream.writable);
      this.serialReader = this.serialTextDecoderStream.readable.getReader();

      // Read loop (buffer by lines; handle partial chunks)
      while (this.state.scanning && this.serialReader) {
        const { value, done } = await this.serialReader.read();
        if (done) break;
        if (!value) continue;

        this.serialBuffer += value;
        const parts = this.serialBuffer.split(/\r?\n/);
        this.serialBuffer = parts.pop() ?? "";

        for (const line of parts) {
          const uid = extractUidFromText(line);
          if (uid) {
            this.handleUid(uid);
          }
        }

        // Also try extracting from the rolling buffer (some devices don't newline).
        const uidFromBuffer = extractUidFromText(this.serialBuffer);
        if (uidFromBuffer) {
          this.handleUid(uidFromBuffer);
          this.serialBuffer = "";
        }
      }

      await readableStreamClosed.catch(() => {
        // ignore (happens on disconnect/stop)
      });
    } catch (err) {
      const raw = safeErrorMessage(err);
      if (raw.toLowerCase().includes("networkerror") || raw.toLowerCase().includes("disconnect")) {
        this.handleError("Scanner disconnected mid-scan. Please reconnect and try again.", err);
      } else if (raw.toLowerCase().includes("busy")) {
        this.handleError("Serial port busy. Please close other apps using the scanner.", err);
      } else {
        this.handleReadError("Scanner read error. Please retry.", err);
      }
      this.stopScanning();
    }
  }

  private stopWebSerialScan(): void {
    if (this.serialTimeoutId != null) {
      window.clearTimeout(this.serialTimeoutId);
      this.serialTimeoutId = null;
    }
    if (this.serialReader) {
      try {
        this.serialReader.cancel();
      } catch {
        // ignore
      }
      this.serialReader.releaseLock?.();
      this.serialReader = null;
    }
    if (this.serialTextDecoderStream) {
      this.serialTextDecoderStream = null;
    }
  }

  private async cleanupWebSerial(): Promise<void> {
    this.stopWebSerialScan();
    if (this.port) {
      try {
        await this.port.close();
      } catch {
        // ignore
      }
      this.port = null;
    }
  }

  // -----------------------
  // Shared helpers/events
  // -----------------------

  private handleUid(uid: string): void {
    // reset timeout window on activity
    if (this.state.method === "web-nfc" && this.nfcTimeoutId != null) {
      window.clearTimeout(this.nfcTimeoutId);
      this.nfcTimeoutId = window.setTimeout(() => {
        this.handleError("No tag detected (timeout).");
        this.stopScanning();
      }, this.timeoutMs);
    }
    if (this.state.method === "web-serial" && this.serialTimeoutId != null) {
      window.clearTimeout(this.serialTimeoutId);
      this.serialTimeoutId = window.setTimeout(() => {
        this.handleError("No tag detected (timeout).");
        this.stopScanning();
      }, this.timeoutMs);
    }

    this.scanRetryCount = 0;
    this.setError(null);
    this.currentScanCallback?.(uid);
  }

  private handleReadError(message: string, err?: unknown): void {
    if (this.scanRetryCount < this.maxRetries) {
      this.scanRetryCount += 1;
      // Auto-retry: keep scanning but notify error
      this.currentErrorCallback?.(`${message} (retry ${this.scanRetryCount}/${this.maxRetries})`, err);
      return;
    }
    this.handleError(message, err);
  }

  private handleError(message: string, err?: unknown): void {
    this.setError(message);
    this.currentErrorCallback?.(message, err);
  }

  private setError(message: string | null): void {
    this.state.error = message;
    this.emitState();
  }

  private emitState(): void {
    this.onStateChange?.(this.getState());
  }
}

