"""
Pull customer offers from the management API and mirror related rows in the main database.

Uses the same primary keys as the management database so instances align across a shared DB.
"""
import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from module_product.models import Category, Product, UserSpecialOffer
from module_shop.models import Branch, Shop
from utils.management_cache import (
    get_cached_or_fetch,
    is_throttle_error,
    offers_cache_ttl,
)
from utils.management_client import ManagementAPIError, management_configured, management_request

logger = logging.getLogger(__name__)
User = get_user_model()

_SYNC_OWNER_USERNAME = "__management_sync__"


def _sync_owner() -> User:
    owner, created = User.objects.get_or_create(
        username=_SYNC_OWNER_USERNAME,
        defaults={"phone_number": None},
    )
    if created:
        owner.set_unusable_password()
        owner.save(update_fields=[])
    return owner


def _fetch_customer_offers_live(
    phone_number: str,
    shop_id: int | None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"phone_number": phone_number}
    if shop_id is not None:
        params["shop_id"] = shop_id
    payload = management_request(
        "GET",
        "/api/integration/customer-offers/",
        params=params,
    )
    return payload.get("offers") or []


def fetch_customer_offers(
    phone_number: str,
    shop_id: int | None = None,
) -> list[dict[str, Any]] | None:
    if not management_configured():
        logger.warning("Management API is not configured; skipping offer sync")
        return None

    phone_number = (phone_number or "").strip()
    if not phone_number:
        return []

    shop_part = shop_id if shop_id is not None else "all"
    cache_key = f"offers:{phone_number}:{shop_part}"

    try:
        return get_cached_or_fetch(
            cache_key,
            lambda: _fetch_customer_offers_live(phone_number, shop_id),
            ttl=offers_cache_ttl(),
        )
    except ManagementAPIError as exc:
        if is_throttle_error(exc):
            logger.warning(
                "Failed to fetch customer offers from management (throttled): %s",
                exc,
            )
        else:
            logger.error("Failed to fetch customer offers from management: %s", exc)
        return None


def _upsert_shop(shop_data: dict[str, Any], owner: User) -> Shop | None:
    shop_id = shop_data.get("id")
    if not shop_id:
        return None
    shop, _ = Shop.objects.update_or_create(
        pk=shop_id,
        defaults={
            "name": shop_data.get("name") or f"Shop {shop_id}",
            "owner": owner,
        },
    )
    return shop


def _upsert_branch(branch_data: dict[str, Any] | None, shop: Shop) -> Branch | None:
    if not branch_data:
        return None
    branch_id = branch_data.get("id")
    if not branch_id:
        return None
    branch, _ = Branch.objects.update_or_create(
        pk=branch_id,
        defaults={
            "shop": shop,
            "name": branch_data.get("name") or f"Branch {branch_id}",
            "is_active": branch_data.get("is_active", True),
        },
    )
    return branch


def _upsert_category(category_data: dict[str, Any] | None, shop: Shop, branch: Branch | None) -> Category | None:
    if not category_data:
        return None
    category_id = category_data.get("id")
    if not category_id:
        return None
    category, _ = Category.objects.update_or_create(
        pk=category_id,
        defaults={
            "shop": shop,
            "branch": branch,
            "title": category_data.get("title") or "",
            "description": category_data.get("description"),
            "sort_order": category_data.get("sort_order") or 0,
            "is_active": category_data.get("is_active", True),
        },
    )
    return category


def _upsert_product(
    product_data: dict[str, Any],
    shop: Shop,
    branch: Branch | None,
    category: Category | None,
) -> Product | None:
    product_id = product_data.get("id")
    if not product_id:
        return None
    product, _ = Product.objects.update_or_create(
        pk=product_id,
        defaults={
            "shop": shop,
            "branch": branch,
            "category": category,
            "title": product_data.get("title") or "",
            "second_id": product_data["second_id"],
            "price": product_data["price"],
            "score": product_data["score"],
            "is_active": product_data.get("is_active", True),
            "is_offerable": product_data.get("is_offerable", False),
            "remote_image_url": product_data.get("image_url") or None,
        },
    )
    return product


def ensure_local_shop(shop_id: int) -> Shop | None:
    """Mirror a shop row locally using management integration shop list."""
    from utils.management_shops import fetch_management_shops

    shops = fetch_management_shops()
    if shops is None:
        return Shop.objects.filter(pk=shop_id).first()

    shop_data = next((row for row in shops if row.get("id") == shop_id), None)
    if not shop_data:
        return None

    owner = _sync_owner()
    return _upsert_shop(shop_data, owner)


@transaction.atomic
def sync_customer_offers_for_user(user: User, shop_id: int | None = None) -> bool:
    """
    Fetch offers for ``user.phone_number`` and refresh local mirror + UserSpecialOffer rows.
    When ``shop_id`` is set, only offers for that shop are synced (others are removed).
    Returns True if sync ran (including empty offer list), False if fetch was skipped/failed.
    """
    phone_number = (user.phone_number or "").strip()
    if not phone_number:
        return False

    if shop_id is not None:
        ensure_local_shop(shop_id)

    offers_payload = fetch_customer_offers(phone_number, shop_id=shop_id)
    if offers_payload is None:
        return False

    owner = _sync_owner()
    seen_offer_ids: list[int] = []

    for offer in offers_payload:
        product_data = offer.get("product") or {}
        shop_data = product_data.get("shop") or {}
        shop = _upsert_shop(shop_data, owner)
        if shop is None:
            continue

        branch = _upsert_branch(product_data.get("branch"), shop)
        category = _upsert_category(product_data.get("category"), shop, branch)
        product = _upsert_product(product_data, shop, branch, category)
        if product is None:
            continue

        offer_id = offer.get("id")
        if not offer_id:
            continue

        user_offer, _ = UserSpecialOffer.objects.update_or_create(
            pk=offer_id,
            defaults={
                "user": user,
                "product": product,
                "offer_rate": int(offer.get("offer_rate") or 0),
            },
        )
        seen_offer_ids.append(user_offer.id)

    UserSpecialOffer.objects.filter(user=user).exclude(id__in=seen_offer_ids).delete()
    return True
