const SHOP_STORAGE_KEY = "customerclub_selected_shop_id";

export function getSelectedShopId(): number | null {
  const raw = sessionStorage.getItem(SHOP_STORAGE_KEY);
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function setSelectedShopId(shopId: number): void {
  sessionStorage.setItem(SHOP_STORAGE_KEY, String(shopId));
}

export function clearSelectedShopId(): void {
  sessionStorage.removeItem(SHOP_STORAGE_KEY);
}
