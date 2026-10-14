#!/usr/bin/env bash
set -e

# Cleanly stop both processes when pressing Ctrl+C
cleanup() {
    echo ""
    echo "Shutting down DataForge services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup EXIT INT TERM

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================================="
echo " Starting DataForge Ecosystem"
echo " Backend : http://localhost:5000"
echo " Frontend: http://localhost:3000"
echo "=================================================="

# 1. Start Backend (FastAPI + Uvicorn)
if [ -d "$ROOT_DIR/backend/.venv" ]; then
    PYTHON_BIN="$ROOT_DIR/backend/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

(cd "$ROOT_DIR/backend" && "$PYTHON_BIN" main.py) &

# 2. Start Frontend (Next.js)
(cd "$ROOT_DIR/frontend" && npm run dev) &

# Wait for both processes
wait
