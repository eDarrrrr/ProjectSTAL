@echo off
setlocal ENABLEDELAYEDEXPANSION

REM pindah ke folder skrip ini
cd /d "%~dp0"

REM 1) buat venv kalau belum ada
if not exist ".venv" (
  echo [INFO] Membuat virtualenv .venv ...
  py -3 -m venv .venv || (
    echo [ERROR] Gagal membuat venv. Pastikan Python ter-install dan 'py' tersedia.
    pause & exit /b 1
  )
)

REM 2) aktifkan venv + install requirements
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if exist requirements.txt (
  echo [INFO] Install dependencies dari requirements.txt ...
  python -m pip install -r requirements.txt || (
    echo [ERROR] Gagal install dependencies.
    pause & exit /b 1
  )
) else (
  echo [WARN] requirements.txt tidak ditemukan. Lewati install.
)

REM 3) jalankan app dengan interpreter venv
echo [INFO] Menjalankan main.py ...
start "" ".venv\Scripts\pythonw.exe" main.py
set EXITCODE=%ERRORLEVEL%

echo.
echo [INFO] Program selesai (exit code %EXITCODE%), membuka program...
pause
exit /b %EXITCODE%
