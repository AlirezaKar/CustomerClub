# CustomerClub — Management (Django + React)

Staff console and **source of truth** for shops, branches, products, offers, and end users.

| Component | Path | Dev URL |
|-----------|------|---------|
| API | `backend/` | http://127.0.0.1:8000/ |
| SPA | `frontend/` | http://127.0.0.1:5001/ |

See [../README.md](../README.md) and [../docs/DOCUMENTATION.md](../docs/DOCUMENTATION.md).

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 8000

cd ../frontend
npm install
npm run dev
```

Integration API for the kiosk: set `MANAGEMENT_SERVICE_API_KEY` in `backend/.env` (same value as kiosk `Django_React/backend/.env`).
