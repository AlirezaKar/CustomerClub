# Dataset import & database backup scripts

Standalone utilities for the **management** server (`Django_React_management/backend`). They load `.env` from that backend (including `USE_POSTGRES=1` / PostgreSQL settings).

## Prerequisites

1. PostgreSQL database created and migrated:

   ```bash
   cd Django_React_management/backend
   cp .env.example .env
   # Set USE_POSTGRES=1, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
   pip install -r requirements.txt
   python manage.py migrate
   ```

2. At least **one Shop** in the DB (branches are created/updated from `Aras_stores.csv`).

3. Dataset layout (defaults):

   ```
   Dataset/
     Aras_articles.xlsx      # or Aras_articles.csv
     Aras_stores.csv         # store → branch name, store_id → branch PK
     final_prediction.csv
     product_images/         # file name = product name, short name, or articles_id
   ```

## Import data

**Recommended** (same style as `send_transactions_new.py`, project root):

```bash
# Direct PostgreSQL via backend/.env (USE_POSTGRES=1)
python send_dataset_to_management.py --dry-run
python send_dataset_to_management.py
```

Or the CLI wrapper:

```bash
python scripts/import_dataset_to_db.py --dry-run
python scripts/import_dataset_to_db.py
```

API mode (management server running; `dataset_root` must exist on the server host):

Edit `USE_API = True` and `BASE_URL` / `API_KEY` in `send_dataset_to_management.py`, then run it.

### Field mapping (articles)

| Database        | File column   |
|-----------------|---------------|
| `second_id`     | `articles_id` / `article_id` |
| `title`         | `name`        |
| `category.title`| `G1`          |
| `score`         | `score`       |
| `price`         | `price`       |
| `image`         | `Dataset/product_images/<name>.<ext>` (exact, substring, or `articles_id`) |
| `category`      | **one row per shop** per **G1** value (branch empty); all branches share it |
| `is_active`     | random `True`/`False` (use `--no-random-active` for all active) |
| `is_offerable`  | `False` on import; set `True` for products listed in predictions |
| `shop` | only shop in DB (override with `--shop-id`) |
| `branch` | **every** row in `Aras_stores.csv` gets a full copy of the catalog (`store` → `Branch.name`, `store_id` → `Branch.id`) |

### Offers (`final_prediction.csv`)

| Column          | Usage |
|-----------------|-------|
| `customers_id`  | End-user `phone_number` (normalized to 11 digits, e.g. `900…` → `0900…`) |
| `0` … `9`       | 10 offered product **names** per user (`offer_rate` 10 → 1) |

Creates missing `EndUser` rows. Products referenced in the CSV are marked `is_offerable=True` on **all branches** that carry that title.

### Branches (`Aras_stores.csv`)

| CSV column | Database |
|------------|----------|
| `store` | `Branch.name` |
| `store_id` | `Branch.id` (created or updated under the target shop) |

```bash
python scripts/import_dataset_to_db.py --branch-id 12   # only صادقیه (store_id=12)
```

Options:

```bash
python scripts/import_dataset_to_db.py --skip-offers
python scripts/import_dataset_to_db.py --skip-products
python scripts/import_dataset_to_db.py --clear-offers
python scripts/import_dataset_to_db.py --articles Dataset/Aras_articles.csv
python scripts/import_dataset_to_db.py --seed 42
```

## Backup database

```bash
python scripts/export_postgres_database.py
```

Writes under `backups/`:

- `customerclub_management_YYYYMMDD_HHMMSS.dump` (pg_dump custom format)
- `customerclub_management_YYYYMMDD_HHMMSS.sql` (plain SQL)

If `pg_dump` is not installed, falls back to Django `dumpdata` JSON.

```bash
python scripts/export_postgres_database.py --format json
python scripts/export_postgres_database.py --output-dir D:/backups
python scripts/export_postgres_database.py --sql-only
```

### Restore (PostgreSQL)

```bash
pg_restore -h localhost -U postgres -d customerclub_management --clean --if-exists backups/your_file.dump
# or
psql -h localhost -U postgres -d customerclub_management -f backups/your_file.sql
```

## API alternative

The reference script `send_transactions_new.py` posts JSON to HTTP endpoints with a bearer token. This project’s management API exposes product CRUD at `/api/products/` (JWT) and integration endpoints under `/api/integration/` (`MANAGEMENT_SERVICE_API_KEY`). Bulk seeding with images is simpler via the Django scripts above; use the API for incremental sync from external systems.
