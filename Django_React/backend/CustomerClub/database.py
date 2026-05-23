"""
Database configuration: SQLite for local dev, PostgreSQL for production.

Environment (see backend/.env.example):
  USE_POSTGRES=1     Force PostgreSQL
  USE_SQLITE=1       Force SQLite
  (default)          SQLite when DEBUG=True, PostgreSQL when DEBUG=False

  DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
"""
from __future__ import annotations

import os
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def build_databases(*, base_dir: Path, debug: bool) -> dict:
    db_name = os.environ.get("DB_NAME", "customerclub_kiosk")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")

    engine = (os.environ.get("DB_ENGINE") or "").strip()
    if _env_bool("USE_POSTGRES") or engine == "django.db.backends.postgresql":
        use_sqlite = False
    elif _env_bool("USE_SQLITE") or engine == "django.db.backends.sqlite3":
        use_sqlite = True
    else:
        use_sqlite = debug

    if use_sqlite:
        sqlite_name = os.environ.get("DB_NAME", "db.sqlite3")
        sqlite_path = Path(sqlite_name)
        if not sqlite_path.is_absolute():
            sqlite_path = base_dir / sqlite_name
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": sqlite_path,
                "OPTIONS": {"timeout": 20},
            }
        }

    # Shorter timeout in dev avoids blocking runserver when Postgres is down.
    connect_timeout = 2 if debug else 10

    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
            "CONN_MAX_AGE": 600 if not debug else 0,
            "CONN_HEALTH_CHECKS": not debug,
            "OPTIONS": {
                "connect_timeout": connect_timeout,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        }
    }
