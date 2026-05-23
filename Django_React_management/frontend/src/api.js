/**
 * API client for CustomerClub Management backend.
 * Uses JWT from localStorage (key: accessToken).
 */
import { parseApiError } from "./apiErrors.js";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

/**
 * Turn a stored media path or relative URL into an absolute URL the browser can load.
 * The SPA often runs on a different origin than Django, so relative /media/... would 404.
 */
export function resolveMediaUrl(imageField) {
  if (imageField == null || imageField === "") return "";
  const s = String(imageField).trim();
  if (!s) return "";
  if (s.startsWith("http://") || s.startsWith("https://")) return s;
  try {
    const u = new URL(API_BASE);
    const path = s.startsWith("/") ? s : `/${s}`;
    return `${u.origin}${path}`;
  } catch {
    return s;
  }
}

function getToken() {
  return localStorage.getItem("accessToken");
}

/** Authorization only (no Content-Type). Use with FormData so the browser sets multipart boundaries. */
function getAuthHeaders() {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

function getHeaders(useJson = true) {
  const headers = getAuthHeaders();
  if (useJson) headers["Content-Type"] = "application/json";
  return headers;
}

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  const data = await res.json();
  localStorage.setItem("accessToken", data.access);
  if (data.refresh) localStorage.setItem("refreshToken", data.refresh);
  return data;
}

export function logout() {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
}

export function isAuthenticated() {
  return !!getToken();
}

export async function register(data) {
  const res = await fetch(`${API_BASE}/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function fetchShops() {
  const res = await fetch(`${API_BASE}/shops/`, { headers: getHeaders() });
  if (!res.ok) throw new Error("بارگذاری فروشگاه‌ها ناموفق بود.");
  return res.json();
}

export async function fetchBranches(shopId) {
  const res = await fetch(`${API_BASE}/branches/?shop=${shopId}`, { headers: getHeaders() });
  if (!res.ok) throw new Error("بارگذاری شعب ناموفق بود.");
  const raw = await res.json();
  if (Array.isArray(raw)) {
    return {
      branches: raw,
      totalBranchesInShop: raw.length,
      can_create_branches: false,
    };
  }
  return {
    branches: raw.branches ?? [],
    totalBranchesInShop: Number(raw.total_branches_in_shop) || 0,
    can_create_branches: raw.can_create_branches === true,
  };
}

export async function createShop(payload) {
  const res = await fetch(`${API_BASE}/shops/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ name: payload.name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function createBranch(shopId, payload) {
  const res = await fetch(`${API_BASE}/branches/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ shop: Number(shopId), name: payload.name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function fetchCategories(shopId) {
  const res = await fetch(`${API_BASE}/categories/?shop=${shopId}`, { headers: getHeaders() });
  if (!res.ok) throw new Error("بارگذاری دسته‌بندی‌ها ناموفق بود.");
  return res.json();
}

export async function createCategory(shopId, data) {
  const res = await fetch(`${API_BASE}/categories/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ shop: shopId, ...data }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function fetchProducts(shopId, branchId = null) {
  let url = `${API_BASE}/products/?shop=${shopId}`;
  if (branchId) url += `&branch=${branchId}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) throw new Error("بارگذاری محصولات ناموفق بود.");
  return res.json();
}

export async function fetchProduct(id) {
  const res = await fetch(`${API_BASE}/products/${id}/`, { headers: getHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function createProduct(formData) {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE}/products/`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function updateProductOfferable(id, isOfferable) {
  const res = await fetch(`${API_BASE}/products/${id}/`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify({ is_offerable: isOfferable }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function updateProduct(id, formData) {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE}/products/${id}/`, {
    method: "PATCH",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function deleteProduct(id) {
  const res = await fetch(`${API_BASE}/products/${id}/`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
}

export async function fetchProfile() {
  const res = await fetch(`${API_BASE}/me/`, { headers: getHeaders() });
  if (!res.ok) throw new Error("بارگذاری پروفایل ناموفق بود.");
  return res.json();
}

export async function fetchBranchPermissions(shopId, updatePayload = null) {
  const url = `${API_BASE}/shop-branch-permissions/?shop=${shopId}`;
  if (!updatePayload) {
    const res = await fetch(url, { headers: getHeaders() });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseApiError(err));
    }
    return res.json();
  }

  const res = await fetch(`${API_BASE}/shop-branch-permissions/`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify({ shop: Number(shopId), ...updatePayload }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function updateProfile(data) {
  const isFormData = typeof FormData !== "undefined" && data instanceof FormData;
  const res = await fetch(`${API_BASE}/me/`, {
    method: "PATCH",
    headers: isFormData ? getAuthHeaders() : getHeaders(),
    body: isFormData ? data : JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function changePassword(currentPassword, newPassword) {
  const res = await fetch(`${API_BASE}/me/change-password/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const message = parseApiError(err);
    const fallback =
      res.status >= 500
        ? "خطای سرور. لطفاً دوباره تلاش کنید."
        : "تغییر رمز عبور ناموفق بود.";
    throw new Error(message && message !== "خطایی رخ داد." ? message : fallback);
  }
  return res.json();
}

export async function createShopKeeper(data) {
  const res = await fetch(`${API_BASE}/shop-keepers/`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function checkShopOwner() {
  const res = await fetch(`${API_BASE}/check-shop-owner/`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err) || "بررسی وضعیت فروشگاه ناموفق بود.");
  }
  return res.json();
}