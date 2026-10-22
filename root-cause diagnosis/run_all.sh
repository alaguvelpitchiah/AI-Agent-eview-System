#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================"
echo " RUNNING ALL ROOT-CAUSE DIAGNOSIS FILES"
echo "========================================================"

if [ -f "$DIR/phase3/.venv/bin/python" ]; then
    PYTHON="$DIR/phase3/.venv/bin/python"
else
    PYTHON="python3"
fi

exec "$PYTHON" "$DIR/phase3/run_all_diagnosis.py"
