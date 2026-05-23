#!/usr/bin/env python3
"""
Import Customer Club Dataset files into the management server PostgreSQL database.

Reads (under Dataset/ by default):
  - Aras_articles.xlsx / .csv   → products (all branches get every product)
  - Aras_stores.csv             → branches (store → name, store_id → branch PK)
  - product_images/             → images (filename often shorter than product name)
  - final_prediction.csv        → end users + special offers (columns 0–9)

Two modes (see USE_API below):
  - Direct DB (default): uses Django + backend/.env (USE_POSTGRES=1) — same DB as management.
  - API: POST to /api/integration/dataset-import/ (management server must be running).

Style matches send_transactions_new.py (step logging, requests session, config block at bottom).

  pip install requests openpyxl python-dotenv
  cd Django_React_management/backend && python manage.py migrate

  python send_dataset_to_management.py
  python send_dataset_to_management.py --dry-run
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "Dataset"
BACKEND_DIR = PROJECT_ROOT / "Django_React_management" / "backend"

DEFAULT_IMPORT_ENDPOINT = "/api/integration/dataset-import/"


def _configure_stdio_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _build_url(base_url: str, endpoint_path: str) -> str:
    base = base_url.rstrip("/")
    endpoint = "/" + endpoint_path.lstrip("/")
    return f"{base}{endpoint}"


def _summarize_response_body(body, limit=400):
    if not isinstance(body, dict):
        return body
    raw = body.get("raw")
    if isinstance(raw, str) and len(raw) > limit:
        return {"raw": raw[:limit] + f"... [truncated, total {len(raw)} chars]"}
    return body


def send_dataset_import_via_api(
    base_url: str,
    api_key: str,
    *,
    dataset_root: Path,
    shop_id: int | None = None,
    branch_id: int | None = None,
    skip_products: bool = False,
    skip_offers: bool = False,
    clear_offers: bool = False,
    no_random_active: bool = False,
    seed: int | None = None,
    endpoint_path: str = DEFAULT_IMPORT_ENDPOINT,
    timeout: int = 3600,
) -> tuple[bool, int, dict]:
    """
    POST one import job to the management integration API.
    Returns: (ok, status_code, response_body)
    """
    url = _build_url(base_url, endpoint_path)
    headers = {
        "X-Management-API-Key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "dataset_root": str(dataset_root.resolve()),
        "skip_products": skip_products,
        "skip_offers": skip_offers,
        "images_only": images_only,
        "clear_offers": clear_offers,
        "no_random_active": no_random_active,
    }
    if shop_id is not None:
        payload["shop_id"] = shop_id
    if branch_id is not None:
        payload["branch_id"] = branch_id
    if seed is not None:
        payload["seed"] = seed

    print(f"Step 4: POST import job -> {url}")
    print(f"Step 4a: dataset_root={payload['dataset_root']}")
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text}
        return resp.ok, resp.status_code, body
    except requests.RequestException as exc:
        return False, 0, {"error": str(exc)}


def run_dataset_import_direct(
    *,
    dataset_root: Path,
    shop_id: int | None = None,
    branch_id: int | None = None,
    skip_products: bool = False,
    skip_offers: bool = False,
    clear_offers: bool = False,
    no_random_active: bool = False,
    seed: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Import using Django ORM and backend/.env database settings."""
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")

    import django

    django.setup()

    from django.conf import settings

    engine = settings.DATABASES["default"]["ENGINE"]
    print(f"Step 2: Django DB engine -> {engine}")
    if "sqlite" in engine:
        print(
            "Warning: SQLite detected. Set USE_POSTGRES=1 in Django_React_management/backend/.env",
            file=sys.stderr,
        )

    from module_api.dataset_import_service import run_dataset_import

    if dry_run:
        from module_api.dataset_import_service import load_articles, load_stores

        stores = load_stores(dataset_root / "Aras_stores.csv")
        articles_path = dataset_root / "Aras_articles.xlsx"
        if not articles_path.exists():
            articles_path = dataset_root / "Aras_articles.csv"
        articles = load_articles(articles_path)
        print(f"Step 3 (dry-run): {len(stores)} stores, {len(articles)} articles")
        print(f"  product rows would be ~{len(stores) * len(articles)}")
        pred = dataset_root / "final_prediction.csv"
        if pred.exists():
            with pred.open(encoding="utf-8-sig") as f:
                lines = sum(1 for _ in f) - 1
            print(f"  prediction rows: {lines}")
        return {"dry_run": True, "stores": len(stores), "articles": len(articles)}

    print("Step 3: Run import via Django ORM …")
    return run_dataset_import(
        dataset_root=dataset_root,
        shop_id=shop_id,
        branch_id=branch_id,
        skip_products=skip_products,
        skip_offers=skip_offers,
        clear_offers=clear_offers,
        random_active=not no_random_active,
        seed=seed,
        log=print,
    )


