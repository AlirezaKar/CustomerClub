/**
 * Browser port of flutter_frontend/lib/utils/functions/hardware_base.dart
 * and hardware.dart — same MIFARE-over-USB-serial protocol.
 */

export type MifareResponse = {
  is_done: boolean;
  data?: string | null;
  error?: string | null;
};

const BAUD_RATE = Number(import.meta.env.VITE_NFC_SERIAL_BAUD ?? "19200");
const READ_TIMEOUT_MS = 200;
const WATCH_DOG_LIMIT = 1;
const WATCH_DOG_DELAY_MS = 100;
const CREATE_NEW_CONNECTION_LIMIT = 5;
const CREATE_NEW_CONNECTION_DELAY_MS = 300;

const RESERVE_CONNECTION_ERRORS = ["create_new_connection_limit"];
const RESERVE_RELEASE_ERRORS = ["already_released", "can_not_release_connection"];
const OPEN_CONNECTION_ERRORS = [
  "already_opened",
  "hardware_not_connected",
  "access_denied",
  "somwthing_went_wrong_in_open_connection",
];

/** Internal serial-state errors — retry silently in the UI scan loop. */
export const MIFARE_INTERNAL_ERRORS = new Set([
  "create_new_connection_limit",
  "reservetion_code_is_not_match",
  "already_opened",
  "already_released",
  "can_not_release_connection",
  "already_closed",
]);

let hardwareChain: Promise<unknown> = Promise.resolve();

