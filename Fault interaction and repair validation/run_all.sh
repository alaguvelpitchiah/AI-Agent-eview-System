#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================================"
echo " RUNNING ALL FAULT INTERACTION AND REPAIR VALIDATION SYSTEM FILES"
echo "========================================================================"

if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

exec "$PYTHON" "$DIR/run_all_system.py"
