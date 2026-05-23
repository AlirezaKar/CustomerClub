/**
 * Stable per-card identifier stored on the management server as card_uid / uid_code.
 * Matches backend NFCTag.hash_uid (SHA-256 hex of normalized raw scanner UID).
 */
export async function deriveCardUidCode(rawUid: string): Promise<string> {
  const normalized = (rawUid || "").trim().toLowerCase();
  if (!normalized) {
    return "";
  }
  const encoded = new TextEncoder().encode(normalized);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}
