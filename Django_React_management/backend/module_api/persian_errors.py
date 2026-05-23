"""
Map API / validation errors to Persian messages for clients.
"""
from __future__ import annotations

import re
from typing import Any

from rest_framework.response import Response


def _normalize_key(message: str) -> str:
    return " ".join((message or "").strip().split())


# Exact English strings → Persian (keys are normalized: single spaces)
_EXACT: dict[str, str] = {
    "This field is required.": "این فیلد الزامی است.",
    "This field may not be null.": "این فیلد نمی‌تواند خالی باشد.",
    "This field may not be blank.": "این فیلد نمی‌تواند خالی باشد.",
    "Enter a valid email address.": "ایمیل وارد شده معتبر نیست.",
    "Enter a valid value.": "مقدار وارد شده معتبر نیست.",
    "A valid integer is required.": "عدد صحیح معتبر وارد کنید.",
    "A valid number is required.": "عدد معتبر وارد کنید.",
    "Login failed": "ورود ناموفق بود.",
    "Failed to load shops": "بارگذاری فروشگاه‌ها ناموفق بود.",
    "Failed to load branches": "بارگذاری شعب ناموفق بود.",
    "Failed to load categories": "بارگذاری دسته‌بندی‌ها ناموفق بود.",
    "Failed to load products": "بارگذاری محصولات ناموفق بود.",
    "Failed to load product": "بارگذاری محصول ناموفق بود.",
    "Failed to load profile": "بارگذاری پروفایل ناموفق بود.",
    "Failed to check shop status": "بررسی وضعیت فروشگاه ناموفق بود.",
    "Shop not found": "فروشگاه یافت نشد.",
    "Branch not found": "شعبه یافت نشد.",
    "Product not found": "محصول یافت نشد.",
    "User not found": "کاربر یافت نشد.",
    "Branch is required.": "انتخاب شعبه الزامی است.",
    "You cannot manage this shop.": "شما به این فروشگاه دسترسی ندارید.",
    "You cannot manage this branch.": "شما به این شعبه دسترسی ندارید.",
    "Branch must belong to the selected shop.": "شعبه باید متعلق به همان فروشگاه باشد.",
    "Only the shop manager can create products.": "فقط مدیر فروشگاه می‌تواند محصول ایجاد کند.",
    "You cannot add products to this shop.": "امکان افزودن محصول به این فروشگاه وجود ندارد.",
    "You cannot add products to this branch.": "امکان افزودن محصول به این شعبه وجود ندارد.",
    "Query param 'shop' (shop id) is required": "شناسه فروشگاه الزامی است.",
    "Invalid branch": "شعبه نامعتبر است.",
    "phone_number query parameter is required": "شماره تلفن الزامی است.",
    "shop_id query parameter is required": "شناسه فروشگاه الزامی است.",
    "shop_id must be an integer": "شناسه فروشگاه باید عدد باشد.",
    "Phone number must be 11 digits.": "شماره تلفن باید ۱۱ رقم باشد.",
    "card_uid already exists": "کارت NFC قبلاً ثبت شده است.",
    "A user with this username already exists.": "نام کاربری قبلاً استفاده شده است.",
    "A user with this phone number already exists.": "شماره تلفن قبلاً ثبت شده است.",
    "Ensure this field has at least 8 characters.": "رمز عبور باید حداقل ۸ کاراکتر باشد.",
    "Current password is incorrect.": "رمز عبور فعلی نادرست است.",
    "Password updated.": "رمز عبور به‌روزرسانی شد.",
    "The fields branch, second_id must make a unique set.": (
        "شناسه ثانویه وارد شده قبلا استفاده شده است"
    ),
    "You are not allowed to create a shop.": "شما مجاز به ایجاد فروشگاه نیستید.",
    "You already manage at least one shop.": "شما از قبل حداقل یک فروشگاه را مدیریت می‌کنید.",
    "Only the shop manager can create branches.": "فقط مدیر فروشگاه می‌تواند شعبه ایجاد کند.",
    "You cannot add branches to this shop.": "امکان افزودن شعبه به این فروشگاه وجود ندارد.",
    "Only the shop manager can create categories.": "فقط مدیر فروشگاه می‌تواند دسته‌بندی ایجاد کند.",
    "You cannot create categories for this branch.": "امکان ایجاد دسته‌بندی برای این شعبه وجود ندارد.",
    "Branch managers may only change whether a product is offerable.": (
        "مدیران شعبه فقط می‌توانند وضعیت «قابل پیشنهاد» محصول را تغییر دهند."
    ),
    "You cannot edit this product.": "امکان ویرایش این محصول وجود ندارد.",
    "Only the shop manager can edit products.": "فقط مدیر فروشگاه می‌تواند محصول را ویرایش کند.",
    "Only the shop manager can delete products.": "فقط مدیر فروشگاه می‌تواند محصول را حذف کند.",
    "Only shop managers or staff can create branch manager accounts.": (
        "فقط مدیر فروشگاه یا کارکنان سایت می‌توانند حساب مدیر شعبه ایجاد کنند."
    ),
    "Fields 'shop' and 'user_id' are required.": "فیلدهای «فروشگاه» و «شناسه کاربر» الزامی هستند.",
    "This account could not be promoted to shop manager. Use branch permissions for branch staff, or register a new shop manager account.": (
        "ارتقای این حساب به مدیر فروشگاه ممکن نیست. برای پرسنل شعبه از دسترسی شعب استفاده کنید، "
        "یا حساب جدید با نقش مدیر فروشگاه ثبت کنید."
    ),
    "Only shop manager or branch manager accounts can own a shop. End-user accounts cannot be assigned as shop manager.": (
        "فقط حساب‌های مدیر فروشگاه یا مدیر شعبه می‌توانند مالک فروشگاه باشند. "
        "حساب‌های مشتری (کاربر نهایی) قابل واگذاری به‌عنوان مدیر فروشگاه نیستند."
    ),
    "This account does not have a valid shop manager profile. Ask them to register as a shop manager.": (
        "این حساب پروفایل معتبر مدیر فروشگاه ندارد. از او بخواهید با نقش مدیر فروشگاه ثبت‌نام کند."
    ),
    "This user already manages another shop. They cannot be assigned as manager of this shop.": (
        "این کاربر از قبل فروشگاه دیگری را مدیریت می‌کند و نمی‌تواند مدیر این فروشگاه شود."
    ),
    "You are the shop manager (owner). Branch permissions apply to branch manager accounts. To give someone else ownership, select a shop manager account and enable «Assign as shop manager».": (
        "شما مدیر (مالک) فروشگاه هستید. دسترسی شعب برای حساب‌های مدیر شعبه است. "
        "برای واگذاری مالکیت به دیگری، یک حساب مدیر فروشگاه انتخاب کنید و «واگذاری مدیریت فروشگاه» را فعال کنید."
    ),
    "Branch permissions apply only to branch manager accounts. To make this user the shop owner, they must register with the shop manager role and you must enable «Assign as shop manager».": (
        "دسترسی شعب فقط برای حساب‌های مدیر شعبه است. برای مالک فروشگاه کردن این کاربر، "
        "باید با نقش مدیر فروشگاه ثبت‌نام کند و گزینه «واگذاری مدیریت فروشگاه» را فعال کنید."
    ),
    "Name is required.": "نام الزامی است.",
    "Request context is required.": "خطای داخلی درخواست.",
    "Product instance is required for update.": "خطای داخلی در به‌روزرسانی محصول.",
    "Authentication required.": "لطفاً وارد حساب کاربری شوید.",
    "Invalid shop.": "فروشگاه نامعتبر است.",
    "You must own a shop to create accounts.": "برای ایجاد حساب باید مالک یک فروشگاه باشید.",
    "You do not own this shop.": "شما مالک این فروشگاه نیستید.",
    "Select a shop when you own more than one.": "وقتی بیش از یک فروشگاه دارید، فروشگاه را انتخاب کنید.",
}

