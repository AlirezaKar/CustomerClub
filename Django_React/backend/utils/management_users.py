"""
End-user registration and lookup via the management server (source of truth).
"""
from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth import get_user_model

from utils.card_uid import card_lookup_candidates, normalize_card_identifier
from utils.management_client import ManagementAPIError, management_request

logger = logging.getLogger(__name__)
User = get_user_model()

_INTEGRATION_END_USERS = "/api/integration/end-users/"


def lookup_end_user_by_id(user_id: int) -> dict[str, Any] | None:
    try:
        payload = management_request(
            "GET",
            _INTEGRATION_END_USERS,
            params={"user_id": int(user_id)},
        )
    except ManagementAPIError:
        raise
    if not payload.get("exists"):
        return None
    user = payload.get("user")
    return user if isinstance(user, dict) else None


def lookup_end_user(phone_number: str) -> dict[str, Any] | None:
    """
    Return management end-user payload if registered, else None.
    Raises ManagementAPIError on transport/config failures.
    """
    phone_number = (phone_number or "").strip()
    payload = management_request(
        "GET",
        _INTEGRATION_END_USERS,
        params={"phone_number": phone_number},
    )
    if not payload.get("exists"):
        return None
    user = payload.get("user")
    return user if isinstance(user, dict) else None


def lookup_end_user_by_card_uid(card_uid: str) -> dict[str, Any] | None:
    """
    Return management end-user payload for a registered NFC card UID, else None.
    Raises ManagementAPIError on transport/config failures.
    """
    for candidate in card_lookup_candidates(card_uid):
        payload = management_request(
            "GET",
            _INTEGRATION_END_USERS,
            params={"uid_code": candidate},
        )
        if payload.get("exists"):
            user = payload.get("user")
            return user if isinstance(user, dict) else None
    return None


def register_end_user(
    *,
    phone_number: str,
    age: int,
    gender: str,
    card_uid: str | None = None,
    uid_code: str | None = None,
) -> dict[str, Any]:
    """Create end user on management; returns user payload."""
    resolved_uid = normalize_card_identifier((uid_code or card_uid or "").strip())
    body: dict[str, Any] = {
        "phone_number": phone_number,
        "age": age,
        "gender": gender,
    }
    if resolved_uid:
        body["uid_code"] = resolved_uid
    payload = management_request("POST", _INTEGRATION_END_USERS, json=body)
    user = payload.get("user")
    if not isinstance(user, dict) or not user.get("id"):
        logger.error("Management register returned unexpected payload: %s", payload)
        raise ManagementAPIError("Invalid response from management server.")
    return user


def mirror_end_user_from_management(mgmt_user: dict[str, Any]) -> User:
    """Ensure a local User row exists with the same primary key as management."""
    user_id = mgmt_user["id"]
    phone_number = mgmt_user.get("phone_number") or ""
    username = mgmt_user.get("username") or phone_number or str(user_id)

    defaults = {
        "username": username,
        "phone_number": phone_number or None,
        "age": mgmt_user.get("age"),
        "gender": mgmt_user.get("gender") or "",
        "card_uid": mgmt_user.get("card_uid"),
        "score": int(mgmt_user.get("score") or 0),
    }
    user, created = User.objects.update_or_create(pk=user_id, defaults=defaults)
    if created:
        user.set_unusable_password()
        user.save(update_fields=[])
    return user
