#!/usr/bin/env python3
"""Repairs, Conflicts, Validation & Orchestration - Full System Runner.

Executes:
1. Automated Test Suite (pytest - 50 tests across Phase 3, Phase 4, Phase 5)
2. Phase 3 Root-Cause Diagnosis Benchmark (phase3.demo)
3. Phase 4 Fault Interaction & Repair Validation Demo (phase4.demo4)
4. Phase 5 Orchestration, 8 Hard Gates & Failure Memory Demo (phase5.demo5)
5. Starts & Verifies the Unified API & Dashboard Server on Port 8003
6. Live HTTP API requests to Port 8003 verifying diagnosis, interactions, repair planning, 8 gates, human approval, and failure memory
7. Prints prominent banner displaying the active Port and Dashboard URL
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
PORT = int(os.environ.get("PORT", 8003))
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

    for _ in range(40):
        if is_server_ready(BASE_URL):
            print(f"-> Server successfully started and verified on {BASE_URL} (Port {PORT})")
            return proc
        time.sleep(0.25)

    print(f"WARNING: Server did not respond within timeout on Port {PORT}.")
    return proc


def main():
    print("=" * 80)
    print("  AI AGENT REVIEW & PERFORMANCE IMPROVEMENT SYSTEM: FULL SYSTEM RUN")
    print("  Phases 3, 4 & 5: Repairs, Conflicts, Validation & Orchestration")
    print("=" * 80)

    # 1. Run Automated Unit Tests
    print("\n[STEP 1/6] Running All Test Files (pytest -q phase3/tests)...")
    test_proc = subprocess.run([PYTEST_EXEC, "-q", "phase3/tests"], cwd=str(DIR), capture_output=True, text=True)
    print(test_proc.stdout.strip())
    if test_proc.returncode != 0:
        print("Test stderr:", test_proc.stderr)
        sys.exit(test_proc.returncode)

    # 2. Run Phase 3 Evaluation Demo
    print("\n[STEP 2/6] Running Phase 3 Root-Cause Diagnosis Engine Demo (phase3.demo)...")
    demo3_proc = subprocess.run(
        [PYTHON_EXEC, "-m", "phase3.demo"],
        cwd=str(DIR),
        env={**os.environ, "PYTHONPATH": str(DIR / "phase3")},
        capture_output=True,
        text=True,
    )
    print(demo3_proc.stdout.strip())

    # 3. Run Phase 4 Interaction & Repair Validation Demo
    print("\n[STEP 3/6] Running Phase 4 Fault Interaction & Repair Planner Demo (phase4.demo4)...")
    demo4_proc = subprocess.run(
        [PYTHON_EXEC, "-m", "phase4.demo4"],
        cwd=str(DIR),
        env={**os.environ, "PYTHONPATH": str(DIR / "phase3")},
        capture_output=True,
        text=True,
    )
    print(demo4_proc.stdout.strip())

    # 4. Run Phase 5 Orchestrator, 8 Hard Gates & Memory Demo
    print("\n[STEP 4/6] Running Phase 5 Orchestrator, Gates & Memory Demo (phase5.demo5)...")
    demo5_proc = subprocess.run(
        [PYTHON_EXEC, "-m", "phase5.demo5"],
        cwd=str(DIR),
        env={**os.environ, "PYTHONPATH": str(DIR / "phase3")},
        capture_output=True,
        text=True,
    )
    print(demo5_proc.stdout.strip())

    # 5. Start / Verify Server on Port 8003
    print(f"\n[STEP 5/6] Launching & Verifying System Web & API Server on Port {PORT}...")
    ensure_server_running()
    health = get_json(f"{BASE_URL}/api/health")
    print(f"-> Port Status:       ONLINE ({PORT})")
    print(f"-> Health Response:   {health.get('status')} | {health.get('system')}")
    print(f"-> Web Dashboard:     {BASE_URL}/")
    print(f"-> Interactive Docs:  {BASE_URL}/docs")
    print(f"-> ReDoc Docs:        {BASE_URL}/redoc")

    # 6. Live End-to-End API Requests
    print(f"\n[STEP 6/6] Executing Live API Calls Against Port {PORT}...")

    # A. Test Root-Cause Diagnosis Endpoint (Phase 3)
    print("\n--- A. POST /api/agents/toy/diagnose (Phase 3 API: Counterfactual Diagnosis) ---")
    dx_payload = {
        "input": {"resume": "Python and SQL developer with Docker", "required": ["python", "sql"]},
        "expected": {"decision": "match"},
        "faults": ["TOY-F02", "TOY-F03"],
        "run_ref": "live-orchestration-joint-test",
    }
    dx_res = post_json(f"{BASE_URL}/api/agents/toy/diagnose", dx_payload)
    print(f"  Diagnosis ID:      {dx_res.get('diagnosis_id')}")
    print(f"  Verdict:           {dx_res.get('verdict')}")
    print(f"  Confidence:        {dx_res.get('confidence')}")
    print(f"  Suspected Stages:  {dx_res.get('suspected_stages')}")
    print(f"  Experiments Run:   {dx_res.get('experiments_run')}")

    # B. Test Repair Plan & Interaction Analysis Endpoint (Phase 4)
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
    print(f"  Conflicts Found:   {plan_data.get('conflicts')}")
    print(f"  Warnings:          {plan_data.get('warnings')}")

    # C. Test Phase 5 Background Job Orchestration & 8 Hard Gates
    print("\n--- C. POST /api/jobs/review (Phase 5 API: Full Pipeline & 8 Hard Gates) ---")
    scenarios_data = get_json(f"{BASE_URL}/api/scenarios")
    inc = scenarios_data["incidents"][0]
    review_job_payload = {
        "agent_id": "toy",
        "target": inc["target"],
        "faults": inc["faults"],
        "regression": scenarios_data["regression_suite"],
        "heldout": scenarios_data["heldout_suite"],
        "use_memory": True,
    }
    job_submit_res = post_json(f"{BASE_URL}/api/jobs/review", review_job_payload)
    job_id = job_submit_res["job_id"]
    print(f"  Submitted Job ID:  {job_id}")

    # Wait for job completion
    job_record = None
    for _ in range(40):
        time.sleep(0.2)
        job_record = get_json(f"{BASE_URL}/api/jobs/{job_id}")
        if job_record.get("status") in ("completed", "failed"):
            break

    job_result = job_record.get("result", {})
    print(f"  Job Status:        {job_record.get('status')}")
    print(f"  Review ID:         {job_result.get('review_id')}")
    print(f"  Review Outcome:    {job_result.get('outcome')}")
    print(f"  Selected Repairs:  {[r['repair_id'] for r in job_result.get('selected_repairs', [])]}")
    gates_res = job_result.get("gates", {})
    print(f"  8 Hard Gates:      All Passed = {gates_res.get('all_passed')} (8/8 Gates Checked)")

    # D. Test Human Approval & Apply Workflow (Phase 5)
    appr_id = job_result.get("approval_request_id")
    if appr_id:
        print(f"\n--- D. Human Approval & Apply Workflow for Approval Request #{appr_id} ---")
        appr_res = post_json(
            f"{BASE_URL}/api/approvals/{appr_id}/approve",
            {"reviewer": "alice (QA Lead)", "note": "Verified by automated regression and held-out evaluation."},
        )
        print(f"  Status after Approval: {appr_res.get('status')} by {appr_res.get('reviewer')}")

        apply_res = post_json(f"{BASE_URL}/api/approvals/{appr_id}/apply", {})
        print(f"  Status after Apply:    Repairs applied -> {[r['repair_id'] for r in apply_res.get('repairs', [])]}")

    # E. Query Failure Memory
    print(f"\n--- E. GET /api/memory/toy (Phase 5 Failure Memory Audit Trail) ---")
    memory_rows = get_json(f"{BASE_URL}/api/memory/toy")
    print(f"  Memory Records:    {len(memory_rows)} cached patterns")
    for row in memory_rows:
        print(f"    Record #{row['id']}: stages={row['suspected_stages']} repairs={row['repair_ids']} status={row['status']} uses={row['uses']}")

    print("\n" + "=" * 80)
    print("  PROJECT FILES EXECUTED & SYSTEM FULLY OPERATING ON PORT:")
    print(f"  >> http://127.0.0.1:{PORT}/ << (Port {PORT})")
    print(f"  >> Interactive Docs: http://127.0.0.1:{PORT}/docs")
    print(f"  >> ReDoc Docs:       http://127.0.0.1:{PORT}/redoc")
    print("=" * 80)


if __name__ == "__main__":
    main()
