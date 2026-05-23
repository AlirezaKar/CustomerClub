"""
Dummy data initializer for CustomerClub backend.

This file is intentionally standalone (single-file seed script) and does not
require changing any other project files.

Run from backend directory:
    python manage.py shell -c "exec(open('module_product/managment/command/init_db.py', encoding='utf-8').read())"
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction

from module_product.models import Category, Product, UserSpecialOffer
from module_shop.models import Score, Shop


User = get_user_model()


@dataclass(frozen=True)
class CatalogItem:
    title: str
    price: int
    score: int


CATALOG: dict[str, list[CatalogItem]] = {
    "Cookies": [
        CatalogItem("Oat Cookie", 35000, 35),
        CatalogItem("Chocolate Cookie", 42000, 42),
        CatalogItem("Apricot Cookie", 39000, 39),
        CatalogItem("Berry Cookie", 40000, 40),
    ],
    "Sandwiches": [
        CatalogItem("Turkey Club", 130000, 130),
        CatalogItem("Chicken Pesto Club", 125000, 125),
        CatalogItem("Beef Club", 150000, 150),
        CatalogItem("Veggie Club", 110000, 110),
    ],
    "Noodles": [
        CatalogItem("Chicken Noodles", 140000, 140),
        CatalogItem("Beef Noodles", 155000, 155),
        CatalogItem("Vegetable Noodles", 120000, 120),
    ],
    "Drinks": [
        CatalogItem("Lemonade", 45000, 45),
        CatalogItem("Cola", 30000, 30),
        CatalogItem("Zero Cola", 32000, 32),
    ],
}


def _get_or_create_owner() -> User:
    owner = User.objects.filter(is_superuser=True).first()
    if owner:
        return owner

    owner = User.objects.filter(phone_number="09120000000").first()
    if owner:
        return owner

    owner = User.objects.create(
        username="09120000000",
        phone_number="09120000000",
        age=30,
        gender="male",
        card_uid="OWNER-CARD-0001",
        is_staff=True,
        is_superuser=True,
    )
    owner.set_unusable_password()
    owner.save()
    return owner


def _create_customers(total: int = 16) -> list[User]:
    customers: list[User] = []
    for idx in range(1, total + 1):
        phone = f"0912000{idx:04d}"
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={
                "username": phone,
                "age": random.randint(18, 55),
                "gender": random.choice(["male", "female"]),
                "score": random.randint(200, 3000),
                "card_uid": f"CARD-{idx:04d}",
            },
        )
        if created:
            user.set_unusable_password()
            user.save()
        customers.append(user)
    return customers


def _seed_shop_and_products(owner: User) -> tuple[Shop, list[Product]]:
    shop, _ = Shop.objects.get_or_create(name="CustomerClub Demo Shop", owner=owner)

    Score.objects.get_or_create(
        shop=shop,
        defaults={
            "price_for_score": 1000000,
            "score_for_purchase": 1,
        },
    )

    products: list[Product] = []
    second_id_counter = 100001

    for order, (category_title, items) in enumerate(CATALOG.items(), start=1):
        category, _ = Category.objects.get_or_create(
            shop=shop,
            title=category_title,
            defaults={"description": f"Dummy category: {category_title}", "sort_order": order, "is_active": True},
        )

        for item in items:
            product, _ = Product.objects.get_or_create(
                second_id=second_id_counter,
                defaults={
                    "shop": shop,
                    "category": category,
                    "title": item.title,
                    "price": item.price,
                    "score": item.score,
                    "is_active": True,
                },
            )
            # Keep shop/category synced if a matching second_id existed earlier.
            updates = []
            if product.shop_id != shop.id:
                product.shop = shop
                updates.append("shop")
            if product.category_id != category.id:
                product.category = category
                updates.append("category")
            if updates:
                product.save(update_fields=updates)

            products.append(product)
            second_id_counter += 1

    return shop, products


def _seed_user_offers(customers: list[User], products: list[Product]) -> None:
    for user in customers:
        offerable = [p for p in products if getattr(p, "is_offerable", False)]
        chosen = random.sample(offerable, k=min(4, len(offerable)))
        for product in chosen:
            UserSpecialOffer.objects.get_or_create(
                user=user,
                product=product,
                defaults={"offer_rate": random.randint(10, 40)},
            )


@transaction.atomic
def run() -> None:
    random.seed(20260222)

    owner = _get_or_create_owner()
    customers = _create_customers(total=18)
    shop, products = _seed_shop_and_products(owner)
    _seed_user_offers(customers, products)

    print("Dummy data initialized.")
    print(f"Shop ID: {shop.id} | Name: {shop.name}")
    print(f"Customers: {len(customers)}")
    print(f"Categories: {Category.objects.filter(shop=shop).count()}")
    print(f"Products: {Product.objects.filter(shop=shop).count()}")
    print(f"User offers: {UserSpecialOffer.objects.count()}")


run()
