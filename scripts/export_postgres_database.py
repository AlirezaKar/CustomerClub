#!/usr/bin/env python3
"""
Backup the Customer Club management PostgreSQL database.

Preferred: native ``pg_dump`` (custom format + plain SQL).
Fallback: Django ``dumpdata`` JSON (works with SQLite too).

Reads DB settings from Django_React_management/backend/.env

  python scripts/export_postgres_database.py
  python scripts/export_postgres_database.py --output-dir backups
  python scripts/export_postgres_database.py --format json
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "Django_React_management" / "backend"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "backups"


def _configure_stdio_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_db_settings() -> dict:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")

    import django

    django.setup()
    from django.conf import settings

    db = settings.DATABASES["default"]
    return {
        "engine": db["ENGINE"],
        "name": db["NAME"],
        "user": db.get("USER", ""),
        "password": db.get("PASSWORD", ""),
        "host": db.get("HOST", "localhost"),
        "port": str(db.get("PORT", "5432")),
    }


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def db_backup_label(db: dict) -> str:
    """Safe filename prefix (Postgres name or SQLite file stem)."""
    name = str(db["name"])
    if "sqlite" in db["engine"]:
        return Path(name).stem
    return name


def export_pg_dump(db: dict, output_dir: Path, plain_sql: bool, custom: bool) -> list[Path]:
    pg_dump = shutil.which("pg_dump")
    if not pg_dump:
        raise FileNotFoundError("pg_dump not found on PATH. Install PostgreSQL client tools.")

    output_dir.mkdir(parents=True, exist_ok=True)
    label = db_backup_label(db)
    base = f"{label}_{timestamp()}"
    written: list[Path] = []
    env = os.environ.copy()
    if db["password"]:
        env["PGPASSWORD"] = str(db["password"])

    common = [
        pg_dump,
        "-h",
        str(db["host"]),
        "-p",
        str(db["port"]),
        "-U",
        str(db["user"]),
        "-d",
        str(db["name"]),
        "--no-owner",
        "--no-acl",
    ]

    if custom:
        out = output_dir / f"{base}.dump"
        cmd = common + ["-Fc", "-f", str(out)]
        print(f"Running: {' '.join(cmd[:6])} ... -f {out.name}")
        subprocess.run(cmd, check=True, env=env)
        written.append(out)

    if plain_sql:
        out = output_dir / f"{base}.sql"
        cmd = common + ["-f", str(out)]
        print(f"Running: {' '.join(cmd[:6])} ... -f {out.name}")
        subprocess.run(cmd, check=True, env=env)
        written.append(out)

    return written


def export_dumpdata(db: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{db_backup_label(db)}_{timestamp()}.json"
    manage_py = BACKEND_DIR / "manage.py"
    cmd = [
        sys.executable,
        str(manage_py),
        "dumpdata",
        "--natural-foreign",
        "--natural-primary",
        "-e",
        "contenttypes",
        "-e",
        "auth.Permission",
        "--indent",
        "2",
        "-o",
        str(out),
    ]
    print(f"Running Django dumpdata -> {out.name}")
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    subprocess.run(cmd, check=True, cwd=str(BACKEND_DIR), env=env)
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup management database (PostgreSQL or SQLite).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Backup directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--format",
        choices=("auto", "pg_dump", "json"),
        default="auto",
        help="auto: pg_dump for PostgreSQL, else dumpdata JSON",
    )
    parser.add_argument("--sql-only", action="store_true", help="pg_dump plain .sql only (no .dump)")
    parser.add_argument("--dump-only", action="store_true", help="pg_dump custom .dump only (no .sql)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    args = parse_args(argv)

    if not BACKEND_DIR.is_dir():
        print(f"Backend not found: {BACKEND_DIR}", file=sys.stderr)
        return 1

    db = load_db_settings()
    is_postgres = "postgresql" in db["engine"]
    print(f"Database engine: {db['engine']}")
    print(f"Database name: {db['name']}")

    try:
        if args.format == "json" or (args.format == "auto" and not is_postgres):
            path = export_dumpdata(db, args.output_dir)
            print(f"Backup written: {path.resolve()}")
            return 0

        plain = not args.dump_only
        custom = not args.sql_only
        if args.sql_only and args.dump_only:
            print("Use at most one of --sql-only / --dump-only.", file=sys.stderr)
            return 1
        if not plain and not custom:
            custom = True

        paths = export_pg_dump(db, args.output_dir, plain_sql=plain, custom=custom)
        for p in paths:
            size_mb = p.stat().st_size / (1024 * 1024)
            print(f"Backup written: {p.resolve()} ({size_mb:.2f} MB)")
        return 0
    except FileNotFoundError as exc:
        print(f"{exc}", file=sys.stderr)
        if is_postgres:
            print("Falling back to Django dumpdata …", file=sys.stderr)
            path = export_dumpdata(db, args.output_dir)
            print(f"Backup written: {path.resolve()}")
            return 0
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Backup command failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
