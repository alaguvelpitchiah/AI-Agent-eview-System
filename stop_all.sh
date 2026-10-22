#!/usr/bin/env bash
# ==============================================================================
# AI Agent Review and Performance Improvement System - Graceful Shutdown
# ==============================================================================

echo "========================================================================"
echo "🛑 Stopping AI Agent Review System background processes..."
echo "========================================================================"

for port in 8000 8001 8002 8003 8004 8501; do
    if command -v fuser >/dev/null 2>&1; then
        pid=$(fuser "$port/tcp" 2>/dev/null || true)
        if [ -n "$pid" ]; then
            echo "[+] Stopping process on port $port (PID: $pid)..."
            fuser -k "$port/tcp" 2>/dev/null || true
        fi
    fi
done

sleep 1
echo "[✓] All system processes on ports 8000-8004 and 8501 have been stopped."
