"""
Build kiosk API user payloads from management integration responses.
"""
from __future__ import annotations

from typing import Any


def _product_from_offer_payload(product_data: dict[str, Any]) -> dict[str, Any]:
    category = product_data.get("category") or {}
    return {
        "id": product_data.get("id"),
        "second_id": product_data.get("second_id"),
        "title": product_data.get("title") or "",
        "price": product_data.get("price") or 0,
        "score": product_data.get("score") or 0,
        "image_url": product_data.get("image_url"),
        "is_offerable": product_data.get("is_offerable", False),
        "is_active": product_data.get("is_active", True),
        "category_id": category.get("id"),
        "category_title": category.get("title"),
    }


def offers_to_useroffer_set(offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for offer in offers:
        product_data = offer.get("product") or {}
        if not product_data.get("id"):
            continue
        result.append(
            {
                "product": _product_from_offer_payload(product_data),
                "offer_rate": int(offer.get("offer_rate") or 0),
            }
        )
    return result


def build_user_profile(
    mgmt_user: dict[str, Any],
    *,
    offers: list[dict[str, Any]] | None = None,
    shop_id: int | None = None,
) -> dict[str, Any]:
    """Shape matching module_account.serializers.UserSerializer output."""
    user_score = int(mgmt_user.get("score") or 0)
    offer_rows = offers if offers is not None else []
    useroffer_set = offers_to_useroffer_set(offer_rows)

    if shop_id is not None:
        filtered_offers = []
        for offer in offer_rows:
            product_data = offer.get("product") or {}
            shop_data = product_data.get("shop") or {}
            if shop_data.get("id") == shop_id:
                filtered_offers.append(offer)
        useroffer_set = offers_to_useroffer_set(filtered_offers)

    return {
        "first_name": mgmt_user.get("first_name") or "",
        "last_name": mgmt_user.get("last_name") or "",
        "phone_number": mgmt_user.get("phone_number") or "",
        "score": user_score,
        "useroffer_set": useroffer_set,
    }

