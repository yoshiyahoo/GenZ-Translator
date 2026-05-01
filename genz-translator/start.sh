#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8000}"

python -m uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
