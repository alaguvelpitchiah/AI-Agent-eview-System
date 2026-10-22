#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================================"
echo " RUNNING ALL DASHBOARD & EVALUATION (PHASE 6) PROJECT FILES"
echo "========================================================================"

if [ -f "/home/alaguvel/ds_env/bin/python" ]; then
    PYTHON="/home/alaguvel/ds_env/bin/python"
elif [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

exec "$PYTHON" "$DIR/run_all_system.py"
