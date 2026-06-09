#!/usr/bin/env bash
# LocalMeshAI — one-command dev launcher (macOS/Linux)
#
#     ./start-dev.sh
#
# Starts the FastAPI backend and the Vite frontend. First run creates the backend venv and
# installs deps if missing. Ctrl-C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV="$BACKEND/.venv"

if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating backend virtual environment..."
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip
  "$VENV/bin/python" -m pip install -r "$BACKEND/requirements.txt"
fi

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND" && npm install)
fi

echo "Launching backend on http://localhost:8000 ..."
(cd "$BACKEND" && "$VENV/bin/python" -m uvicorn main:app --reload --port 8000) &
BACKEND_PID=$!

echo "Launching frontend on http://localhost:5173 ..."
(cd "$FRONTEND" && npm run dev) &
FRONTEND_PID=$!

trap 'echo; echo "Stopping..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' INT TERM
wait
