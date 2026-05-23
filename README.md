# CustomerClub (Production)

Two-app monorepo for the **Aras Customer Club**: a public **kiosk** (shop floor) and a **management** console (catalog, branches, offers).

| App | Folder | API (dev) | SPA (dev) |
|-----|--------|-----------|-----------|
| Kiosk (main) | `Django_React/` | http://127.0.0.1:8001/ | http://127.0.0.1:5002/ |
| Management | `Django_React_management/` | http://127.0.0.1:8000/ | http://127.0.0.1:5001/ |

Full setup, architecture, and operations: **[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)**.

## Quick start (Windows)

1. Create virtualenvs and install dependencies (see documentation).
2. Copy `backend/.env.example` → `backend/.env` in **both** backends and set `MANAGEMENT_SERVICE_API_KEY` to the same value.
3. Run migrations on **management** first, then kiosk.
4. Start everything:

```bat
start-all-dev.cmd
```

## Repository layout

```
Production/
├── Django_React/              # Kiosk: Django API + React (Vite) SPA
├── Django_React_management/   # Staff: Django API + React admin SPA
├── Dataset/                   # Seed data (articles, stores, predictions)
├── docs/                      # Project documentation
├── scripts/                   # DB import / backup utilities
├── backups/                   # pg_dump output (gitignored)
└── start-all-dev.cmd          # Launch all four dev processes
```

## Related docs

- [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) — installation, env vars, integration, performance
- [docs/DATABASE.md](docs/DATABASE.md) — SQLite vs PostgreSQL, stateless kiosk
- [scripts/README.md](scripts/README.md) — dataset import and backups
- [Django_React/README.md](Django_React/README.md) — kiosk app and NFC authentication
- [Django_React/docs/NFC_LOGIN.md](Django_React/docs/NFC_LOGIN.md) — NFC bridge (COM port readers)
