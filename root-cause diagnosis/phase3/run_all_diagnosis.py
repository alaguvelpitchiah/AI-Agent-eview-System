"""Comprehensive runner for Phase 3 Root-Cause Diagnosis System.

Executes:
1. Automated Test Suite (pytest)
2. Evaluation Demo across all failure cases (demo.py)
3. Ensures Diagnosis API server is running on port 8001 (auto-starts if needed)
4. Live HTTP API calls to the service running on port 8001
5. Querying stored diagnoses from SQLite
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8001"
DIR = Path(__file__).resolve().parent

CASES_TO_TEST = [
    {
        "name": "Case 1: Single Root Cause (Tokenize)",
        "input": {"resume": "Experienced developer with python and sql", "required": ["python", "sql"]},
        "expected": {"decision": "match"},
        "faults": ["TOY-F01"],
        "run_ref": "run-f01-single",
    },
    {
        "name": "Case 2: Joint Root Cause (Extract + Score Interaction)",
        "input": {"resume": "Python and SQL developer with Docker", "required": ["python", "sql"]},
        "expected": {"decision": "match"},
        "faults": ["TOY-F02", "TOY-F03"],
        "run_ref": "run-joint-extract-score",
    },
    {
        "name": "Case 3: Masked Faults (Tokenize + Decide)",
        "input": {"resume": "I know python and sql", "required": ["python", "sql", "docker"]},
        "expected": {"decision": "match"},
        "faults": ["TOY-F01", "TOY-F04"],
        "run_ref": "run-masked-tokenize-decide",
    },
    {
        "name": "Case 4: Latent Fault (Decide fault unexercised)",
        "input": {"resume": "Experienced developer with python and sql", "required": ["python", "sql"]},
        "expected": {"decision": "match"},
        "faults": ["TOY-F01", "TOY-F04"],
        "run_ref": "run-latent-fault",
    },
]


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


def ensure_server_running(url: str):
    if is_server_ready(url):
        print(f"-> Diagnosis API server is already running on {url}")
        return None

    print(f"-> Starting Diagnosis API server on port 8001 in background...")
    venv_python = DIR / ".venv" / "bin" / "python"
    py_exec = str(venv_python) if venv_python.exists() else sys.executable
    proc = subprocess.Popen(
        [py_exec, "-m", "phase3.api"],
        cwd=str(DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(25):
        if is_server_ready(url):
            print(f"-> Server started successfully on {url}")
            return proc
        time.sleep(0.4)
    print("WARNING: Server did not respond within timeout, proceeding with checks...")
    return proc


def main():
    print("=" * 70)
    print("PHASE 3 ROOT-CAUSE DIAGNOSIS: FULL SYSTEM EXECUTION")
    print("=" * 70)

    # 1. Run Unit Tests
    print("\n[STEP 1] Running all test files with pytest...")
    venv_pytest = DIR / ".venv" / "bin" / "pytest"
    if venv_pytest.exists():
        test_cmd = [str(venv_pytest), "-q"]
    else:
        test_cmd = [sys.executable, "-m", "pytest", "-q"]

    test_proc = subprocess.run(test_cmd, cwd=str(DIR), capture_output=True, text=True)
    print(test_proc.stdout.strip())
    if test_proc.returncode != 0:
        print("Tests failed:", test_proc.stderr)
        return

    # 2. Run Engine Benchmark / Evaluation
    print("\n[STEP 2] Running Root-Cause Engine Benchmark (phase3.demo)...")
    venv_py = DIR / ".venv" / "bin" / "python"
    py_exec = str(venv_py) if venv_py.exists() else sys.executable
    demo_proc = subprocess.run([py_exec, "-m", "phase3.demo"], cwd=str(DIR), capture_output=True, text=True)
    print(demo_proc.stdout.strip())

    # 3. Ensure API Server is Running
    print(f"\n[STEP 3] Verifying / Launching API Server on Port 8001 ({BASE_URL})...")
    ensure_server_running(BASE_URL)
    health = get_json(f"{BASE_URL}/api/health")
    print(f"-> Active Port: 8001")
    print(f"-> Health Check: {health}")
    print(f"-> OpenAPI Docs: {BASE_URL}/docs")

    # 4. Live API Execution via Port 8001
    print(f"\n[STEP 4] Executing Diagnostic Cases via Port 8001...")
    created_ids = []
    for c in CASES_TO_TEST:
        print(f"\n--- {c['name']} ---")
        payload = {
            "input": c["input"],
            "expected": c["expected"],
            "faults": c["faults"],
            "run_ref": c["run_ref"],
        }
        res = post_json(f"{BASE_URL}/api/agents/toy/diagnose", payload)
        diag_id = res.get("diagnosis_id")
        created_ids.append(diag_id)
        print(f" Diagnosis ID:      {diag_id}")
        print(f" Verdict:           {res.get('verdict')}")
        print(f" Confidence:        {res.get('confidence')}")
        print(f" Suspected Stages:  {res.get('suspected_stages')}")
        print(f" Minimal Fix Sets:  {res.get('minimal_fix_sets')}")
        print(f" Pattern:           {res.get('interaction_pattern')}")
        print(f" Experiments Run:   {len(res.get('experiments', []))}")

    # 5. Fetch stored diagnoses
    print(f"\n[STEP 5] Querying Stored Diagnoses from Port 8001 (GET /api/diagnoses)...")
    all_diags = get_json(f"{BASE_URL}/api/diagnoses")
    print(f"Total Diagnoses stored in SQLite: {len(all_diags)}")
    if created_ids:
        sample = get_json(f"{BASE_URL}/api/diagnoses/{created_ids[-1]}")
        print(f"Sample Diagnosis detail fetched for ID {created_ids[-1]}: verdict='{sample.get('verdict')}', suspected={sample.get('suspected_stages')}")

    print("\n" + "=" * 70)
    print("ALL PROJECT FILES & ENDPOINTS SUCCESSFULLY EXECUTED ON PORT 8001")
    print("=" * 70)


if __name__ == "__main__":
    main()
