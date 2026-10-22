#!/usr/bin/env bash
# ==============================================================================
# AI Agent Review and Performance Improvement System - Health & Status Checker
# ==============================================================================

echo "========================================================================"
echo "📊 AI Agent Review System - Services & Health Status"
echo "========================================================================"

check_service() {
    local name="$1"
    local port="$2"
    local url="$3"

    if curl -s -f -m 2 "$url" >/dev/null 2>&1; then
        echo -e " \033[0;32m● RUNNING\033[0m   Port $port | $name | $url"
    elif fuser "$port/tcp" >/dev/null 2>&1; then
        echo -e " \033[0;33m▲ ACTIVE\033[0m    Port $port | $name (Responding on socket)"
    else
        echo -e " \033[0;31m○ STOPPED\033[0m   Port $port | $name"
    fi
}

check_service "Unified Full-Stack Web Application (Phase 1-6)" "8004" "http://127.0.0.1:8004/api/health"
check_service "Streamlit Benchmark Dashboard"                   "8501" "http://127.0.0.1:8501"
check_service "AI Agent Monitoring & Execution Backend"         "8000" "http://127.0.0.1:8000/api/health"
check_service "Root-Cause Diagnosis Service (Phase 3)"          "8001" "http://127.0.0.1:8001/api/health"
check_service "Fault Interaction & Repair Validation (Phase 4)" "8002" "http://127.0.0.1:8002/api/health"
check_service "Orchestration & 8 Hard Gates (Phase 5)"          "8003" "http://127.0.0.1:8003/api/health"

echo "========================================================================"
echo "Active SQLite Databases:"
for db in \
    "Monitoring and Faliure Detection/ai-agent-review-system/backend/review.db" \
    "Dashboard and evaluation/phase3/phase6_results/app.db" \
    "Dashboard and evaluation/phase3/phase6_results/diagnoses.db" \
    "Dashboard and evaluation/phase3/phase6_results/repair_plans.db"; do
    if [ -f "$db" ]; then
        size=$(du -h "$db" | cut -f1)
        echo " [✓] $db ($size)"
    else
        echo " [-] $db (Not initialized yet)"
    fi
done
echo "========================================================================"
