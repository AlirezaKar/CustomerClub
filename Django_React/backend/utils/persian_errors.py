"""
Map API / validation errors to Persian messages for the public kiosk API.
"""
from __future__ import annotations

import re
from typing import Any

_EXACT: dict[str, str] = {
    "required phone_number": "شماره تلفن الزامی است.",
    "required age": "سن الزامی است.",
    "required gender": "جنسیت الزامی است.",
    "required shop_id": "انتخاب فروشگاه الزامی است.",
    "shop_not_found": "فروشگاه انتخاب‌شده یافت نشد.",
    "required send_login_verification_code or login_verification_code": (
        "ارسال یا وارد کردن کد پیامکی الزامی است."
    ),
    "card_uid is wrong": "کارت شناسایی نشد.",
    "phone_number is wrong": "شماره تلفن یافت نشد.",
    "product_id is wrong": "محصول یافت نشد.",
    "offer_not_assigned": "این پیشنهاد به شما تعلق ندارد.",
    "insufficient_score": "امتیاز کافی نیست.",
    "product_not_available": "محصول در دسترس نیست.",
    "Could not reach management server.": "ارتباط با سرور مدیریت برقرار نشد.",
    "The fields branch, second_id must make a unique set.": (
        "شناسه ثانویه وارد شده قبلا استفاده شده است"
    ),
}

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"unique set", re.I), "شناسه ثانویه وارد شده قبلا استفاده شده است"),
    (re.compile(r"already exists", re.I), "این مقدار قبلاً ثبت شده است"),
    (re.compile(r"not found", re.I), "مورد درخواستی یافت نشد"),
    (re.compile(r"required", re.I), "فیلد الزامی است"),
]


def translate_message(message: str) -> str:
    text = (message or "").strip()
    if not text:
        return "خطایی رخ داد."
    if text in _EXACT:
        return _EXACT[text]
    for pattern, persian in _PATTERNS:
        if pattern.search(text):
            return persian
    if re.search(r"[\u0600-\u06FF]", text):
        return text
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
