#!/usr/bin/env python3
"""Fault Interaction and Repair Validation System - Full System Runner.

Executes:
1. Automated Test Suite (pytest - 27 tests across Phase 3 and Phase 4)
2. Phase 3 Root-Cause Diagnosis Benchmark (phase3.demo)
3. Phase 4 Fault Interaction & Repair Validation Demo (phase4.demo4)
4. Checks / Starts the Unified API & Dashboard Server on Port 8002
5. Live HTTP API requests to Port 8002 verifying diagnosis, interaction analysis, repair validation, and conflict testing
6. Prints prominent banner displaying the active Port and Dashboard URL
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
PORT = int(os.environ.get("PORT", 8002))
BASE_URL = f"http://127.0.0.1:{PORT}"

VENV_PYTHON = DIR / ".venv" / "bin" / "python"
VENV_PYTEST = DIR / ".venv" / "bin" / "pytest"
PYTHON_EXEC = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
PYTEST_EXEC = str(VENV_PYTEST) if VENV_PYTEST.exists() else "pytest"


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str) -> dict | list:
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_server_ready(url: str) -> bool:
    try:
        res = get_json(f"{url}/api/health")
        return res.get("status") == "ok"
    except Exception:
        return False


def ensure_server_running():
    if is_server_ready(BASE_URL):
        print(f"-> API Server is already live on {BASE_URL} (Port {PORT})")
        return None

    print(f"-> Starting API & Dashboard Server on Port {PORT} in background...")
    proc = subprocess.Popen(
        [PYTHON_EXEC, str(DIR / "server.py")],
        cwd=str(DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(30):
        if is_server_ready(BASE_URL):
            print(f"-> Server successfully started and verified on {BASE_URL} (Port {PORT})")
            return proc
        time.sleep(0.3)

    print(f"WARNING: Server did not respond within timeout on Port {PORT}.")
    return proc


def main():
    print("=" * 76)
    print("  FAULT INTERACTION AND REPAIR VALIDATION SYSTEM: FULL SYSTEM RUN")
    print("=" * 76)

    # 1. Run Automated Unit Tests
    print("\n[STEP 1/5] Running All Test Files (pytest -q)...")
    test_proc = subprocess.run([PYTEST_EXEC, "-q"], cwd=str(DIR / "phase3"), capture_output=True, text=True)
    print(test_proc.stdout.strip())
    if test_proc.returncode != 0:
        print("Test stderr:", test_proc.stderr)
        sys.exit(test_proc.returncode)

    # 2. Run Phase 3 Evaluation Demo
    print("\n[STEP 2/5] Running Phase 3 Root-Cause Diagnosis Engine Demo (phase3.demo)...")
    demo3_proc = subprocess.run([PYTHON_EXEC, "-m", "phase3.demo"], cwd=str(DIR / "phase3"), capture_output=True, text=True)
    print(demo3_proc.stdout.strip())

    # 3. Run Phase 4 Interaction & Repair Validation Demo
    print("\n[STEP 3/5] Running Phase 4 Fault Interaction & Repair Planner Demo (phase4.demo4)...")
    demo4_proc = subprocess.run([PYTHON_EXEC, "-m", "phase4.demo4"], cwd=str(DIR / "phase3"), capture_output=True, text=True)
    print(demo4_proc.stdout.strip())

    # 4. Start / Verify Server on Port 8002
    print(f"\n[STEP 4/5] Launching & Verifying System Web & API Server on Port {PORT}...")
    ensure_server_running()
    health = get_json(f"{BASE_URL}/api/health")
    print(f"-> Port Status:       ONLINE ({PORT})")
    print(f"-> Health Response:   {health}")
    print(f"-> Web Dashboard:     {BASE_URL}/")
    print(f"-> Interactive Docs:  {BASE_URL}/docs")
    print(f"-> ReDoc Docs:        {BASE_URL}/redoc")

    # 5. Live End-to-End API Requests
    print(f"\n[STEP 5/5] Executing Live API Calls Against Port {PORT}...")

    # A. Test Root-Cause Diagnosis Endpoint
    print("\n--- A. POST /api/agents/toy/diagnose (Phase 3 API) ---")
    dx_payload = {
        "input": {"resume": "Python and SQL developer with Docker", "required": ["python", "sql"]},
        "expected": {"decision": "match"},
        "faults": ["TOY-F02", "TOY-F03"],
        "run_ref": "live-test-joint-faults",
    }
    dx_res = post_json(f"{BASE_URL}/api/agents/toy/diagnose", dx_payload)
    print(f"  Diagnosis ID:      {dx_res.get('diagnosis_id')}")
    print(f"  Verdict:           {dx_res.get('verdict')}")
    print(f"  Confidence:        {dx_res.get('confidence')}")
    print(f"  Suspected Stages:  {dx_res.get('suspected_stages')}")
    print(f"  Pattern:           {dx_res.get('interaction_pattern')}")

    # B. Test Repair Plan & Interaction Analysis Endpoint (Scenario with conflict trap)
    print("\n--- B. POST /api/agents/toy/repair-plan (Phase 4 API: Conflict Trap Scenario) ---")
    plan_payload = {
        "target": {
            "case_id": "R6",
            "input": {"resume": "I know python", "required": ["python", "sql"]},
            "expected": {"decision": "match"},
        },
        "faults": ["TOY-F03"],
        "regression": [
            {"case_id": "R1", "input": {"resume": "Python and SQL developer with Docker", "required": ["python", "sql"]}, "expected": {"decision": "match"}},
            {"case_id": "RX", "input": {"resume": "I know python", "required": ["python", "sql", "docker"]}, "expected": {"decision": "reject"}},
        ],
    }
    plan_res = post_json(f"{BASE_URL}/api/agents/toy/repair-plan", plan_payload)
    plan_data = plan_res.get("plan", {})
    inter_data = plan_res.get("interaction", {})
    print(f"  Plan ID:           {plan_res.get('plan_id')}")
    print(f"  Plan Status:       {plan_data.get('status')}")
    print(f"  Selected Repairs:  {plan_data.get('selected')}")
    print(f"  Interaction Kind:  {inter_data.get('summary')}")
    print(f"  Conflicts Found:   {plan_data.get('conflicts')}")
    print(f"  Warnings:          {plan_data.get('warnings')}")

    # C. Test Repair Plan & Interaction Analysis Endpoint (Synergistic Faults Scenario)
    print("\n--- C. POST /api/agents/toy/repair-plan (Phase 4 API: Synergistic Joint Faults) ---")
    syn_payload = {
        "target": {
            "case_id": "R1",
            "input": {"resume": "Python and SQL developer with Docker", "required": ["python", "sql"]},
            "expected": {"decision": "match"},
        },
        "faults": ["TOY-F02", "TOY-F03"],
        "regression": [
            {"case_id": "R2", "input": {"resume": "Experienced developer with python and sql", "required": ["python", "sql"]}, "expected": {"decision": "match"}},
            {"case_id": "RX", "input": {"resume": "I know python", "required": ["python", "sql", "docker"]}, "expected": {"decision": "reject"}},
        ],
    }
    syn_res = post_json(f"{BASE_URL}/api/agents/toy/repair-plan", syn_payload)
    syn_plan = syn_res.get("plan", {})
    syn_inter = syn_res.get("interaction", {})
    print(f"  Plan ID:           {syn_res.get('plan_id')}")
    print(f"  Plan Status:       {syn_plan.get('status')}")
    print(f"  Selected Repairs:  {syn_plan.get('selected')}")
    print(f"  Interaction Kind:  {syn_inter.get('summary')} (2^k factorial outcomes: {len(syn_inter.get('outcomes', []))} runs)")

    # D. Query Stored Records
    print(f"\n--- D. GET /api/repair-plans & GET /api/diagnoses (SQLite Storage) ---")
    plans = get_json(f"{BASE_URL}/api/repair-plans")
    diagnoses = get_json(f"{BASE_URL}/api/diagnoses")
    print(f"  Total Repair Plans Stored:  {len(plans)}")
    print(f"  Total Diagnoses Stored:     {len(diagnoses)}")

    print("\n" + "=" * 76)
    print("  PROJECT FILES EXECUTED & SYSTEM OPERATING ON PORT:")
    print(f"  >> http://127.0.0.1:{PORT}/ << (Port {PORT})")
    print("=" * 76)


if __name__ == "__main__":
    main()
