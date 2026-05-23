"""
Cache management API responses to avoid hammering the management server.

On HTTP 429 (throttle) or transient errors, returns the last known good payload
when available so kiosk login and shop listing keep working.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from django.conf import settings
from django.core.cache import cache

from utils.management_client import ManagementAPIError

logger = logging.getLogger(__name__)

T = TypeVar("T")

_CACHE_PREFIX = "mgmt:v1:"
_STALE_SUFFIX = ":stale"
_CACHE_MISS = object()


def _ttl(name: str, default: int) -> int:
    return int(getattr(settings, name, default))


def shops_cache_ttl() -> int:
    return _ttl("MANAGEMENT_CACHE_TTL_SHOPS", 600)


def catalog_cache_ttl() -> int:
    return _ttl("MANAGEMENT_CACHE_TTL_CATALOG", 300)


def offers_cache_ttl() -> int:
    return _ttl("MANAGEMENT_CACHE_TTL_OFFERS", 120)


def stale_cache_ttl(active_ttl: int) -> int:
    multiplier = int(getattr(settings, "MANAGEMENT_CACHE_STALE_MULTIPLIER", 24))
    return max(active_ttl * multiplier, active_ttl + 60)


def is_throttle_error(exc: ManagementAPIError) -> bool:
    if exc.status_code == 429:
        return True
    message = str(exc).lower()
    return "throttl" in message or "rate limit" in message


def invalidate_customer_offers_cache(
    phone_number: str,
    shop_id: int | None = None,
) -> None:
    phone_number = (phone_number or "").strip()
    if not phone_number:
        return
    keys = {f"offers:{phone_number}:all"}
    if shop_id is not None:
        keys.add(f"offers:{phone_number}:{shop_id}")
    for key in keys:
        cache.delete(f"{_CACHE_PREFIX}{key}")
        cache.delete(f"{_CACHE_PREFIX}{key}{_STALE_SUFFIX}")


def get_cached_or_fetch(
    cache_key: str,
    fetcher: Callable[[], T | None],
    *,
    ttl: int,
    allow_none: bool = False,
) -> T | None:
    """
    Return a cached value or call ``fetcher``.

    ``allow_none``: when True, cached ``None`` is treated as a valid result
    (e.g. user not found). When False, only non-None results are cached.
    """
    full_key = f"{_CACHE_PREFIX}{cache_key}"
    stale_key = f"{full_key}{_STALE_SUFFIX}"

    cached = cache.get(full_key, _CACHE_MISS)
    if cached is not _CACHE_MISS:
        return cached

    try:
        value = fetcher()
    except ManagementAPIError as exc:
        stale = cache.get(stale_key)
        if stale is not None and (is_throttle_error(exc) or exc.status_code in (502, 503, 504)):
            logger.warning(
                "Management API unavailable (%s); using stale cache for %s",
                exc,
                cache_key,
            )
            return stale
        raise

    if value is not None or allow_none:
        cache.set(full_key, value, ttl)
        cache.set(stale_key, value, stale_cache_ttl(ttl))
    return value
