#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "========================================================"
echo " RUNNING ALL ROOT-CAUSE DIAGNOSIS FILES"
echo "========================================================"

if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

exec "$PYTHON" "$DIR/run_all_diagnosis.py"
