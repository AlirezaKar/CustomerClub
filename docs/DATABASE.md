# Database setup (SQLite dev · PostgreSQL production)

Both Django backends share the same pattern:

| Backend | Path | Default DB name (Postgres) |
|---------|------|----------------------------|
| Management | `Django_React_management/backend` | `customerclub_management` |
| Kiosk (main) | `Django_React/backend` | `customerclub_kiosk` |

## Startup performance (kiosk)

If the kiosk API (`Django_React/backend`) starts slowly while management is fast:

- Use **SQLite** locally (`DEBUG=True` and do not set `USE_POSTGRES=1` unless Postgres is running).
- Keep **`ENABLE_OPENAPI=false`** in kiosk `.env` unless you need Swagger.
- Use `python manage.py runserver 8001 --skip-checks` (added automatically by `manage.py` in dev).

See [DOCUMENTATION.md](DOCUMENTATION.md#performance-and-startup).

## Stateless kiosk (recommended)

With `STATELESS_KIOSK=true` (default in `Django_React/backend/.env.example`), the public shop API does **not** mirror users, products, or offers into the kiosk database. All business reads and writes go through the management server integration API (`MANAGEMENT_API_BASE_URL` + `MANAGEMENT_SERVICE_API_KEY`).

The kiosk database is then only required for Django internals (migrations, optional admin); you can use an empty SQLite file or omit business seeding. SMS login codes and NFC bridge tokens live in cache only.

Set `STATELESS_KIOSK=false` only if you need the legacy local mirror behaviour.

## Local development (SQLite)

```bash
# Management
cd Django_React_management/backend
cp .env.example .env
# DEBUG=True → SQLite at db.sqlite3 (no Postgres required)
python manage.py migrate

# Kiosk
cd Django_React/backend
cp .env.example .env
python manage.py migrate
```

## Production (PostgreSQL)

1. Install PostgreSQL and create two databases (or one if you only run management):

```sql
CREATE DATABASE customerclub_management;
CREATE DATABASE customerclub_kiosk;
```

2. In each backend `.env`:

```env
DEBUG=False
DB_NAME=customerclub_management   # or customerclub_kiosk
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Or keep `DEBUG=True` locally but force Postgres: `USE_POSTGRES=1`.

3. Install dependencies and migrate:

```bash
pip install -r requirements.txt
python manage.py migrate
```

## Migrations

Migration files under each app’s `migrations/` folder are the **source of truth** for schema. Running `python manage.py migrate` on an empty database applies the full chain and recreates the current working state.

```bash
python manage.py showmigrations   # see what is applied
python manage.py migrate          # apply pending
```

To rebuild from scratch (destructive):

```bash
# Drop/recreate the PostgreSQL database (or delete db.sqlite3), then:
python manage.py migrate
```

Optional later: run `python manage.py squashmigrations <app> <first> <last> --squashed-name squashed --no-input` per app, then manually port any `RunPython` functions Django flags (see Django docs). Migrations with custom Python (score ledger, image paths, role hierarchy) need that extra step before deleting old files.

## Migrating data from SQLite to PostgreSQL

Use the standalone script (when added) or export/import:

```bash
# Export from SQLite (management example)
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 -o data_backup.json

# Point .env to PostgreSQL, create DB, then:
python manage.py migrate
python manage.py loaddata data_backup.json
```

Run separately for management and kiosk backends (different databases).
