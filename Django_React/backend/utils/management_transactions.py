"""
Notify the management server after a special-offer redemption on the main kiosk API.
"""
from __future__ import annotations

import logging
from typing import Any

from utils.management_client import ManagementAPIError, management_request

logger = logging.getLogger(__name__)

_INTEGRATION_OFFER_SUBMIT = "/api/integration/special-offer-transactions/"


def record_special_offer_on_management(
    *,
    user_id: int,
    product_id: int,
    user_score: int,
) -> dict[str, Any]:
    """
    Mirror a completed offer redemption on management (score ledger entry + score sync).
    """
    payload = management_request(
        "POST",
        _INTEGRATION_OFFER_SUBMIT,
        json={
            "user_id": int(user_id),
            "product_id": int(product_id),
            "user_score": int(user_score),
        },
    )
    transaction_data = payload.get("transaction")
    if not isinstance(transaction_data, dict) or transaction_data.get("id") is None:
        logger.error("Management offer record returned unexpected payload: %s", payload)
        raise ManagementAPIError("Invalid response from management server.")
    return payload
