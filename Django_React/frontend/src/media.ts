const MANAGEMENT_ORIGIN = (
  import.meta.env.VITE_MANAGEMENT_API_BASE_URL ?? "http://127.0.0.1:8000"
)
  .replace(/\/api\/?$/, "")
  .replace(/\/$/, "");

const PLACEHOLDER_IMAGE =
  "data:image/svg+xml," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200"><rect fill="#eefaf3" width="200" height="200"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#1fa86c" font-family="sans-serif" font-size="14">بدون تصویر</text></svg>',
  );

/** Resolve product image URLs from main or management media servers. */
export function resolveProductImageUrl(url?: string | null): string {
  if (!url) return PLACEHOLDER_IMAGE;
  const trimmed = url.trim();
  if (!trimmed) return PLACEHOLDER_IMAGE;
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  const path = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  return `${MANAGEMENT_ORIGIN}${path}`;
}
