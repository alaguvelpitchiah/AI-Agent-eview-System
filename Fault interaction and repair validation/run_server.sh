#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-8002}"

echo "========================================================================"
echo " Starting Fault Interaction & Repair Validation System Server"
echo " Server Port:      $PORT"
echo " Base URL:         http://127.0.0.1:$PORT"
echo " Web Dashboard:    http://127.0.0.1:$PORT/"
echo " Interactive Docs: http://127.0.0.1:$PORT/docs"
echo "========================================================================"

if [ -f "/home/alaguvel/ds_env/bin/python" ]; then
    PYTHON="/home/alaguvel/ds_env/bin/python"
elif [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

exec "$PYTHON" "$DIR/server.py"
