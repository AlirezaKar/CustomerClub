import type { AuthSession, JwtPair } from "./api";

const ACCESS_KEY = "access";
const REFRESH_KEY = "refresh";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: JwtPair): void {
  localStorage.setItem(ACCESS_KEY, tokens.access);
  localStorage.setItem(REFRESH_KEY, tokens.refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function applyAuthSession(session: AuthSession): void {
  setTokens({ access: session.access, refresh: session.refresh });
}

