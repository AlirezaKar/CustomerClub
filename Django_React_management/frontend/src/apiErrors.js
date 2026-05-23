/**
 * Extract a user-facing message from a management API error payload.
 */
function firstFieldMessage(value) {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (Array.isArray(value) && value[0]) return String(value[0]);
  if (value && typeof value === "object") {
    for (const nested of Object.values(value)) {
      const found = firstFieldMessage(nested);
      if (found) return found;
    }
  }
  return null;
}

export function parseApiError(err) {
  if (err == null) return "خطایی رخ داد.";
  if (typeof err === "string") {
    const text = err.trim();
    return text && text !== "{}" ? text : "خطایی رخ داد.";
  }
  if (typeof err.error === "string" && err.error.trim()) return err.error.trim();
  if (typeof err.detail === "string" && err.detail.trim()) return err.detail.trim();
  if (Array.isArray(err.non_field_errors) && err.non_field_errors[0]) {
    return String(err.non_field_errors[0]);
  }
  for (const value of Object.values(err)) {
    const found = firstFieldMessage(value);
    if (found) return found;
  }
  if (typeof err === "object" && Object.keys(err).length === 0) {
    return "خطایی رخ داد.";
  }
  return "خطایی رخ داد.";
}