function withHardwareLock<T>(fn: () => Promise<T>): Promise<T> {
  const run = hardwareChain.then(fn, fn);
  hardwareChain = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function intToHex(value: number, byteCount: number): string {
  return value.toString(16).padStart(byteCount * 2, "0");
}

function hexStrToIntList(hexStr: string): number[] {
  const intList: number[] = [];
  for (let byteIndex = 0; byteIndex < hexStr.length; byteIndex += 2) {
    intList.push(parseInt(hexStr.substring(byteIndex, byteIndex + 2), 16));
  }
  return intList;
}

function intListToHexStr(intList: number[]): string {
  return intList.map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function generateXor(data: string): string {
  let xor = 0;
  for (let byteIndex = 8; byteIndex < data.length; byteIndex += 2) {
    xor ^= parseInt(data.substring(byteIndex, byteIndex + 2), 16);
  }
  return intToHex(xor, 1);
}

export function checkResponse(
  response: MifareResponse,
  dataType?: "string" | "int",
): MifareResponse {
  const next: MifareResponse = { ...response };
  if (next.is_done && next.data) {
    next.is_done = parseInt(next.data.substring(16, 18), 16) === 0;
  }
  if (next.is_done && dataType != null && next.data) {
    if (dataType === "string") {
      next.data = next.data.substring(18, next.data.length - 2);
    } else if (dataType === "int") {
      next.data = String(
        parseInt(next.data.substring(18, next.data.length - 2), 16),
      );
    }
  } else {
    next.data = null;
  }
  return next;
}

class HardwareBase {
  private static reservationCode: string | null = null;
  private static connection: SerialPort | null = null;
  private static watchDog = 0;
  private static createNewConnection = 0;

  private static reservationChars =
    "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz1234567890";

  static forceReset(): void {
    this.reservationCode = null;
    this.createNewConnection = 0;
    this.watchDog = 0;
    if (this.connection) {
      void this.connection.close().catch(() => undefined);
      this.connection = null;
    }
  }

  private static generateReservationCode(length = 10): string {
    let code = "";
    for (let i = 0; i < length; i += 1) {
      code +=
        this.reservationChars[
          Math.floor(Math.random() * this.reservationChars.length)
        ];
    }
    return code;
  }

  static async reserveConnection(): Promise<string> {
    if (this.reservationCode != null) {
      this.createNewConnection += 1;
      if (this.createNewConnection >= CREATE_NEW_CONNECTION_LIMIT) {
        this.createNewConnection = 0;
        return RESERVE_CONNECTION_ERRORS[0];
      }
      await sleep(CREATE_NEW_CONNECTION_DELAY_MS);
      return this.reserveConnection();
    }
    this.reservationCode = this.generateReservationCode();
    this.createNewConnection = 0;
    return this.reservationCode;
  }

  static async releaseConnection(reservationCode: string): Promise<string | null> {
    if (this.reservationCode == null) {
      return RESERVE_RELEASE_ERRORS[0];
    }
    if (this.reservationCode !== reservationCode) {
      return RESERVE_RELEASE_ERRORS[1];
    }
    this.reservationCode = null;
    this.createNewConnection = 0;
    return null;
  }

  private static async releaseOwnedReservation(
    reservationCode: string | null,
    ownedReservation: string | null,
  ): Promise<void> {
    if (reservationCode == null && ownedReservation) {
      await this.releaseConnection(ownedReservation);
    }
  }

  static async openConnection(): Promise<string | null> {
    if (this.connection != null) {
      return OPEN_CONNECTION_ERRORS[0];
    }

    const nav = navigator as Navigator & { serial?: Serial };
    if (!nav.serial) {
      return OPEN_CONNECTION_ERRORS[1];
    }

    try {
      const existingPorts = await nav.serial.getPorts();
      const port = existingPorts[0] ?? (await nav.serial.requestPort());
      await port.open({ baudRate: BAUD_RATE, dataBits: 8, stopBits: 1, parity: "none" });
      this.connection = port;
      return null;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (message.toLowerCase().includes("denied")) {
        return OPEN_CONNECTION_ERRORS[2];
      }
      this.watchDog += 1;
      if (this.watchDog >= WATCH_DOG_LIMIT) {
        this.watchDog = 0;
        return OPEN_CONNECTION_ERRORS[3];
      }
      await sleep(WATCH_DOG_DELAY_MS);
      return this.openConnection();
    }
  }

  static async closeConnection(): Promise<string | null> {
    if (this.connection == null) {
      return "already_closed";
    }
    try {
      await this.connection.close();
      this.connection = null;
      return null;
    } catch {
      this.watchDog += 1;
      if (this.watchDog >= WATCH_DOG_LIMIT) {
        this.watchDog = 0;
        this.connection = null;
        return "somwthing_went_wrong_in_close_connection";
      }
      await sleep(WATCH_DOG_DELAY_MS);
      return this.closeConnection();
    }
  }

  private static async readWithTimeout(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    timeoutMs: number,
  ): Promise<Uint8Array> {
    const deadline = Date.now() + timeoutMs;
    const chunks: Uint8Array[] = [];
    let totalLength = 0;

    while (totalLength < 1000 && Date.now() < deadline) {
      const remaining = deadline - Date.now();
      if (remaining <= 0) {
        break;
      }

      const result = await Promise.race([
        reader.read(),
        sleep(remaining).then(() => ({ done: true as const, value: undefined })),
      ]);

      if (result.done || !result.value) {
        break;
      }
      chunks.push(result.value);
      totalLength += result.value.length;
    }

    const merged = new Uint8Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    return merged;
  }

  static async sendData(
    data: string,
    options: {
      crcLength: number;
      crcGenerator: (payload: string) => string;
      reservationCode?: string | null;
      controlConnection?: boolean;
      haveResponse?: boolean;
    },
  ): Promise<MifareResponse> {
    const {
      crcLength,
      crcGenerator,
      reservationCode = null,
      controlConnection = true,
      haveResponse = true,
    } = options;

    let ownedReservation: string | null = null;
    const response: MifareResponse = { is_done: false };

    if (reservationCode != null) {
      if (this.reservationCode !== reservationCode) {
        this.watchDog = 0;
        response.error = "reservetion_code_is_not_match";
        return response;
      }
    } else {
      const reserved = await this.reserveConnection();
      if (RESERVE_CONNECTION_ERRORS.includes(reserved)) {
        this.watchDog = 0;
        response.error = reserved;
        return response;
      }
      ownedReservation = reserved;
    }

    const activeReservation = reservationCode ?? ownedReservation;

    try {
      if (controlConnection) {
        const openConnectionResponse = await this.openConnection();
        if (openConnectionResponse != null) {
          this.watchDog = 0;
          response.error = openConnectionResponse;
          return response;
        }
      }

      const payload = data + crcGenerator(data);
      const bytes = new Uint8Array(hexStrToIntList(payload));

      if (!this.connection?.writable) {
        response.error = "hardware_not_connected";
        return response;
      }

      const writer = this.connection.writable.getWriter();
      try {
        await writer.write(bytes);
      } finally {
        writer.releaseLock();
      }

      let responseString: string | null = null;

      if (haveResponse && this.connection.readable) {
        const reader = this.connection.readable.getReader();
        try {
          const received = await this.readWithTimeout(reader, READ_TIMEOUT_MS);
          if (received.length === 0) {
            this.watchDog += 1;
            if (this.watchDog >= WATCH_DOG_LIMIT) {
              this.watchDog = 0;
              response.error = "timeout";
              return response;
            }
            await sleep(WATCH_DOG_DELAY_MS);
            return this.sendData(data, {
              crcLength,
              crcGenerator,
              reservationCode: activeReservation,
              controlConnection: false,
              haveResponse,
            });
          }

          responseString = intListToHexStr(Array.from(received));
          const responseData = responseString.substring(
            0,
            responseString.length - crcLength,
          );
          const responseCrc = responseString.substring(responseString.length - crcLength);
          const generatedCrc = crcGenerator(responseData);
          if (responseCrc !== generatedCrc) {
            this.watchDog += 1;
            if (this.watchDog >= WATCH_DOG_LIMIT) {
              this.watchDog = 0;
              response.error = "crc_not_match";
              return response;
            }
            await sleep(WATCH_DOG_DELAY_MS);
            return this.sendData(data, {
              crcLength,
              crcGenerator,
              reservationCode: activeReservation,
              controlConnection: false,
              haveResponse,
            });
          }
        } finally {
          reader.releaseLock();
        }
      }

      if (controlConnection) {
        const closeConnectionResponse = await this.closeConnection();
        if (closeConnectionResponse != null) {
          this.watchDog = 0;
          response.error = closeConnectionResponse;
          return response;
        }
      }

      this.watchDog = 0;
      response.is_done = true;
      response.data = responseString;
      return response;
    } finally {
      if (controlConnection && this.connection != null) {
        await this.closeConnection();
      }
      await this.releaseOwnedReservation(reservationCode, ownedReservation);
    }
  }
}

async function sendChecked(
  data: string,
  dataType?: "string" | "int",
): Promise<MifareResponse> {
  const response = await HardwareBase.sendData(data, {
    crcLength: 2,
    crcGenerator: generateXor,
  });
  return checkResponse(response, dataType);
}

async function setBuzzerBeep(delayTime: number): Promise<MifareResponse> {
  const clamped = Math.min(delayTime, 255);
  const data = "AABB" + "0600" + "0000" + "0601" + intToHex(clamped, 1);
  return sendChecked(data);
}

async function setLedColor(options: { green?: boolean; red?: boolean } = {}): Promise<MifareResponse> {
  let colorData = 0;
  if (options.green) colorData += 2;
  if (options.red ?? true) colorData += 1;
  const data = "AABB" + "0600" + "0000" + "0701" + intToHex(colorData, 1);
  return sendChecked(data);
}

async function successAlert(): Promise<void> {
  await setBuzzerBeep(20);
  await setLedColor({ green: true, red: false });
  await sleep(50);
  await setLedColor();
}

export async function mifareRequest(): Promise<MifareResponse> {
  const data = "AABB" + "0600" + "0000" + "0102" + "52";
  return sendChecked(data, "string");
}

export async function mifareAnticollision(): Promise<MifareResponse> {
  return withHardwareLock(async () => {
    const requestResponse = await mifareRequest();
    if (!requestResponse.is_done) {
      if (requestResponse.error && MIFARE_INTERNAL_ERRORS.has(requestResponse.error)) {
        HardwareBase.forceReset();
      }
      return requestResponse;
    }

    const data = "AABB" + "0500" + "0000" + "0202";
    const checked = await sendChecked(data, "string");
    if (checked.error && MIFARE_INTERNAL_ERRORS.has(checked.error)) {
      HardwareBase.forceReset();
      return checked;
    }
    if (checked.is_done) {
      await successAlert();
    }
    return checked;
  });
}

export function isMifareSerialAvailable(): boolean {
  return "serial" in navigator;
}

export async function disconnectMifareReader(): Promise<void> {
  return withHardwareLock(async () => {
    HardwareBase.forceReset();
  });
}

export function isMifareInternalError(error: string | null | undefined): boolean {
  return Boolean(error && MIFARE_INTERNAL_ERRORS.has(error));
}
