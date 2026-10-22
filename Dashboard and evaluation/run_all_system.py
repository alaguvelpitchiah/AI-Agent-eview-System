#!/usr/bin/env python3
"""AI Agent Review and Performance Improvement System - Dashboard & Evaluation Full System Runner.

Executes:
1. Automated Test Suite (pytest - 67 comprehensive tests across Phase 3, Phase 4, Phase 5, Phase 6)
2. Phase 3 Root-Cause Diagnosis Benchmark (phase3.demo)
3. Phase 4 Fault Interaction & Repair Validation Demo (phase4.demo4)
4. Phase 5 Orchestration, 8 Hard Gates & Failure Memory Demo (phase5.demo5)
5. Phase 6 Final Benchmark Evaluation (phase6.run_benchmark)
6. Streamlit Interactive Dashboard on Port 8501
7. Unified API & Web Dashboard Server on Port 8004
8. Live HTTP API Verification to Port 8004 and Port 8501
9. Prominent Banner displaying Active Project Ports and URLs
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

DIR = Path(__file__).resolve().parent
PHASE3_DIR = DIR / "phase3"
PORT = int(os.environ.get("PORT", 8004))
STREAMLIT_PORT = int(os.environ.get("STREAMLIT_PORT", 8501))
BASE_URL = f"http://127.0.0.1:{PORT}"
STREAMLIT_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"

# Preferred Python interpreter with installed dependencies
DS_ENV_PYTHON = Path("/home/alaguvel/ds_env/bin/python")
DS_ENV_PYTEST = Path("/home/alaguvel/ds_env/bin/pytest")
DS_ENV_STREAMLIT = Path("/home/alaguvel/ds_env/bin/streamlit")

PYTHON_EXEC = str(DS_ENV_PYTHON) if DS_ENV_PYTHON.exists() else sys.executable
PYTEST_EXEC = str(DS_ENV_PYTEST) if DS_ENV_PYTEST.exists() else "pytest"
STREAMLIT_EXEC = str(DS_ENV_STREAMLIT) if DS_ENV_STREAMLIT.exists() else "streamlit"


def banner(title: str, char: str = "="):
    line = char * 80
    print(f"\n{line}")
    print(f" {title.upper()}")
    print(f"{line}\n")


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "TestRunner"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_server_ready(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status in (200, 304)
    except Exception:
        return False


def run_command_live(cmd: list[str], cwd: Path | None = None, title: str = ""):
    if title:
        print(f"-> {title}")
    res = subprocess.run(cmd, cwd=str(cwd or DIR))
    if res.returncode != 0:
        print(f"WARNING: Command failed with exit code {res.returncode}: {' '.join(cmd)}")
    return res.returncode == 0


def ensure_streamlit_running():
    if is_server_ready(STREAMLIT_URL):
        print(f"-> Streamlit Dashboard is already LIVE on {STREAMLIT_URL} (Port {STREAMLIT_PORT})")
        return None

    print(f"-> Starting Streamlit Dashboard on Port {STREAMLIT_PORT} in background...")
    proc = subprocess.Popen(
        [
            STREAMLIT_EXEC,
            "run",
            "phase6/dashboard.py",
            "--server.port",
            str(STREAMLIT_PORT),
            "--server.headless",
            "true",
        ],
        cwd=str(PHASE3_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(25):
        time.sleep(0.5)
        if is_server_ready(STREAMLIT_URL):
            print(f"-> Streamlit Dashboard is UP and responding at {STREAMLIT_URL}")
            return proc
    print(f"-> Streamlit Dashboard process launched (PID: {proc.pid})")
    return proc


def ensure_server_running():
    if is_server_ready(f"{BASE_URL}/api/health"):
        print(f"-> Unified API & Dashboard Server is already LIVE on {BASE_URL} (Port {PORT})")
        return None

    print(f"-> Starting Unified API & Dashboard Server on Port {PORT} in background...")
    proc = subprocess.Popen(
        [PYTHON_EXEC, str(DIR / "server.py")],
        cwd=str(DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "PORT": str(PORT), "STREAMLIT_PORT": str(STREAMLIT_PORT)},
        start_new_session=True,
    )
    for _ in range(25):
        time.sleep(0.5)
        if is_server_ready(f"{BASE_URL}/api/health"):
            print(f"-> Unified Server is UP and responding at {BASE_URL}")
            return proc
    print(f"-> Server launched (PID: {proc.pid})")
    return proc


def main():
    banner("1. Running Automated Test Suite (pytest)")
    run_command_live([PYTEST_EXEC, "-q"], cwd=PHASE3_DIR, title="Executing pytest suite across tests/")

    banner("2. Running Phase 3 Root-Cause Diagnosis Benchmark (phase3.demo)")
    run_command_live([PYTHON_EXEC, "-m", "phase3.demo"], cwd=PHASE3_DIR, title="Executing Phase 3 Demo")

    banner("3. Running Phase 4 Fault Interaction & Repair Planning Demo (phase4.demo4)")
    run_command_live([PYTHON_EXEC, "-m", "phase4.demo4"], cwd=PHASE3_DIR, title="Executing Phase 4 Demo")

    banner("4. Running Phase 5 Orchestration, Hard Gates & Memory Demo (phase5.demo5)")
    run_command_live([PYTHON_EXEC, "-m", "phase5.demo5"], cwd=PHASE3_DIR, title="Executing Phase 5 Demo")

    banner("5. Running Phase 6 Final Benchmark Evaluation (phase6.run_benchmark)")
    run_command_live(
        [PYTHON_EXEC, "-m", "phase6.run_benchmark", "--seed", "7", "--out", "phase6_results"],
        cwd=PHASE3_DIR,
        title="Executing Phase 6 Benchmark (39 scenarios, Wilson CIs, report generation)",
    )

    banner("6. Starting & Verifying Project Servers & Ports")
    ensure_streamlit_running()
    ensure_server_running()

    banner("7. Executing Live Verification of Endpoints")
    try:
        health = get_json(f"{BASE_URL}/api/health")
        print(f"  [OK] Health Check: {health.get('system')} (Server Port {health.get('server_port')})")
        
        bench_summary = get_json(f"{BASE_URL}/api/benchmark/summary")
        print(f"  [OK] Benchmark Summary: {bench_summary.get('meta', {}).get('scenarios')} Scenarios loaded")

        walkthrough_res = post_json(
            f"{BASE_URL}/api/benchmark/walkthrough",
            {"sid": "double_synergistic:F02+F03:P-n2k2-plain", "residual_check": True},
        )
        print(f"  [OK] Live Scenario Walkthrough: sid=double_synergistic:F02+F03:P-n2k2-plain outcome={walkthrough_res.get('outcome')}")
        selected_repairs = [r.get('repair_id') for r in walkthrough_res.get('selected_repairs', [])]
        print(f"       Selected Validated Repairs: {', '.join(selected_repairs) or 'None'}")
    except Exception as e:
        print(f"  [WARNING] Verification query failed: {e}")

    banner("PROJECT EXECUTION COMPLETE - ACTIVE PORTS & DASHBOARDS")
    print(f"  ==========================================================================")
    print(f"   PROJECT NAME:        AI Agent Review & Performance Improvement System")
    print(f"   PROJECT COMPONENT:   Dashboard & Evaluation (Phase 6 Final System)")
    print(f"  ==========================================================================")
    print(f"   ACTIVE SERVER PORT:  {PORT}")
    print(f"   STREAMLIT UI PORT:   {STREAMLIT_PORT}")
    print(f"  --------------------------------------------------------------------------")
    print(f"   Unified Web Dashboard:    http://127.0.0.1:{PORT}/")
    print(f"   Interactive Streamlit UI: http://127.0.0.1:{STREAMLIT_PORT}")
    print(f"   OpenAPI Swagger Docs:     http://127.0.0.1:{PORT}/docs")
    print(f"   ReDoc Documentation:      http://127.0.0.1:{PORT}/redoc")
    print(f"   Official HTML Report:     http://127.0.0.1:{PORT}/api/benchmark/report/html")
    print(f"  ==========================================================================\n")


if __name__ == "__main__":
    main()
