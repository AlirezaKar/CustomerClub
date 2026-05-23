@echo off
setlocal
set "ROOT=%~dp0"

echo CustomerClub dev stack
echo   Django_React API        http://127.0.0.1:8001/
echo   Django_React SPA        http://127.0.0.1:5002/
echo   Management API         http://127.0.0.1:8000/
echo   Management SPA          http://127.0.0.1:5001/
echo.

start "CustomerClub API (8001)" cmd /k cd /d "%ROOT%Django_React\backend" ^&^& call "%ROOT%Django_React\.venv\Scripts\activate.bat" ^&^& python manage.py runserver 8001 --skip-checks
start "Management API (8000)" cmd /k cd /d "%ROOT%Django_React_management\backend" ^&^& call "%ROOT%Django_React_management\.venv3.12\Scripts\activate.bat" ^&^& python manage.py runserver 8000 --skip-checks
start "CustomerClub UI (5002)" cmd /k cd /d "%ROOT%Django_React\frontend" ^&^& npm run dev
start "Management UI (5001)" cmd /k cd /d "%ROOT%Django_React_management\frontend" ^&^& npm run dev

echo Opened four windows. Close each window to stop that service.
endlocal
