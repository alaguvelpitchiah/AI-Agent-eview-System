#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=8001

echo "========================================================"
echo " Starting AI Agent Root-Cause Diagnosis API Server"
echo " Server Port:      $PORT"
echo " Base URL:         http://127.0.0.1:$PORT"
echo " Interactive Docs: http://127.0.0.1:$PORT/docs"
echo "========================================================"

if [ -f "/home/alaguvel/ds_env/bin/python" ]; then
    PYTHON="/home/alaguvel/ds_env/bin/python"
elif [ -f "$DIR/phase3/.venv/bin/python" ]; then
    PYTHON="$DIR/phase3/.venv/bin/python"
elif [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

exec "$PYTHON" "$DIR/phase3/phase3/api.py"
