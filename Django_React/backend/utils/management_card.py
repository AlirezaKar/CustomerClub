"""
Link or unlink NFC card UID on the management server.
"""
from __future__ import annotations

import logging
from typing import Any

from utils.card_uid import normalize_card_identifier
from utils.management_client import ManagementAPIError, management_request

logger = logging.getLogger(__name__)


def link_end_user_card(*, user_id: int, card_uid: str) -> dict[str, Any]:
    stable_uid = normalize_card_identifier(card_uid)
    payload = management_request(
        "POST",
        "/api/integration/end-users/card/",
        json={"user_id": int(user_id), "uid": stable_uid},
    )
    user = payload.get("user")
    if not isinstance(user, dict):
        raise ManagementAPIError("Invalid response from management server.")
    return payload


def unlink_end_user_card(*, user_id: int) -> dict[str, Any]:
    payload = management_request(
        "DELETE",
        "/api/integration/end-users/card/",
        json={"user_id": int(user_id)},
    )
    user = payload.get("user")
    if not isinstance(user, dict):
        raise ManagementAPIError("Invalid response from management server.")
    return payload
