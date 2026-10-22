# Phase 3 - Root-cause Diagnosis System

A root-cause isolation and failure analysis engine for AI agents that identifies single causes, multi-stage interaction faults, and prunes unexercised/latent faults.

## One-Click Full Execution (Tests + Demo + Port 8001 API)
```bash
./run_all.sh
# or: python3 run_all_diagnosis.py
```

## Running the API Server Standalone
```bash
./run_server.sh
# or: python3 -m phase3.api
# or: uvicorn phase3.api:app --host 0.0.0.0 --port 8001
```
- **Active Port**: `8001`
- **Base URL**: `http://127.0.0.1:8001`
- **Interactive Swagger Docs**: `http://127.0.0.1:8001/docs`
- **Health Check**: `GET http://127.0.0.1:8001/api/health`

## Running Tests & Benchmarks Individually
- **Unit & Contract Tests**: `pytest -q` (14 passed)
- **Engine Benchmark Evaluation**: `python3 -m phase3.demo`

## Modules
- `root_cause_engine`: Isolates root causes using counterfactual state substitution and minimal fix sets.
- `controlled_experiment`: Executes intervention experiments.
- `diagnostic_selector`: Selects candidate stages via divergence analysis.
- `evidence_analyzer`: Analyzes stage-level divergence between failing and clean runs.
- `storage`: SQLite persistent storage for diagnoses (`GET /api/diagnoses`).
- `api`: FastAPI router and standalone web service on port 8001.
