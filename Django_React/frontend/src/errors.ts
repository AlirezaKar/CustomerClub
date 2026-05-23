const CARD_ALREADY_MESSAGE = "کارت قبلا ثبت شده است";
const PHONE_ALREADY_MESSAGE = "شماره تلفن قبلا ثبت شده است";

/** Map signup / NFC registration API errors to user-facing Persian text. */
export function formatSignupError(
  message: string,
  status?: number,
  options?: { hasCard?: boolean },
): string {
  const text = (message || "").trim();
  const lower = text.toLowerCase();
  const hasCard = options?.hasCard ?? false;

  if (text.includes("کارت") || lower.includes("nfc") || lower.includes("uid")) {
    return CARD_ALREADY_MESSAGE;
  }
  if (text.includes("تلفن") || lower.includes("phone") || lower.includes("username")) {
    return PHONE_ALREADY_MESSAGE;
  }
  if (status === 409 && hasCard) {
    return CARD_ALREADY_MESSAGE;
  }
  if (status === 409) {
    return text || PHONE_ALREADY_MESSAGE;
  }
  if (
    hasCard &&
    (status === 500 || text === `خطا (${status})` || /^خطا \(\d+\)$/.test(text))
  ) {
    return CARD_ALREADY_MESSAGE;
  }
  if (text && !/^خطا \(\d+\)$/.test(text)) {
    return text;
  }
  return hasCard ? CARD_ALREADY_MESSAGE : "ثبت نام ناموفق بود.";
}
