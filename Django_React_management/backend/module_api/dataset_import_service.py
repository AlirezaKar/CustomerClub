"""
Load Dataset files into the management PostgreSQL database.

Used by the integration API and by standalone import scripts.
"""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from difflib import get_close_matches
from pathlib import Path

OFFER_COLUMN_KEYS = tuple(str(i) for i in range(10))

# Product image folders under Dataset/ (first match with files wins).
IMAGE_FOLDER_NAMES = ("product_images", "products_images", "کالا", "kala")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".jfif"}
# Minimum length for substring filename ↔ product title matching.
IMAGE_SUBSTRING_MIN_LEN = 3
# Fuzzy match when spaces/typos differ (e.g. رپ کوکو سبزی ↔ file رپ کوکوسیبزمینی).
IMAGE_FUZZY_CUTOFF = 0.82


def normalize_phone(raw: str) -> str | None:
    if raw is None:
        return None
    digits = "".join(c for c in str(raw).strip() if c.isdigit())
    if not digits:
        return None
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    if len(digits) != 11 or not digits.isdigit():
        return None
    return digits


def normalize_title(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def compact_match_key(text: str) -> str:
    """Title/filename without spaces — helps match minor spacing differences."""
    return normalize_match_key(text).replace(" ", "")


def normalize_match_key(text: str) -> str:
    """
    Normalize product / filename text for image lookup (Persian variants, ZWNJ, etc.).
    """
    s = normalize_title(text)
    for old, new in (
        ("\u064a", "\u06cc"),  # Arabic yeh → Persian ye
        ("\u0643", "\u06a9"),  # Arabic kaf → Persian kaf
        ("\u0629", "\u0647"),  # teh marbuta → heh
        ("\u200c", " "),  # ZWNJ → space
        ("\u200d", ""),
        ("\u0640", ""),  # tatweel
    ):
        s = s.replace(old, new)
    return " ".join(s.split())


def normalize_category_key(text: str) -> str:
    """Canonical key so e.g. drink / Drink / DRINK share one shop-wide category."""
    label = normalize_title(text) or "عمومی"
    if label.isascii():
        return label.lower()
    return label


def load_articles(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Articles file not found: {path}")

    suffix = path.suffix.lower()
    rows: list[dict] = []

    if suffix in (".xlsx", ".xlsm", ".xltx"):
        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        headers = [str(h).strip() if h is not None else "" for h in header_row]
        for values in ws.iter_rows(min_row=2, values_only=True):
            if not values or all(v is None or str(v).strip() == "" for v in values):
                continue
            row = {headers[i]: values[i] for i in range(len(headers)) if i < len(values)}
            parsed = _parse_article_row(row)
            if parsed:
                rows.append(parsed)
        wb.close()
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                parsed = _parse_article_row(row)
                if parsed:
                    rows.append(parsed)
    return rows


def _parse_article_row(row: dict) -> dict | None:
    def pick(*keys):
        for key in keys:
            if key in row and row[key] not in (None, ""):
                return row[key]
        lowered = {str(k).lower(): v for k, v in row.items()}
        for key in keys:
            lk = key.lower()
            if lk in lowered and lowered[lk] not in (None, ""):
                return lowered[lk]
        return None

    raw_id = pick("articles_id", "article_id", "Article_ID", "second_id")
    title = pick("name", "title", "Name", "Title")
    category = pick("G1", "Category", "category")
    price = pick("price", "Price")
    score = pick("score", "Score")
    if raw_id is None or title is None:
        return None

    try:
        second_id = int(float(str(raw_id).strip()))
    except (TypeError, ValueError):
        return None

    title = normalize_title(str(title))
    if not title:
        return None

    try:
        price_val = int(float(str(price or 0).strip()))
    except (TypeError, ValueError):
        price_val = 0
    try:
        score_val = int(float(str(score or 0).strip()))
    except (TypeError, ValueError):
        score_val = 0

    raw_category = normalize_title(str(category or "عمومی")) or "عمومی"
    return {
        "second_id": second_id,
        "title": title,
        "category": raw_category,
        "category_key": normalize_category_key(raw_category),
        "price": max(price_val, 0),
        "score": max(score_val, 0),
    }


def load_stores(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Stores file not found: {path}")

    stores: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            def pick(*keys):
                for key in keys:
                    if key in row and row[key] not in (None, ""):
                        return row[key]
                lowered = {str(k).lower(): v for k, v in row.items()}
                for key in keys:
                    if key.lower() in lowered and lowered[key.lower()] not in (None, ""):
                        return lowered[key.lower()]
                return None

            raw_id = pick("store_id", "Store_ID", "branch_id", "id")
            name = pick("store", "Store", "branch", "name")
            if raw_id is None:
                continue
            try:
                store_id = int(float(str(raw_id).strip()))
            except (TypeError, ValueError):
                continue
            store_name = normalize_title(str(name or ""))
            if not store_name:
                continue
            stores.append({"store_id": store_id, "name": store_name})

    if not stores:
        raise ValueError(f"No stores loaded from {path.name}")
    return stores


def resolve_shop(shop_id: int | None):
    from module_shop.models import Shop

    if shop_id is not None:
        shop = Shop.objects.filter(pk=shop_id).first()
        if not shop:
            raise ValueError(f"Shop id={shop_id} not found.")
        return shop

    shops = list(Shop.objects.all().order_by("id"))
    if not shops:
        raise ValueError("No shop in database.")
    return shops[0]


def resolve_branches_from_stores(shop, stores: list[dict], *, only_branch_id: int | None = None):
    from django.db import connection

    from module_shop.models import Branch

    if only_branch_id is not None:
        stores = [s for s in stores if s["store_id"] == only_branch_id]
        if not stores:
            raise ValueError(f"store_id={only_branch_id} not in stores file.")

    branches = []
    created = 0
    updated = 0

    for store in stores:
        store_id = store["store_id"]
        store_name = store["name"]

        existing = Branch.objects.filter(pk=store_id).first()
        if existing:
            if existing.shop_id != shop.id:
                raise ValueError(
                    f"Branch id={store_id} belongs to shop {existing.shop_id}, not {shop.id}."
                )
            changed = False
            if existing.name != store_name:
                existing.name = store_name
                changed = True
            if not existing.is_active:
                existing.is_active = True
                changed = True
            if changed:
                existing.save()
                updated += 1
            branches.append(existing)
            continue

        by_name = Branch.objects.filter(shop=shop, name=store_name).first()
        if by_name:
            branches.append(by_name)
            continue

        branch = Branch.objects.create(
            id=store_id,
            shop=shop,
            name=store_name,
            is_active=True,
        )
        created += 1
        branches.append(branch)

    if created and connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence('module_shop_branch', 'id'),
                    COALESCE((SELECT MAX(id) FROM module_shop_branch), 1)
                )
                """
            )

    return branches, {"created": created, "updated": updated, "total": len(branches)}


def resolve_images_dir(dataset_root: Path, override: Path | None = None) -> Path:
    """Prefer Dataset/product_images (names often shorter than full product title)."""
    if override is not None:
        p = Path(override)
        if p.is_dir():
            return p

    root = Path(dataset_root)
    best: Path | None = None
    best_count = 0
    for name in IMAGE_FOLDER_NAMES:
        candidate = root / name
        if not candidate.is_dir():
            continue
        count = sum(
            1
            for f in candidate.rglob("*")
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        )
        if count > best_count:
            best = candidate
            best_count = count

    if best is not None:
        return best
    kala = root / "کالا"
    if kala.is_dir():
        return kala
    return root / "product_images"


def _image_index_keys(stem: str) -> set[str]:
    keys: set[str] = set()
    raw = (stem or "").strip()
    if not raw:
        return keys
    keys.add(raw)
    keys.add(normalize_title(raw))
    keys.add(normalize_match_key(raw))
    normalized = normalize_match_key(raw)
    if normalized:
        if normalized.isascii():
            keys.add(normalized.lower())
        for word in normalized.split():
            if len(word) >= IMAGE_SUBSTRING_MIN_LEN:
                keys.add(word)
    digits = "".join(c for c in raw if c.isdigit())
    if digits:
        keys.add(digits)
        try:
            keys.add(str(int(digits)))
        except ValueError:
            pass
    return {k for k in keys if k}


def build_image_index(images_dir: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    """Return (token index, compact index) for product_images lookup."""
    if not images_dir.is_dir():
        return {}, {}
    index: dict[str, Path] = {}
    compact_index: dict[str, Path] = {}
    for path in images_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        for key in _image_index_keys(path.stem):
            if key not in index:
                index[key] = path
        compact = compact_match_key(path.stem)
        if compact and compact not in compact_index:
            compact_index[compact] = path
    return index, compact_index


def find_product_image(
    index: dict[str, Path],
    row: dict,
    compact_index: dict[str, Path] | None = None,
) -> Path | None:
    """
    Match image in product_images to a product row.

    Tries, in order:
      1. Exact normalized title or articles_id (second_id)
      2. Longest substring overlap (e.g. file ``اسپرایت`` → ``نوشابه قوطی اسپرایت``)
      3. Any word in the product title that matches a filename key
    """
    title_key = normalize_match_key(row["title"])
    article_id = str(row["second_id"])

    if title_key in index:
        return index[title_key]
    if article_id in index:
        return index[article_id]

    best_path: Path | None = None
    best_key_len = 0
    for key, path in index.items():
        if len(key) < IMAGE_SUBSTRING_MIN_LEN:
            continue
        if key in title_key or title_key in key:
            if len(key) > best_key_len:
                best_key_len = len(key)
                best_path = path
    if best_path is not None:
        return best_path

    for word in title_key.split():
        if len(word) >= IMAGE_SUBSTRING_MIN_LEN and word in index:
            return index[word]

    compact_index = compact_index or {}
    title_compact = compact_match_key(row["title"])
    if title_compact in compact_index:
        return compact_index[title_compact]

    if title_compact and compact_index:
        fuzzy_hits = get_close_matches(
            title_compact,
            compact_index.keys(),
            n=1,
            cutoff=IMAGE_FUZZY_CUTOFF,
        )
        if fuzzy_hits:
            return compact_index[fuzzy_hits[0]]

    return None


def preload_shop_category_cache(shop) -> dict[str, "Category"]:
    """Shop-wide categories only (branch is null) — one row per G1 key for the whole shop."""
    from module_product.models import Category

    cache: dict[str, Category] = {}
    for cat in Category.objects.filter(shop=shop, branch__isnull=True).only("id", "title"):
        key = normalize_category_key(cat.title)
        if key not in cache:
            cache[key] = cat
    return cache


def get_or_create_shop_category(
    shop,
    row: dict,
    cache: dict[str, "Category"],
) -> tuple["Category", bool]:
    """One Category per shop per G1 value (branch=null). All branches' products use it."""
    from module_product.models import Category

    key = row["category_key"]
    if key in cache:
        return cache[key], False

    display_title = row["category"]
    category = Category.objects.create(
        shop=shop,
        branch=None,
        title=display_title,
        is_active=True,
        sort_order=len(cache),
    )
    cache[key] = category
    return category, True


def consolidate_shop_categories(shop, log=None) -> dict:
    """
    Merge branch-scoped duplicate categories into one shop-wide category per G1 key.
    Re-import runs this automatically so old per-branch rows (e.g. many dessert) are fixed.
    """
    from module_product.models import Category, Product

    log = log or (lambda msg: None)
    canonical = preload_shop_category_cache(shop)
    created = 0

    for cat in Category.objects.filter(shop=shop, branch__isnull=False).order_by("id"):
        key = normalize_category_key(cat.title)
        if key not in canonical:
            canonical[key] = Category.objects.create(
                shop=shop,
                branch=None,
                title=cat.title,
                is_active=True,
                sort_order=len(canonical),
            )
            created += 1

    products_reassigned = 0
    categories_deleted = 0

    for cat in Category.objects.filter(shop=shop).exclude(
        id__in=[c.id for c in canonical.values()]
    ):
        key = normalize_category_key(cat.title)
        target = canonical.get(key)
        if not target:
            continue
        count = Product.objects.filter(category_id=cat.id).update(category_id=target.id)
        products_reassigned += count
        if not Product.objects.filter(category_id=cat.id).exists():
            cat.delete()
            categories_deleted += 1

    log(
        f"Categories consolidated: {len(canonical)} shop-wide, "
        f"{created} created, {products_reassigned} products relinked, "
        f"{categories_deleted} duplicate category rows removed"
    )
    return {
        "shop_wide_categories": len(canonical),
        "categories_created": created,
        "products_reassigned": products_reassigned,
        "categories_deleted": categories_deleted,
    }


def attach_product_image(product, img_path: Path) -> None:
    from django.core.files import File

    from module_product.image_storage import finalize_product_image

    with img_path.open("rb") as img_file:
        product.image.save(img_path.name, File(img_file), save=False)
    if finalize_product_image(product):
        product.save(update_fields=["image"])
    else:
        product.save(update_fields=["image"])


def import_products(
    *,
    articles: list[dict],
    images_dir: Path,
    shop,
    branches: list,
    random_active: bool = True,
    log=None,
) -> tuple[dict, dict]:
    from django.db import transaction

    from module_product.models import Product

    log = log or (lambda msg: None)
    image_index, compact_image_index = build_image_index(images_dir)
    title_to_product: dict = {}

    created_cats = 0
    created_products = 0
    updated_products = 0
    images_attached = 0
    missing_images = 0
    missing_image_titles: list[str] = []

    log(f"Images: {len(image_index)} lookup keys from {images_dir}")

    shop_categories = preload_shop_category_cache(shop)
    consolidate_stats = consolidate_shop_categories(shop, log=log)

    @transaction.atomic
    def _run():
        nonlocal created_cats, created_products, updated_products, images_attached, missing_images
        for branch in branches:
            branch_id = branch.id

            for row in articles:
                category, cat_created = get_or_create_shop_category(
                    shop, row, shop_categories
                )
                if cat_created:
                    created_cats += 1

                is_active = random.choice((True, False)) if random_active else True
                product, was_created = Product.objects.update_or_create(
                    branch=branch,
                    second_id=row["second_id"],
                    defaults={
                        "shop": shop,
                        "branch": branch,
                        "category": category,
                        "title": row["title"],
                        "price": row["price"],
                        "score": row["score"],
                        "is_active": is_active,
                        "is_offerable": False,
                    },
                )
                if row["title"] not in title_to_product:
                    title_to_product[row["title"]] = product
                if was_created:
                    created_products += 1
                else:
                    updated_products += 1

                img_path = find_product_image(image_index, row, compact_image_index)
                if img_path:
                    attach_product_image(product, img_path)
                    images_attached += 1
                else:
                    missing_images += 1
                    if len(missing_image_titles) < 15:
                        missing_image_titles.append(row["title"])

            log(f"  branch id={branch_id} ({branch.name!r}): done")

    _run()

    unique_category_keys = {row["category_key"] for row in articles}
    stats = {
        "articles": len(articles),
        "branches": len(branches),
        "product_rows": len(articles) * len(branches),
        "unique_categories_in_file": len(unique_category_keys),
        "shop_wide_categories": len(shop_categories),
        "category_consolidation": consolidate_stats,
        "categories_created": created_cats,
        "products_created": created_products,
        "products_updated": updated_products,
        "images_dir": str(images_dir),
        "image_lookup_keys": len(image_index),
        "images_attached": images_attached,
        "images_missing": missing_images,
        "missing_image_samples": missing_image_titles,
    }
    return stats, title_to_product


def backfill_product_images(
    *,
    articles: list[dict],
    images_dir: Path,
    shop,
    branches: list,
    log=None,
) -> dict:
    """Attach images from product_images to existing products (no new products/categories)."""
    from module_product.models import Product

    log = log or (lambda msg: None)
    image_index, compact_image_index = build_image_index(images_dir)
    log(f"Image backfill: {len(image_index)} lookup keys from {images_dir}")

    images_attached = 0
    missing_images = 0
    products_not_found = 0
    missing_image_titles: list[str] = []

    for branch in branches:
        for row in articles:
            product = Product.objects.filter(
                shop=shop,
                branch=branch,
                second_id=row["second_id"],
            ).first()
            if not product:
                products_not_found += 1
                continue

            img_path = find_product_image(image_index, row, compact_image_index)
            if img_path:
                attach_product_image(product, img_path)
                images_attached += 1
            else:
                missing_images += 1
                if len(missing_image_titles) < 20:
                    missing_image_titles.append(row["title"])

        log(f"  branch id={branch.id} ({branch.name!r}): images updated")

    return {
        "articles": len(articles),
        "branches": len(branches),
        "product_rows": len(articles) * len(branches),
        "images_dir": str(images_dir),
        "image_lookup_keys": len(image_index),
        "images_attached": images_attached,
        "images_missing": missing_images,
        "products_not_found": products_not_found,
        "missing_image_samples": missing_image_titles,
    }


def import_offers(
    *,
    predictions_path: Path,
    shop,
    title_to_product: dict | None = None,
    clear_existing: bool = False,
    log=None,
) -> dict:
    from django.db import transaction

    from module_account.models import EndUser
    from module_product.models import Product, UserSpecialOffer

    log = log or (lambda msg: None)
    if not predictions_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {predictions_path}")

    product_by_title: dict[str, Product] = {}
    for p in (
        Product.objects.filter(shop=shop)
        .only("id", "title", "branch_id")
        .order_by("branch_id", "id")
    ):
        key = normalize_title(p.title)
        if key not in product_by_title:
            product_by_title[key] = p
    if title_to_product:
        for title, prod in title_to_product.items():
            if prod is not None:
                product_by_title[normalize_title(title)] = prod

    stats: dict = defaultdict(int)
    pending_offers: list[tuple[str, str, int]] = []

    with predictions_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        phone_col = None
        for name in reader.fieldnames or []:
            if name and name.lower() in ("customers_id", "customer_id", "phone_number", "phone"):
                phone_col = name
                break
        if not phone_col:
            raise ValueError(f"No customer id column in {predictions_path.name}")

        for row in reader:
            stats["rows"] += 1
            phone = normalize_phone(row.get(phone_col, ""))
            if not phone:
                stats["bad_phone"] += 1
                continue
            for col_idx, col_key in enumerate(OFFER_COLUMN_KEYS):
                title = normalize_title(row.get(col_key, ""))
                if not title:
                    continue
                pending_offers.append((phone, title, 10 - col_idx))
                stats["offer_cells"] += 1

    unique_phones = {p for p, _, _ in pending_offers}
    log(f"Predictions: {stats['rows']} rows, {len(unique_phones)} phones, {stats['offer_cells']} cells")

    @transaction.atomic
    def _run():
        if clear_existing:
            deleted, _ = UserSpecialOffer.objects.filter(
                product__shop=shop,
                user__role="end_user",
            ).delete()
            stats["offers_cleared"] = deleted

        offer_titles = {title for _p, title, _r in pending_offers if title in product_by_title}
        if offer_titles:
            marked = 0
            for title in offer_titles:
                marked += Product.objects.filter(shop=shop, title=title).update(is_offerable=True)
            stats["products_marked_offerable"] = marked

        existing_users = {
            phone: uid
            for uid, phone in EndUser.objects.filter(phone_number__in=unique_phones).values_list(
                "id", "phone_number"
            )
        }

        for phone in unique_phones:
            if phone in existing_users:
                continue
            user = EndUser.objects.create_end_user(username=phone, phone_number=phone)
            user.set_unusable_password()
            user.save(update_fields=[])
            existing_users[phone] = user.id
            stats["users_created"] += 1

        offer_objects: list[UserSpecialOffer] = []
        seen: set[tuple[int, int]] = set()

        for phone, title, offer_rate in pending_offers:
            user_id = existing_users.get(phone)
            if user_id is None or title not in product_by_title:
                stats["skipped"] += 1
                continue
            product = product_by_title[title]
            pair = (user_id, product.id)
            if pair in seen:
                continue
            seen.add(pair)
            offer_objects.append(
                UserSpecialOffer(user_id=user_id, product_id=product.id, offer_rate=offer_rate)
            )

        if offer_objects:
            UserSpecialOffer.objects.bulk_create(
                offer_objects,
                update_conflicts=True,
                unique_fields=["user", "product"],
                update_fields=["offer_rate"],
            )
            stats["offers_upserted"] = len(offer_objects)

    _run()
    return dict(stats)


def run_dataset_import(
    *,
    dataset_root: Path,
    shop_id: int | None = None,
    branch_id: int | None = None,
    images_dir: Path | None = None,
    skip_products: bool = False,
    skip_offers: bool = False,
    images_only: bool = False,
    clear_offers: bool = False,
    random_active: bool = True,
    seed: int | None = None,
    log=None,
) -> dict:
    """Full import from a Dataset folder into management PostgreSQL."""
    log = log or print
    if seed is not None:
        random.seed(seed)

    dataset_root = Path(dataset_root)
    articles_path = dataset_root / "Aras_articles.xlsx"
    if not articles_path.exists():
        articles_path = dataset_root / "Aras_articles.csv"
    stores_path = dataset_root / "Aras_stores.csv"
    predictions_path = dataset_root / "final_prediction.csv"
    resolved_images = resolve_images_dir(dataset_root, images_dir)

    result: dict = {
        "dataset_root": str(dataset_root),
        "images_dir": str(resolved_images),
    }

    stores = load_stores(stores_path)
    shop = resolve_shop(shop_id)
    branches, branch_stats = resolve_branches_from_stores(
        shop, stores, only_branch_id=branch_id
    )
    result["shop"] = {"id": shop.id, "name": shop.name}
    result["branches"] = branch_stats
    log(f"Shop id={shop.id} ({shop.name!r}), branches={len(branches)}")

    title_map: dict = {}
    articles = load_articles(articles_path)
    log(f"Loaded {len(articles)} articles from {articles_path.name}")

    if images_only:
        result["images"] = backfill_product_images(
            articles=articles,
            images_dir=resolved_images,
            shop=shop,
            branches=branches,
            log=log,
        )
        return result

    if not skip_products:
        product_stats, title_map = import_products(
            articles=articles,
            images_dir=resolved_images,
            shop=shop,
            branches=branches,
            random_active=random_active,
            log=log,
        )
        result["products"] = product_stats

    if not skip_offers:
        offer_stats = import_offers(
            predictions_path=predictions_path,
            shop=shop,
            title_to_product=title_map,
            clear_existing=clear_offers,
            log=log,
        )
        result["offers"] = offer_stats

    return result
