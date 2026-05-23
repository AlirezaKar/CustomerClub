# CustomerClub Management – Backend Setup

This backend defaults to **SQLite** for local development (`DEBUG=True`) and uses **PostgreSQL** when you deploy with `DEBUG=False` and DB settings. It defines the same models as the main CustomerClub project so you can share one PostgreSQL database in production if you choose.

## 1. Environment files

- **Backend:** Copy `backend/.env.example` to `backend/.env`. For local dev, defaults use SQLite; add PostgreSQL variables when you turn off `DEBUG` for production.
- **Frontend:** Copy `frontend/.env.example` to `frontend/.env` (optional; defaults point to `http://localhost:8000/api`). Change `VITE_API_URL` if your API runs elsewhere.

## 2. Database (SQLite in development, PostgreSQL in production)

- **Default:** With `DEBUG=True` (the default in `.env.example`), Django uses **SQLite** at `backend/db.sqlite3`. No PostgreSQL install required for local work.
- **Production:** Set `DEBUG=False` and PostgreSQL variables in `.env`, or use `USE_POSTGRES=1`. See [docs/DATABASE.md](../docs/DATABASE.md).
- **Production:** Set `DEBUG=False` and PostgreSQL variables below; Django switches to PostgreSQL automatically.
- **Overrides (optional):**
  - `USE_POSTGRES=1` — use PostgreSQL even when `DEBUG=True` (e.g. test against a real DB locally).
  - `USE_SQLITE=1` — use SQLite even when `DEBUG=False` (rare; not for production).

### PostgreSQL (production or when `USE_POSTGRES=1`)

- Install PostgreSQL and create a database, e.g. `customerclub_management` (or use the same DB as the main project).
- Set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` in `backend/.env` (see `.env.example`).

## 3. Python and dependencies

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# or: source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

## 4. Migrations

```bash
python manage.py migrate
python manage.py createcachetable
```

Use the same commands for **SQLite** (dev) and **PostgreSQL** (production). With SQLite, `db.sqlite3` is created in `backend/` (gitignored).

`module_account.0002_initial` is **idempotent** on PostgreSQL/SQLite: if M2M join tables (for example `module_account_user_allowed_branches`) already exist from an older migration history, it updates Django’s migration state without failing on “relation already exists”.

If you still see a migration state mismatch (for example after restoring only part of `django_migrations`), align with:

`python manage.py migrate module_account 0002_initial --fake`

then `python manage.py migrate`.

Settings use `DatabaseCache`; `createcachetable` in the block above creates that table for both SQLite and PostgreSQL.

## 5. Run the server

```bash
python manage.py runserver
```

API base: `http://localhost:8000/api/`  
Admin: `http://localhost:8000/admin/`

## 6. Create a shop keeper (superuser + shop)

```bash
python manage.py createsuperuser
```

Then in Django Admin (`http://localhost:8000/admin/`):

1. Log in with the superuser.
2. Create a **Shop** (name + owner = that user).
3. A **Score** is created automatically for the shop.

(Or create a normal **User** in Account → Users, then create a Shop with that user as owner.)

## 7. Frontend (product creation page)

From project root:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5001` (Vite is configured for port 5001). Log in with the user that owns a shop, then use **Products** to add products. With the default dev setup, data lives in `backend/db.sqlite3`; in production it uses PostgreSQL if you set `DEBUG=False` and DB variables.
