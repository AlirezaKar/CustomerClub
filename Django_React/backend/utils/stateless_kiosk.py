"""
Stateless kiosk mode: no business data persisted on the main server.
"""
from __future__ import annotations

from django.conf import settings

from utils.management_client import management_configured
from utils.management_sync import fetch_customer_offers
from utils.stateless_profile import build_user_profile


def stateless_kiosk_enabled() -> bool:
    if not management_configured():
        return False
    return getattr(settings, "STATELESS_KIOSK", True)


def login_profile_for_user(
    mgmt_user: dict,
    *,
    shop_id: int | None = None,
) -> dict:
    phone_number = (mgmt_user.get("phone_number") or "").strip()
    offers_payload = fetch_customer_offers(phone_number, shop_id=shop_id) or []
    return build_user_profile(mgmt_user, offers=offers_payload, shop_id=shop_id)
