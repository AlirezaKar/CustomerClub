"""
Fetch shop list from the management server for public kiosk shop selection.
"""
from __future__ import annotations

import logging
from typing import Any

from utils.management_cache import get_cached_or_fetch, is_throttle_error, shops_cache_ttl
from utils.management_client import ManagementAPIError, management_configured, management_request

logger = logging.getLogger(__name__)


def _fetch_management_shops_live() -> list[dict[str, Any]] | None:
    payload = management_request("GET", "/api/integration/shops/")
    shops = payload.get("shops")
    return shops if isinstance(shops, list) else []


def fetch_management_shops() -> list[dict[str, Any]] | None:
    if not management_configured():
        logger.warning("Management API is not configured; cannot list shops")
        return None

    try:
        return get_cached_or_fetch(
            "shops",
            _fetch_management_shops_live,
            ttl=shops_cache_ttl(),
        )
    except ManagementAPIError as exc:
        if is_throttle_error(exc):
            logger.warning("Failed to fetch shops from management (throttled): %s", exc)
        else:
            logger.error("Failed to fetch shops from management: %s", exc)
        return None
