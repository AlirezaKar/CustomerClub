"""
SMS login verification stored in cache only (no local User rows).
"""
from __future__ import annotations

import random

from django.conf import settings
from django.core.cache import cache

from utils.functions import sms as sms_functions


def _code_cache_key(phone_number: str) -> str:
    return f"stateless_login_code:{phone_number}"


def _resend_cache_key(phone_number: str) -> str:
    return f"stateless_sms_resend:{phone_number}"


def _generate_code() -> int:
    length = int(getattr(settings, "PHONE_NUMBER_VERIFICATION_CODE_LENGTH", 4))
    start = 10 ** (length - 1)
    end = (10 ** length) - 1
    return random.randint(start, end)


def send_login_code(phone_number: str) -> tuple[bool, int | str | None]:
    """
    Generate a code, store in cache, send SMS.
    Returns (ok, error_or_remaining_seconds).
    """
    phone_number = (phone_number or "").strip()
    code_life = int(getattr(settings, "PHONE_NUMBER_VERIFICATION_CODE_LIFE", 300))
    send_limit = int(getattr(settings, "PHONE_NUMBER_VERIFICATION_CODE_SEND_LIMIT", 60))
    max_resends = int(getattr(settings, "SMS_MAX_RESENDS_PER_SESSION", 5))
    session_ttl = int(
        getattr(settings, "SMS_RESEND_SESSION_TTL", code_life)
    )

    resend_key = _resend_cache_key(phone_number)
    current_resends = int(cache.get(resend_key) or 0)
    if current_resends >= max_resends:
        return False, "resend_limit_reached"

    last_send_key = f"stateless_sms_last_send:{phone_number}"
    last_send_ts = cache.get(last_send_key)
    if last_send_ts and not getattr(settings, "SMS_DEBUG_MODE", False):
        elapsed = int(__import__("time").time()) - int(last_send_ts)
        if elapsed < send_limit:
            return False, send_limit - elapsed

    code = _generate_code()
    cache.set(_code_cache_key(phone_number), code, timeout=code_life)
    cache.set(resend_key, current_resends + 1, timeout=session_ttl)
    cache.set(last_send_key, int(__import__("time").time()), timeout=session_ttl)

    code_str = str(code).zfill(
        int(getattr(settings, "PHONE_NUMBER_VERIFICATION_CODE_LENGTH", 4))
    )

    if getattr(settings, "SMS_DEBUG_MODE", False):
        print(f"\n{'=' * 50}\nStateless SMS DEBUG\nPhone: {phone_number}\nCode: {code_str}\n{'=' * 50}\n")
        return True, None

    ok = sms_functions.SMSService.send_verification_code(phone_number, code_str)
    if not ok:
        return False, "sms_failed"
    return True, None


def verify_login_code(phone_number: str, code: str) -> bool:
    phone_number = (phone_number or "").strip()
    try:
        submitted = int(str(code).strip())
    except (TypeError, ValueError):
        return False
    stored = cache.get(_code_cache_key(phone_number))
    if stored is None:
        return False
    if int(stored) != submitted:
        return False
    cache.delete(_code_cache_key(phone_number))
    try:
        cache.delete(f"stateless_sms_resend:{phone_number}")
    except Exception:
        pass
    return True
