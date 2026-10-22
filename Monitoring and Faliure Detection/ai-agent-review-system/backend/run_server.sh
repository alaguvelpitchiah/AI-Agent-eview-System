#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-8000}"

echo "========================================================================"
echo " Starting AI Agent Review System - Agent Monitoring & Failure Detection"
echo " Server Port:      $PORT"
echo " Base URL:         http://127.0.0.1:$PORT"
echo " Interactive Docs: http://127.0.0.1:$PORT/docs"
echo " ReDoc Docs:       http://127.0.0.1:$PORT/redoc"
echo "========================================================================"

if [ -f "/home/alaguvel/ds_env/bin/python" ]; then
    PYTHON="/home/alaguvel/ds_env/bin/python"
elif [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

cd "$DIR"
exec "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
