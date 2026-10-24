#!/usr/bin/env bash
# Starts backend (FastAPI :8000) and frontend (Vite :5173) for local development on Linux/macOS.
# Usage: ./scripts/dev.sh [API_PORT] [WEB_PORT]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${1:-8000}"
WEB_PORT="${2:-5173}"

if [ ! -x "$ROOT/backend/.venv/bin/python" ]; then
  python3 -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/python" -m pip install --upgrade pip
  "$ROOT/backend/.venv/bin/python" -m pip install -e "$ROOT/backend[dev]"
fi
[ -d "$ROOT/frontend/node_modules" ] || (cd "$ROOT/frontend" && npm ci)

export CORS_ORIGINS="http://localhost:$WEB_PORT,http://127.0.0.1:$WEB_PORT"
(cd "$ROOT/backend" && .venv/bin/python -m uvicorn safeguard_pq.api.app:app --host 127.0.0.1 --port "$API_PORT") &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

echo "API      http://127.0.0.1:$API_PORT/docs"
echo "Frontend http://127.0.0.1:$WEB_PORT"
cd "$ROOT/frontend" && SAFEGUARD_API="http://127.0.0.1:$API_PORT" npm run dev -- --host 127.0.0.1 --port "$WEB_PORT"
