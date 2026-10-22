#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PORT=8001

echo "========================================================"
echo " Starting AI Agent Root-Cause Diagnosis API Server"
echo " Server Port:      $PORT"
echo " Base URL:         http://127.0.0.1:$PORT"
echo " Interactive Docs: http://127.0.0.1:$PORT/docs"
echo "========================================================"

if [ -f "$DIR/.venv/bin/uvicorn" ]; then
    UVICORN="$DIR/.venv/bin/uvicorn"
else
    UVICORN="uvicorn"
fi

exec "$UVICORN" phase3.api:app --host 0.0.0.0 --port "$PORT" --reload
