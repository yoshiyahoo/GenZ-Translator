@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
  py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

if "%HOST%"=="" set HOST=127.0.0.1
if "%PORT%"=="" set PORT=8000

python -m uvicorn backend.main:app --host %HOST% --port %PORT% --reload
