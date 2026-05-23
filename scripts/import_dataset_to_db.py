#!/usr/bin/env python3
"""
Thin CLI wrapper around module_api.dataset_import_service (direct PostgreSQL).

Prefer the standalone script at project root (same style as send_transactions_new.py):

  python send_dataset_to_management.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "Django_React_management" / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

DEFAULT_DATASET_ROOT = PROJECT_ROOT / "Dataset"


def _configure_stdio_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Import Dataset into management PostgreSQL.")
    p.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    p.add_argument("--shop-id", type=int, default=None)
    p.add_argument("--branch-id", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-products", action="store_true")
    p.add_argument("--skip-offers", action="store_true")
    p.add_argument("--clear-offers", action="store_true")
    p.add_argument("--no-random-active", action="store_true")
    p.add_argument("--seed", type=int, default=None)
    return p.parse_args(argv)


def main(argv=None) -> int:
    _configure_stdio_utf8()
    args = parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")

    import django

    django.setup()

    if args.dry_run:
        from module_api.dataset_import_service import load_articles, load_stores

        stores = load_stores(args.dataset_root / "Aras_stores.csv")
        ap = args.dataset_root / "Aras_articles.xlsx"
        if not ap.exists():
            ap = args.dataset_root / "Aras_articles.csv"
        articles = load_articles(ap)
        print(f"Dry-run: {len(stores)} stores, {len(articles)} articles")
        return 0

    from module_api.dataset_import_service import run_dataset_import

    run_dataset_import(
        dataset_root=args.dataset_root,
        shop_id=args.shop_id,
        branch_id=args.branch_id,
        skip_products=args.skip_products,
        skip_offers=args.skip_offers,
        clear_offers=args.clear_offers,
        random_active=not args.no_random_active,
        seed=args.seed,
        log=print,
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
