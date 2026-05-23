"""

Fetch shop catalog from the management integration API.

"""

from __future__ import annotations



import logging

from typing import Any



from utils.management_cache import catalog_cache_ttl, get_cached_or_fetch, is_throttle_error

from utils.management_client import ManagementAPIError, management_configured, management_request



logger = logging.getLogger(__name__)





def _fetch_shop_catalog_live(shop_id: int) -> list[dict[str, Any]]:

    payload = management_request(

        "GET",

        "/api/integration/catalog/",

        params={"shop_id": shop_id},

    )

    if isinstance(payload, list):

        return payload

    return []





def fetch_shop_catalog(shop_id: int) -> list[dict[str, Any]] | None:

    if not management_configured():

        logger.warning("Management API is not configured; cannot fetch catalog")

        return None

    try:

        return get_cached_or_fetch(

            f"catalog:{shop_id}",

            lambda: _fetch_shop_catalog_live(shop_id),

            ttl=catalog_cache_ttl(),

        )

    except ManagementAPIError as exc:

        if is_throttle_error(exc):

            logger.warning(

                "Failed to fetch catalog from management (throttled): %s",

                exc,

            )

        else:

            logger.error("Failed to fetch catalog from management: %s", exc)

        return None

