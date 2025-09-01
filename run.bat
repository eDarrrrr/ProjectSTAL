@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

REM 1) pilih interpreter python prioritas: 3.12 -> 3.11 -> default
set PY_CMD=
for %%V in (3.12 3.11) do (
  py -%%V -c "import sys" >nul 2>&1
  if !errorlevel! == 0 (
    set "PY_CMD=py -%%V"
    goto :gotpy
  )
)
REM fallback
set "PY_CMD=py -3"
:gotpy

echo [INFO] Python launcher: %PY_CMD%

REM 2) buat venv kalau belum ada
if not exist ".venv" (
  echo [INFO] Membuat virtualenv .venv ...
  %PY_CMD% -m venv .venv || (
    echo [ERROR] Gagal membuat venv. Pastikan Python ter-install.
    pause & exit /b 1
  )
)

REM 3) aktifkan venv + install requirements
call ".venv\Scripts\activate.bat"
python -c "import sys; print('[INFO] Python in venv:', sys.version)"
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

REM 4) jalankan GUI tanpa console
echo [INFO] Menjalankan main.py ...
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0
