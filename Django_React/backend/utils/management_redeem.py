"""
Redeem special offers on the management server only (stateless kiosk).
"""
from __future__ import annotations

import logging
from typing import Any

from utils.management_cache import invalidate_customer_offers_cache
from utils.management_client import ManagementAPIError, management_request

logger = logging.getLogger(__name__)


def redeem_special_offer(*, user_id: int, product_id: int) -> dict[str, Any]:
    payload = management_request(
        "POST",
        "/api/integration/redeem-special-offer/",
        json={
            "user_id": int(user_id),
            "product_id": int(product_id),
        },
    )
    user = payload.get("user")
    if not isinstance(user, dict) or user.get("id") is None:
        logger.error("Management redeem returned unexpected payload: %s", payload)
        raise ManagementAPIError("Invalid response from management server.")

    phone_number = (user.get("phone_number") or "").strip()
    if phone_number:
        transaction = payload.get("transaction") if isinstance(payload.get("transaction"), dict) else {}
        product = transaction.get("product") if isinstance(transaction.get("product"), dict) else {}
        shop_id = product.get("shop_id")
        try:
            shop_id = int(shop_id) if shop_id is not None else None
        except (TypeError, ValueError):
            shop_id = None
        invalidate_customer_offers_cache(phone_number, shop_id=shop_id)

    return payload
