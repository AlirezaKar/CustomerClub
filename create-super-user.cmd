@echo off
setlocal EnableExtensions
REM =============================================================================
REM  Create a Django superuser (CustomerClub management app — custom User model)
REM
REM  1. Edit ONLY the values in the "EDIT BELOW" block.
REM  2. Save this file, then double-click or run:  create-super-user.cmd
REM
REM  Uses: Django_React_management\backend\manage.py
REM  If you use another project (e.g. Django_React), change BACKEND_DIR below.
REM =============================================================================

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%Django_React_management\backend"

if not exist "%BACKEND_DIR%\manage.py" (
  echo ERROR: manage.py not found at:
  echo   %BACKEND_DIR%\manage.py
  echo Fix BACKEND_DIR in this script if your layout differs.
  exit /b 1
)

REM ---------------------------------------------------------------------------
REM  EDIT BELOW — superuser login (username + password + phone are required)
REM ---------------------------------------------------------------------------
set "SU_USERNAME=aras"
set "SU_PASSWORD=aras"
set "SU_PHONE=09123456789"
set "SU_EMAIL="
set "SU_FIRST_NAME="
set "SU_LAST_NAME="
REM ---------------------------------------------------------------------------
REM  STOP EDITING
REM ---------------------------------------------------------------------------

cd /d "%BACKEND_DIR%" || exit /b 1

REM Django reads these for: python manage.py createsuperuser --noinput
set "DJANGO_SUPERUSER_USERNAME=%SU_USERNAME%"
set "DJANGO_SUPERUSER_PASSWORD=%SU_PASSWORD%"
set "DJANGO_SUPERUSER_PHONE_NUMBER=%SU_PHONE%"
if not "%SU_EMAIL%"=="" set "DJANGO_SUPERUSER_EMAIL=%SU_EMAIL%"
if not "%SU_FIRST_NAME%"=="" set "DJANGO_SUPERUSER_FIRST_NAME=%SU_FIRST_NAME%"
if not "%SU_LAST_NAME%"=="" set "DJANGO_SUPERUSER_LAST_NAME=%SU_LAST_NAME%"

echo.
echo Creating superuser (noinput)...
echo   Username: %SU_USERNAME%
echo   Phone:    %SU_PHONE%
echo.

python manage.py createsuperuser --noinput --username "%SU_USERNAME%"
if errorlevel 1 (
  echo.
  echo FAILED. Common causes:
  echo   - Username or phone number already exists
  echo   - Missing required field for your User model (check module_account.User)
  echo   - Wrong BACKEND_DIR / Django settings
  echo.
  echo You can still create one interactively with:
  echo   cd /d "%BACKEND_DIR%"
  echo   python manage.py createsuperuser
  echo.
  exit /b 1
)

echo.
echo Superuser created.
echo.
endlocal
