import type { Category, ShopOption, UserProfile } from "./types";
import { formatSignupError } from "./errors";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001/api/v1";

type JsonRecord = Record<string, unknown>;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    const message =
      (typeof errorPayload.error === "string" && errorPayload.error) ||
      (typeof errorPayload.detail === "string" && errorPayload.detail) ||
      (Array.isArray(errorPayload.non_field_errors) &&
        String(errorPayload.non_field_errors[0])) ||
      `خطا (${response.status})`;
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json().catch(() => undefined)) as T;
}

async function requestJsonWithMeta(
  path: string,
  init?: RequestInit,
): Promise<{
  ok: boolean;
  status: number;
  data: JsonRecord;
  headers: Headers;
}> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
    });
  } catch (err) {
    const e = new Error("Network error. Please check your internet connection.");
    (e as any).cause = err;
    (e as any).status = 0;
    throw e;
  }

  const data = (await response.json().catch(() => ({}))) as JsonRecord;
  return { ok: response.ok, status: response.status, data, headers: response.headers };
}

function authHeaders(accessToken: string): Record<string, string> {
  return { Authorization: `Bearer ${accessToken}` };
}

export class SmsSendLimitError extends Error {
  remainingSeconds: number;

  constructor(remainingSeconds: number) {
    super(`Please wait ${remainingSeconds} seconds before resend.`);
    this.name = "SmsSendLimitError";
    this.remainingSeconds = remainingSeconds;
  }
}

export async function fetchPublicShops(): Promise<ShopOption[]> {
  const payload = await request<{ shops: ShopOption[] }>("/public/shops/");
  return payload.shops ?? [];
}

export async function signupUser(payload: {
  phone_number: string;
  age: number;
  gender: "male" | "female";
  uid_code?: string;
  card_uid?: string;
}): Promise<void> {
  const hasCard = Boolean(payload.uid_code || payload.card_uid);
  const response = await fetch(`${API_BASE_URL}/user/signup/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorPayload = (await response.json().catch(() => ({}))) as JsonRecord;
    const rawMessage =
      (typeof errorPayload.error === "string" && errorPayload.error) ||
      (typeof errorPayload.detail === "string" && errorPayload.detail) ||
      `خطا (${response.status})`;
    throw new Error(
      formatSignupError(rawMessage, response.status, { hasCard }),
    );
  }
}

export async function sendLoginCode(
  phoneNumber: string,
  shopId: number,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/user/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      phone_number: phoneNumber,
      shop_id: shopId,
      send_login_verification_code: true,
    }),
  });
  if (response.status === 425) {
    const payload = await response.json().catch(() => ({}));
    throw new SmsSendLimitError(Number(payload.time ?? 0));
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error ?? "Could not send SMS code.");
  }
}

export async function verifyLoginCode(payload: {
  phone_number: string;
  login_verification_code: string;
  shop_id: number;
}): Promise<AuthSession> {
  return request<AuthSession>("/user/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function loginByCard(
  uidCode: string,
  shopId: number,
): Promise<AuthSession> {
  return request<AuthSession>("/user/login/", {
    method: "POST",
    body: JSON.stringify({
      uid_code: uidCode,
      shop_id: shopId,
    }),
  });
}

/** Exchange one-time NFC token (from bridge redirect) for user profile. */
export async function nfcCompleteLogin(
  token: string,
  shopId: number,
): Promise<UserProfile> {
  return request<UserProfile>("/nfc-complete/", {
    method: "POST",
    body: JSON.stringify({ token, shop_id: shopId }),
  });
}

export async function fetchCategories(shopId?: number): Promise<Category[]> {
  const query = typeof shopId === "number" ? `?shop_id=${shopId}` : "";
  return request<Category[]>(`/shop/settings/categories/${query}`);
}

export async function submitOfferUse(payload: {
  phone_number: string;
  product_id: number;
}): Promise<UserProfile> {
  return request<UserProfile>("/user/submit-offer/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type JwtPair = { access: string; refresh: string };
export type AuthSession = JwtPair & { user: UserProfile };

export class NfcLockedError extends Error {
  retryAfterSeconds: number | null;

  constructor(retryAfterSeconds: number | null) {
    super(
      retryAfterSeconds != null
        ? `Too many attempts. Try again in ${Math.ceil(retryAfterSeconds / 60)} minutes.`
        : "Too many attempts. Try again later.",
    );
    this.name = "NfcLockedError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export async function nfcJwtLogin(
  uidCode: string,
  shopId: number,
): Promise<AuthSession> {
  const { ok, status, data } = await requestJsonWithMeta("/user/nfc/login/", {
    method: "POST",
    body: JSON.stringify({ uid_code: uidCode, shop_id: shopId }),
  });

  if (ok) {
    return {
      access: String(data.access ?? ""),
      refresh: String(data.refresh ?? ""),
      user: data.user as unknown as UserProfile,
    };
  }

  if (status === 423) {
    const retryAfter = data.retry_after != null ? Number(data.retry_after) : null;
    throw new NfcLockedError(Number.isFinite(retryAfter) ? retryAfter : null);
  }

  const message = String(data.error ?? `Request failed with status ${status}`);
  const err = new Error(message);
  (err as any).status = status;
  throw err;
}

export async function nfcRegisterTag(
  uid: string,
  accessToken: string,
): Promise<{ uid: string; tag_id: number }> {
  const { ok, status, data } = await requestJsonWithMeta("/user/nfc/register/", {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({ uid }),
  });

  if (ok) {
    return { uid: String(data.uid ?? ""), tag_id: Number(data.tag_id ?? 0) };
  }

  const rawMessage = String(data.error ?? `Request failed with status ${status}`);
  const err = new Error(formatSignupError(rawMessage, status, { hasCard: true }));
  (err as any).status = status;
  throw err;
}

export async function nfcStatus(accessToken: string): Promise<{
  has_active_nfc_tags: boolean;
  tags: Array<{
    id: number;
    uid: string;
    is_active: boolean;
    created_at: string;
    last_used_at: string | null;
    failed_attempts: number;
    locked_until: string | null;
  }>;
}> {
  return request("/user/nfc/status/", {
    method: "GET",
    headers: authHeaders(accessToken),
  });
}

export async function nfcUnlinkTag(
  payload: { uid?: string; tag_id?: number },
  accessToken: string,
): Promise<void> {
  await request<void>("/user/nfc/unlink/", {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(payload),
  });
}