def run_import(
    *,
    use_api: bool,
    base_url: str,
    api_key: str,
    dataset_root: Path,
    shop_id: int | None,
    branch_id: int | None,
    skip_products: bool,
    skip_offers: bool,
    images_only: bool,
    clear_offers: bool,
    no_random_active: bool,
    seed: int | None,
    dry_run: bool,
    endpoint_path: str,
) -> int:
    dataset_root = Path(dataset_root).resolve()
    print(f"Step 1: Dataset folder -> {dataset_root}")
    if not dataset_root.is_dir():
        print(f"ERROR: Dataset folder not found: {dataset_root}", file=sys.stderr)
        return 1

    for name in ("Aras_stores.csv", "final_prediction.csv"):
        p = dataset_root / name
        if not p.exists():
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 1

    articles_xlsx = dataset_root / "Aras_articles.xlsx"
    articles_csv = dataset_root / "Aras_articles.csv"
    if not articles_xlsx.exists() and not articles_csv.exists():
        print("ERROR: need Aras_articles.xlsx or Aras_articles.csv", file=sys.stderr)
        return 1

    if dry_run and use_api:
        print("Step 3 (dry-run): API mode — no POST sent.")
        run_dataset_import_direct(
            dataset_root=dataset_root,
            shop_id=shop_id,
            branch_id=branch_id,
            skip_products=skip_products,
            skip_offers=skip_offers,
            dry_run=True,
        )
        return 0

    if use_api:
        if not api_key:
            print("ERROR: MANAGEMENT_API_KEY / API_KEY is required for API mode.", file=sys.stderr)
            return 1
        ok, status_code, body = send_dataset_import_via_api(
            base_url,
            api_key,
            dataset_root=dataset_root,
            shop_id=shop_id,
            branch_id=branch_id,
            skip_products=skip_products,
            skip_offers=skip_offers,
            clear_offers=clear_offers,
            no_random_active=no_random_active,
            seed=seed,
            endpoint_path=endpoint_path,
        )
        if ok:
            print("Step 5: Import finished OK.")
            print(json.dumps(body.get("result", body), ensure_ascii=False, indent=2))
            return 0
        print(f"Step 5: FAIL status={status_code} response={_summarize_response_body(body)}")
        return 1

    if dry_run:
        run_dataset_import_direct(
            dataset_root=dataset_root,
            shop_id=shop_id,
            branch_id=branch_id,
            dry_run=True,
        )
        print("Step 5: Dry-run done.")
        return 0

    result = run_dataset_import_direct(
        dataset_root=dataset_root,
        shop_id=shop_id,
        branch_id=branch_id,
        skip_products=skip_products,
        skip_offers=skip_offers,
        clear_offers=clear_offers,
        no_random_active=no_random_active,
        seed=seed,
    )
    print("Step 5: Import finished.")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    _configure_stdio_utf8()

    # Optional CLI flags: python send_dataset_to_management.py --dry-run
    _cli_dry_run = "--dry-run" in sys.argv
    _cli_skip_products = "--skip-offers" not in sys.argv and "--skip-products" in sys.argv
    _cli_skip_offers = "--skip-products" not in sys.argv and "--skip-offers" in sys.argv
    _cli_clear = "--clear-offers" in sys.argv
    _cli_images_only = "--images-only" in sys.argv

    # -------------------------------------------------------------------------
    # Configuration (edit these, like send_transactions_new.py)
    # -------------------------------------------------------------------------
    print("Step 0: Load script configuration.")

    # False = write directly to PostgreSQL via Django_React_management/backend/.env
    # True  = POST to running management server (dataset_root must exist on that machine)
    USE_API = False

    BASE_URL = "http://127.0.0.1:8000/"
    # Same value as MANAGEMENT_SERVICE_API_KEY in backend/.env (only used when USE_API=True)
    API_KEY = os.environ.get("MANAGEMENT_SERVICE_API_KEY", "change-me-integration-key")

    DATASET_ROOT = DEFAULT_DATASET_ROOT
    IMPORT_ENDPOINT = DEFAULT_IMPORT_ENDPOINT

    SHOP_ID = None  # default: only shop in database
    BRANCH_ID = None  # default: all rows in Aras_stores.csv
    SKIP_PRODUCTS = False
    SKIP_OFFERS = False
    IMAGES_ONLY = _cli_images_only
    CLEAR_OFFERS = False
    NO_RANDOM_ACTIVE = False
    SEED = None
    DRY_RUN = _cli_dry_run
    if _cli_skip_products:
        SKIP_PRODUCTS = True
    if _cli_skip_offers:
        SKIP_OFFERS = True
    if _cli_clear:
        CLEAR_OFFERS = True
    if _cli_images_only:
        SKIP_OFFERS = True

    # -------------------------------------------------------------------------
    exit_code = run_import(
        use_api=USE_API,
        base_url=BASE_URL,
        api_key=API_KEY,
        dataset_root=DATASET_ROOT,
        shop_id=SHOP_ID,
        branch_id=BRANCH_ID,
        skip_products=SKIP_PRODUCTS,
        skip_offers=SKIP_OFFERS,
        images_only=IMAGES_ONLY,
        clear_offers=CLEAR_OFFERS,
        no_random_active=NO_RANDOM_ACTIVE,
        seed=SEED,
        dry_run=DRY_RUN,
        endpoint_path=IMPORT_ENDPOINT,
    )
    raise SystemExit(exit_code)
