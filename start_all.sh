#!/usr/bin/env bash
# ==============================================================================
# AI Agent Review and Performance Improvement System - Master Full-Stack Launcher
# ==============================================================================
set -e

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="/home/alaguvel/ds_env/bin/python"

if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="$(which python3)"
fi

echo "========================================================================"
echo "⚡ Starting AI Agent Review & Performance Improvement Full-Stack System"
echo " Workspace: $WORKSPACE_DIR"
echo " Python:    $PYTHON_EXEC"
echo "========================================================================"

mkdir -p "$WORKSPACE_DIR/.logs"

# Function to check if a port is listening
is_port_open() {
    local port=$1
    if command -v fuser >/dev/null 2>&1; then
        fuser "$port/tcp" >/dev/null 2>&1
        return $?
    elif command -v ss >/dev/null 2>&1; then
        ss -tuln | grep -q ":$port "
        return $?
    else
        netstat -tuln 2>/dev/null | grep -q ":$port "
        return $?
    fi
}

# 1. Start Phase 1 & 2: AI Agent Monitoring & Failure Detection (Port 8000)
if is_port_open 8000; then
    echo "[✓] Port 8000 (Agent Monitoring & Execution) is already running."
else
    echo "[+] Launching Agent Monitoring & Failure Detection on Port 8000..."
    setsid nohup bash -c "cd '$WORKSPACE_DIR/Monitoring and Faliure Detection/ai-agent-review-system/backend' && exec '$PYTHON_EXEC' -m uvicorn app.main:app --host 0.0.0.0 --port 8000" </dev/null > "$WORKSPACE_DIR/.logs/port_8000.log" 2>&1 &
fi

# 2. Start Phase 3: Root-Cause Diagnosis Service (Port 8001)
if is_port_open 8001; then
    echo "[✓] Port 8001 (Root-Cause Diagnosis) is already running."
else
    echo "[+] Launching Root-Cause Diagnosis on Port 8001..."
    setsid nohup bash -c "cd '$WORKSPACE_DIR/root-cause diagnosis' && exec '$PYTHON_EXEC' phase3/phase3/api.py" </dev/null > "$WORKSPACE_DIR/.logs/port_8001.log" 2>&1 &
fi

# 3. Start Phase 4: Fault Interaction & Repair Validation (Port 8002)
if is_port_open 8002; then
    echo "[✓] Port 8002 (Fault Interaction & Repair Validation) is already running."
else
    echo "[+] Launching Repair Validation on Port 8002..."
    setsid nohup bash -c "cd '$WORKSPACE_DIR/Fault interaction and repair validation' && exec '$PYTHON_EXEC' server.py" </dev/null > "$WORKSPACE_DIR/.logs/port_8002.log" 2>&1 &
fi

# 4. Start Phase 5: Repairs, Conflicts & Orchestration (Port 8003)
if is_port_open 8003; then
    echo "[✓] Port 8003 (Orchestration & 8 Hard Gates) is already running."
else
    echo "[+] Launching Orchestration & Hard Gates on Port 8003..."
    setsid nohup bash -c "cd '$WORKSPACE_DIR/Repairs, conflicts, validation, orchestration' && exec '$PYTHON_EXEC' server.py" </dev/null > "$WORKSPACE_DIR/.logs/port_8003.log" 2>&1 &
fi

# 5. Start Phase 6: Unified Full-Stack Web Application (Port 8004)
if is_port_open 8004; then
    echo "[✓] Port 8004 (Unified Web Dashboard & Benchmark) is already running."
else
    echo "[+] Launching Unified Full-Stack Web Application on Port 8004..."
    setsid nohup bash -c "cd '$WORKSPACE_DIR/Dashboard and evaluation' && exec '$PYTHON_EXEC' server.py" </dev/null > "$WORKSPACE_DIR/.logs/port_8004.log" 2>&1 &
fi

# 6. Start Streamlit Visual Dashboard (Port 8501)
if is_port_open 8501; then
    echo "[✓] Port 8501 (Streamlit Visual Dashboard) is already running."
else
    echo "[+] Launching Streamlit Benchmark UI on Port 8501..."
    setsid nohup bash -c "cd '$WORKSPACE_DIR/Dashboard and evaluation/phase3' && exec '$PYTHON_EXEC' -m streamlit run phase6/dashboard.py --server.port 8501 --server.headless true" </dev/null > "$WORKSPACE_DIR/.logs/port_8501.log" 2>&1 &
fi

sleep 2

echo ""
echo "========================================================================"
echo "🚀 AI AGENT REVIEW & PERFORMANCE IMPROVEMENT SYSTEM IS ONLINE!"
echo "========================================================================"
echo " 🌐 Full-Stack Web Dashboard:  http://127.0.0.1:8004/"
echo " 📊 Streamlit Benchmark UI:    http://127.0.0.1:8501/"
echo " 📚 Full API Documentation:    http://127.0.0.1:8004/docs"
echo " 📑 Interactive ReDoc:         http://127.0.0.1:8004/redoc"
echo ""
echo " Standalone Microservice Ports:"
echo " - Port 8000: AI Agent Monitoring & Execution API  (http://127.0.0.1:8000/docs)"
echo " - Port 8001: Root-Cause Diagnosis Service API    (http://127.0.0.1:8001/docs)"
echo " - Port 8002: Fault Interaction Analysis API     (http://127.0.0.1:8002/docs)"
echo " - Port 8003: Orchestrator & 8 Hard Gates API    (http://127.0.0.1:8003/docs)"
echo "========================================================================"
echo " Run './status.sh' to inspect real-time service health."
echo " Run './stop_all.sh' to gracefully stop all background servers."
echo "========================================================================"