# Build normalized lookup
_EXACT_NORM: dict[str, str] = {_normalize_key(k): v for k, v in _EXACT.items()}

# Substring patterns (regex) → Persian — avoid overly broad rules like bare "permission"
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"unique set", re.I), "شناسه ثانویه وارد شده قبلا استفاده شده است"),
    (re.compile(r"already exists", re.I), "این مقدار قبلاً ثبت شده است"),
    (re.compile(r"not found", re.I), "مورد درخواستی یافت نشد"),
    (re.compile(r"authentication credentials", re.I), "لطفاً وارد حساب کاربری شوید"),
]


def translate_message(message: str) -> str:
    text = _normalize_key(message)
    if not text:
        return "خطایی رخ داد."
    if text in _EXACT_NORM:
        return _EXACT_NORM[text]
    if text in _EXACT:
        return _EXACT[text]
    for pattern, persian in _PATTERNS:
        if pattern.search(text):
            return persian
    if re.search(r"[\u0600-\u06FF]", text):
        return message.strip()
    return text


def _first_from_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        return _first_from_value(value[0])
    if isinstance(value, dict):
        if "error" in value:
            return _first_from_value(value["error"])
        for nested in value.values():
            found = _first_from_value(nested)
            if found:
                return found
    return None


def extract_error_message(payload: Any) -> str:
    """Return a single Persian-friendly error string from an API error payload."""
    if payload is None:
        return "خطایی رخ داد."
    if isinstance(payload, str):
        return translate_message(payload)
    if not isinstance(payload, dict):
        return "خطایی رخ داد."

    if isinstance(payload.get("error"), str):
        return translate_message(payload["error"])

    if isinstance(payload.get("detail"), str):
        return translate_message(payload["detail"])

    for key in ("non_field_errors", "__all__"):
        if key in payload:
            msg = _first_from_value(payload[key])
            if msg:
                return translate_message(msg)

    for field_errors in payload.values():
        msg = _first_from_value(field_errors)
        if msg:
            return translate_message(msg)

    return "خطایی رخ داد."


def errors_response(errors: Any, status_code: int = 400) -> dict[str, str]:
    """Normalize serializer errors to {\"error\": \"...\"}."""
    return {"error": extract_error_message(errors)}


def error_response(message: str, status_code: int = 400) -> Response:
    """DRF response with a translated Persian error body."""
    return Response({"error": translate_message(message)}, status=status_code)


def integrity_conflict_message(exc: Exception) -> str:
    """Map database unique violations to kiosk-friendly Persian messages."""
    text = str(exc).lower()
    if "card_uid" in text:
        return "کارت قبلا ثبت شده است"
    if "phone_number" in text:
        return "شماره تلفن قبلا ثبت شده است"
    if "username" in text:
        return "شماره تلفن قبلا ثبت شده است"
    if "unique" in text or "duplicate" in text:
        return "این اطلاعات قبلاً ثبت شده است."
    return "ثبت نام ناموفق بود."
