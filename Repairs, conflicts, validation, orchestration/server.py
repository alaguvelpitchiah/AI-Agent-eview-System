#!/usr/bin/env python3
"""Repairs, Conflicts, Validation, Orchestration System - Unified Server.

Runs the FastAPI application hosting:
- Phase 5: End-to-End Orchestrator, 8 Hard Gates, Human Approvals, Failure Memory & Job Queue
- Phase 4: Fault Interaction Analysis (2^k factorial), Repair Planning, Conflict Testing & Validation
- Phase 3: Root-Cause Diagnosis APIs (Controlled Counterfactual Experiments)
- Modern Interactive Web Dashboard (Dark Mode / Glassmorphism)
- OpenAPI Swagger (/docs) & ReDoc (/redoc) Documentation
"""

from __future__ import annotations
import os
import sys
import json
import sqlite3
import time
from pathlib import Path
from contextlib import asynccontextmanager

# Add phase3 directory to Python path
ROOT_DIR = Path(__file__).resolve().parent
PHASE3_DIR = ROOT_DIR / "phase3"
if str(PHASE3_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE3_DIR))

# Ensure local virtual environment packages are discoverable when run with any python interpreter
VENV_LIB = ROOT_DIR / ".venv" / "lib"
if VENV_LIB.exists():
    for site_pkg in VENV_LIB.glob("python*/site-packages"):
        if str(site_pkg) not in sys.path:
            sys.path.insert(0, str(site_pkg))

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from phase3.toy_agent import ToyAdapter
from phase3.storage import DiagnosisStore
from phase3.api import create_router as create_dx_router
from phase3.root_cause_engine import RootCauseEngine
from phase3.evaluation import Case

from phase4.toy_repairs import ToyRepairAdapter, CATALOG, TRUE_REPAIR
from phase4.storage4 import PlanStore
from phase4.api4 import create_router as create_plan_router
from phase4.interaction_analyzer import InteractionAnalyzer
from phase4.repair_planner import RepairPlanner

from phase5.db import Database
from phase5.jobs import JobRunner
from phase5.orchestrator import ReviewOrchestrator, case_from_dict
from phase5.api5 import create_router as create_phase5_router

DEFAULT_PORT = int(os.environ.get("PORT", 8003))

# Persistent database paths
DB_PATH_ORCH = str(ROOT_DIR / "orchestration.db")
DB_PATH_DX = str(ROOT_DIR / "diagnoses.db")
DB_PATH_PLANS = str(ROOT_DIR / "repair_plans.db")

db = Database(DB_PATH_ORCH)
adapter = ToyRepairAdapter()
dx_store = DiagnosisStore(DB_PATH_DX)
plan_store = PlanStore(DB_PATH_PLANS)

orch = ReviewOrchestrator(adapter, db)
runner = JobRunner(db)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    runner.start(workers=2)
    yield
    runner.stop()


app = FastAPI(
    title="AI Agent Review and Performance Improvement System",
    description="End-to-end root-cause diagnosis, 2^k factorial fault interaction discovery, candidate repair generation, regression validation, conflict testing, 8 hard gates, human approvals, and failure memory.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def handle_head_requests(request: Request, call_next):
    """Automatically handle HEAD requests across all routes."""
    if request.method == "HEAD":
        request.scope["method"] = "GET"
        response = await call_next(request)
        return Response(
            content=b"",
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
    return await call_next(request)


@app.get("/favicon.ico", include_in_schema=False)
@app.head("/favicon.ico", include_in_schema=False)
def favicon():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">⚡</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")


# Mount Phase 5, Phase 4, and Phase 3 API Routers
app.include_router(create_phase5_router(orch, runner), tags=["Phase 5 - Orchestration & Gates"])
app.include_router(create_plan_router(adapter, plan_store), tags=["Phase 4 - Repair Planning & Validation"])
app.include_router(create_dx_router(adapter, dx_store), tags=["Phase 3 - Root-Cause Diagnosis"])


@app.get("/api/health", tags=["System"])
def health_check():
    jobs = runner.list()
    approvals = orch.approvals.list()
    return {
        "status": "ok",
        "system": "Repairs, Conflicts, Validation & Orchestration System",
        "phases": [
            "Phase 3: Root-Cause Diagnosis (Controlled Experiments)",
            "Phase 4: Fault Interaction Discovery & Repair Planning",
            "Phase 5: Orchestration, 8 Hard Gates, Approvals & Failure Memory",
        ],
        "port": DEFAULT_PORT,
        "adapter": "ToyRepairAdapter (Resume Matcher Agent)",
        "jobs_count": len(jobs),
        "approvals_count": len(approvals),
        "timestamp": time.time(),
    }


@app.head("/api/health", include_in_schema=False)
def health_check_head():
    return Response(content=b"", media_type="application/json")


@app.get("/api/catalog", tags=["System"])
def get_catalog():
    """Return available stages, fault injections, and candidate repair patches."""
    catalog_serializable = {}
    for stage, repairs in CATALOG.items():
        catalog_serializable[stage] = [
            {
                "repair_id": r.repair_id,
                "stage": r.stage,
                "description": r.description,
                "patch": r.patch,
                "is_true_repair_for": [f for f, r_id in TRUE_REPAIR.items() if r_id == r.repair_id],
            }
            for r in repairs
        ]

    faults = [
        {"id": "TOY-F01", "stage": "tokenize", "name": "Token Limit Truncation", "description": "Limits tokens to 4 max, dropping later words"},
        {"id": "TOY-F02", "stage": "extract_skills", "name": "Drop Skills Bug", "description": "Filters out 'sql' skill from detected list"},
        {"id": "TOY-F03", "stage": "score", "name": "Denominator Inflater", "description": "Inflates denominator in ratio calculation by +1"},
        {"id": "TOY-F04", "stage": "decide", "name": "Threshold Shift", "description": "Shifts acceptance threshold from 0.5 to 0.7"},
    ]

    return {
        "stages": ["tokenize", "extract_skills", "score", "decide"],
        "faults": faults,
        "repair_catalog": catalog_serializable,
        "ground_truth_map": TRUE_REPAIR,
    }


@app.get("/api/scenarios", tags=["System"])
def get_scenarios():
    """Returns preset incidents and test suites for demonstration."""
    M, X = {"decision": "match"}, {"decision": "reject"}

    def C(cid, resume, req, exp):
        return {"case_id": cid, "input": {"resume": resume, "required": req}, "expected": exp}

    reg_suite = [
        C("R1", "Python and SQL developer with Docker", ["python", "sql"], M),
        C("R2", "Experienced developer with python and sql", ["python", "sql"], M),
        C("R3", "python sql", ["python", "sql", "docker"], M),
        C("R4", "I know python and sql", ["python", "sql", "docker"], M),
        C("R6", "I know python", ["python", "sql"], M),
        C("RX", "I know python", ["python", "sql", "docker"], X),
        C("RY", "I know java", ["python", "sql"], X),
    ]

    heldout_suite = [
        C("RW", "python sql", ["python", "sql", "java", "aws", "docker"], X),
        C("RV", "python", ["python", "sql", "docker", "java"], X),
    ]

    incidents = [
        {
            "id": "inc_f03_conflict_trap",
            "name": "Incident 1: Score Denominator Fault (TOY-F03) - Conflict Trap",
            "target": C("R6", "I know python", ["python", "sql"], M),
            "faults": ["TOY-F03"],
            "description": "Triggered by score inflation fault. Downstream threshold shift (RP5) compensates on target but conflicts with RP3 and causes regression on RX. Safe fix is RP3.",
        },
        {
            "id": "inc_synergistic_joint",
            "name": "Incident 2: Synergistic Multi-Fault (TOY-F02 + TOY-F03)",
            "target": C("R1", "Python and SQL developer with Docker", ["python", "sql"], M),
            "faults": ["TOY-F02", "TOY-F03"],
            "description": "Neither fault alone causes failure; together they fail. Requires factorial interaction analysis and joint repair set {RP2, RP3}.",
        },
        {
            "id": "inc_f04_threshold",
            "name": "Incident 3: Decide Threshold Shift (TOY-F04)",
            "target": C("R3", "python sql", ["python", "sql", "docker"], M),
            "faults": ["TOY-F04"],
            "description": "Strict threshold shifts decision. Tests memory reuse rejection when different cause occurs, finding RP4.",
        },
        {
            "id": "inc_f03_recurrence",
            "name": "Incident 4: Recurrent Score Fault (R7, TOY-F03)",
            "target": C("R7", "I know sql", ["python", "sql"], M),
            "faults": ["TOY-F03"],
            "description": "Recurrence of Incident 1 symptom. Triggers validated Failure Memory lookup (similarity >= 0.85) and skips re-diagnosis safely.",
        },
    ]

    return {
        "incidents": incidents,
        "regression_suite": reg_suite,
        "heldout_suite": heldout_suite,
    }


# Interactive Web Dashboard
@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
def web_dashboard():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Agent Review & Performance Improvement Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #0b0f19;
      --bg-card: rgba(18, 24, 38, 0.85);
      --bg-card-hover: rgba(26, 34, 54, 0.95);
      --border-color: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(99, 102, 241, 0.4);
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --primary-glow: rgba(99, 102, 241, 0.3);
      --success: #10b981;
      --success-glow: rgba(16, 185, 129, 0.25);
      --warning: #f59e0b;
      --danger: #ef4444;
      --purple: #8b5cf6;
      --cyan: #06b6d4;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background: radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.12), transparent 40%),
                  radial-gradient(circle at 85% 85%, rgba(139, 92, 246, 0.1), transparent 40%),
                  var(--bg-dark);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    header {{
      background: rgba(11, 15, 25, 0.8);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .logo-container {{
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }}

    .logo-icon {{
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, var(--primary), var(--purple));
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 16px var(--primary-glow);
      font-size: 1.3rem;
    }}

    .logo-text h1 {{
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      background: linear-gradient(to right, #fff, #cbd5e1);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .logo-text p {{
      font-size: 0.75rem;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .header-badges {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      border: 1px solid transparent;
    }}

    .badge-port {{
      background: rgba(99, 102, 241, 0.15);
      border-color: rgba(99, 102, 241, 0.35);
      color: #a5b4fc;
      font-family: var(--font-mono);
    }}

    .badge-status {{
      background: rgba(16, 185, 129, 0.15);
      border-color: rgba(16, 185, 129, 0.35);
      color: #6ee7b7;
    }}

    .badge-status::before {{
      content: '';
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }}

    .header-links a {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.85rem;
      font-weight: 500;
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      transition: all 0.2s ease;
    }}

    .header-links a:hover {{
      color: #fff;
      background: rgba(255, 255, 255, 0.05);
    }}

    main {{
      flex: 1;
      max-width: 1500px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}

    /* Tabs */
    .tab-bar {{
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 0.5rem;
    }}

    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 0.65rem 1.25rem;
      font-family: var(--font-sans);
      font-size: 0.88rem;
      font-weight: 600;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s ease;
    }}

    .tab-btn:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.04);
    }}

    .tab-btn.active {{
      color: #fff;
      background: var(--primary);
      box-shadow: 0 0 16px var(--primary-glow);
    }}

    .tab-content {{
      display: none;
      flex-direction: column;
      gap: 1.5rem;
    }}

    .tab-content.active {{
      display: flex;
    }}

    /* Card Panels */
    .panel {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.5rem;
      backdrop-filter: blur(12px);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }}

    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border-color);
    }}

    .panel-header h2 {{
      font-size: 1.05rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}

    .panel-header h2 span {{
      color: var(--primary);
    }}

    /* Controls Grid */
    .controls-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 1.5rem;
    }}

    @media (max-width: 992px) {{
      .controls-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .select-group label {{
      display: block;
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 600;
      color: var(--text-dim);
      margin-bottom: 0.4rem;
      letter-spacing: 0.05em;
    }}

    .custom-select {{
      width: 100%;
      background: #151b2c;
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.75rem 1rem;
      border-radius: 8px;
      font-family: var(--font-sans);
      font-size: 0.9rem;
      outline: none;
      cursor: pointer;
      transition: border-color 0.2s;
    }}

    .custom-select:focus {{
      border-color: var(--primary);
    }}

    .scenario-desc {{
      margin-top: 0.75rem;
      padding: 0.85rem;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.03);
      border-left: 3px solid var(--primary);
      font-size: 0.85rem;
      color: var(--text-muted);
      line-height: 1.45;
    }}

    /* Fault Chips */
    .fault-chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.5rem;
    }}

    .fault-chip {{
      padding: 0.45rem 0.85rem;
      border-radius: 6px;
      font-size: 0.78rem;
      font-family: var(--font-mono);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s;
      user-select: none;
    }}

    .fault-chip.selected {{
      background: rgba(239, 68, 68, 0.15);
      border-color: rgba(239, 68, 68, 0.5);
      color: #fca5a5;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      background: var(--primary);
      color: #fff;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-family: var(--font-sans);
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      box-shadow: 0 4px 12px var(--primary-glow);
    }}

    .btn:hover {{
      background: var(--primary-hover);
      transform: translateY(-1px);
    }}

    .btn-success {{
      background: var(--success);
      box-shadow: 0 4px 12px var(--success-glow);
    }}

    .btn-success:hover {{
      background: #059669;
    }}

    .btn-danger {{
      background: var(--danger);
      box-shadow: 0 4px 12px rgba(239, 68, 68, 0.25);
    }}

    .btn-danger:hover {{
      background: #dc2626;
    }}

    /* Pipeline tracker */
    .pipeline-steps {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      overflow-x: auto;
      padding: 0.75rem 0;
      margin-bottom: 1.5rem;
    }}

    .step-node {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.35rem;
      min-width: 110px;
      padding: 0.75rem;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-color);
      transition: all 0.3s;
    }}

    .step-node.completed {{
      border-color: rgba(16, 185, 129, 0.4);
      background: rgba(16, 185, 129, 0.06);
    }}

    .step-node.active {{
      border-color: var(--primary);
      background: rgba(99, 102, 241, 0.1);
      box-shadow: 0 0 12px var(--primary-glow);
    }}

    .step-node.skipped {{
      opacity: 0.45;
    }}

    .step-icon {{
      font-size: 1.1rem;
    }}

    .step-label {{
      font-size: 0.75rem;
      font-weight: 600;
      text-align: center;
    }}

    .step-status {{
      font-size: 0.68rem;
      font-family: var(--font-mono);
      color: var(--text-dim);
    }}

    /* Hard Gates Grid */
    .gates-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }}

    .gate-card {{
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }}

    .gate-card.passed {{
      border-left: 4px solid var(--success);
    }}

    .gate-card.failed {{
      border-left: 4px solid var(--danger);
    }}

    .gate-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .gate-name {{
      font-size: 0.85rem;
      font-weight: 600;
    }}

    .gate-badge {{
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      text-transform: uppercase;
      font-family: var(--font-mono);
    }}

    .gate-badge.pass {{
      background: rgba(16, 185, 129, 0.15);
      color: #6ee7b7;
    }}

    .gate-badge.fail {{
      background: rgba(239, 68, 68, 0.15);
      color: #fca5a5;
    }}

    .gate-reason {{
      font-size: 0.75rem;
      color: var(--text-muted);
      line-height: 1.35;
    }}

    /* Banner Outcome */
    .outcome-banner {{
      padding: 1.25rem 1.5rem;
      border-radius: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }}

    .outcome-banner.approval_pending {{
      background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05));
      border: 1px solid rgba(245, 158, 11, 0.4);
    }}

    .outcome-banner.applied {{
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05));
      border: 1px solid rgba(16, 185, 129, 0.4);
    }}

    .outcome-banner.rejected {{
      background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05));
      border: 1px solid rgba(239, 68, 68, 0.4);
    }}

    .outcome-banner.no_validated_fix {{
      background: linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(239, 68, 68, 0.03));
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    .outcome-text h3 {{
      font-size: 1.1rem;
      font-weight: 700;
    }}

    .outcome-text p {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.2rem;
    }}

    .repairs-pill-list {{
      display: flex;
      gap: 0.5rem;
      margin-top: 0.5rem;
    }}

    .repair-pill {{
      padding: 0.25rem 0.6rem;
      background: rgba(99, 102, 241, 0.2);
      border: 1px solid rgba(99, 102, 241, 0.4);
      color: #c7d2fe;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 600;
    }}

    /* Tables */
    .table-container {{
      overflow-x: auto;
      border-radius: 8px;
      border: 1px solid var(--border-color);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      text-align: left;
    }}

    th {{
      background: rgba(255, 255, 255, 0.03);
      color: var(--text-dim);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border-color);
    }}

    td {{
      padding: 0.75rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-muted);
    }}

    tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    /* JSON Box */
    pre.code-box {{
      background: #0d121f;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: #e2e8f0;
      overflow-x: auto;
      max-height: 380px;
    }}

    /* Loading overlay */
    .loader-overlay {{
      display: none;
      align-items: center;
      justify-content: center;
      gap: 1rem;
      padding: 2rem;
      background: rgba(11, 15, 25, 0.7);
      border-radius: 8px;
    }}

    .spinner {{
      width: 24px;
      height: 24px;
      border: 3px solid rgba(99, 102, 241, 0.2);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }}

    @keyframes spin {{
      to {{ transform: rotate(360deg); }}
    }}

    footer {{
      margin-top: auto;
      border-top: 1px solid var(--border-color);
      padding: 1.25rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.8rem;
      color: var(--text-dim);
    }}
  </style>
</head>
<body>

  <header>
    <div class="logo-container">
      <div class="logo-icon">⚡</div>
      <div class="logo-text">
        <h1>AI Agent Review & Performance Improvement System</h1>
        <p>Phases 3, 4 & 5 Unified Orchestration Platform</p>
      </div>
    </div>
    <div class="header-badges">
      <span class="badge badge-port" id="portBadge">PORT: {DEFAULT_PORT}</span>
      <span class="badge badge-status" id="systemStatusBadge">SYSTEM ONLINE</span>
      <div class="header-links">
        <a href="/docs" target="_blank">Swagger Docs ↗</a>
        <a href="/redoc" target="_blank">ReDoc ↗</a>
      </div>
    </div>
  </header>

  <main>
    <!-- Tab navigation -->
    <div class="tab-bar">
      <button class="tab-btn active" onclick="switchTab('orchestratorTab', this)">
        <span>🎯</span> Phase 5: Orchestration & 8 Hard Gates
      </button>
      <button class="tab-btn" onclick="switchTab('interactionTab', this)">
        <span>🔬</span> Phase 4: Interactions & Conflict Analysis
      </button>
      <button class="tab-btn" onclick="switchTab('diagnosisTab', this)">
        <span>🧪</span> Phase 3: Root-Cause Diagnosis
      </button>
      <button class="tab-btn" onclick="switchTab('memoryTab', this)">
        <span>🧠</span> Failure Memory & Re-validation
      </button>
      <button class="tab-btn" onclick="switchTab('apiTab', this)">
        <span>📡</span> Active APIs & Port Specs
      </button>
    </div>

    <!-- TAB 1: PHASE 5 ORCHESTRATOR & GATES -->
    <div id="orchestratorTab" class="tab-content active">
      <div class="panel">
        <div class="panel-header">
          <h2><span>01</span> Orchestrated Review Runner</h2>
          <span style="font-size:0.8rem; color:var(--text-dim);">Execute full lifecycle: Monitor → Memory → Diagnose → Interaction → Plan → 8 Hard Gates → Approval</span>
        </div>

        <div class="controls-grid">
          <div>
            <div class="select-group">
              <label>Select Test Incident Scenario</label>
              <select id="scenarioSelect" class="custom-select" onchange="onScenarioChange()">
                <!-- Loaded dynamically -->
              </select>
            </div>
            <div id="scenarioDescription" class="scenario-desc">Loading incident description...</div>

            <div style="margin-top: 1rem;">
              <label style="font-size:0.75rem; text-transform:uppercase; font-weight:600; color:var(--text-dim);">Active Fault Injections</label>
              <div class="fault-chips" id="faultChipsContainer"></div>
            </div>
          </div>

          <div style="display:flex; flex-direction:column; justify-content:space-between; gap:1rem;">
            <div style="background:rgba(255,255,255,0.02); padding:1rem; border-radius:8px; border:1px solid var(--border-color);">
              <div style="font-size:0.75rem; color:var(--text-dim); text-transform:uppercase; font-weight:600; margin-bottom:0.5rem;">Pipeline Settings</div>
              <label style="display:flex; align-items:center; gap:0.5rem; font-size:0.85rem; cursor:pointer;">
                <input type="checkbox" id="useMemoryCheckbox" checked>
                Enable Failure Memory Lookup (>= 0.85)
              </label>
            </div>
            <button class="btn" style="height:50px; font-size:1rem;" onclick="runOrchestratedReview()">
              🚀 Run End-to-End Orchestrated Review
            </button>
          </div>
        </div>
      </div>

      <!-- Execution Results -->
      <div id="reviewResultsPanel" class="panel" style="display:none;">
        <div class="panel-header">
          <h2><span>02</span> Orchestration Execution Results</h2>
          <span id="reviewIdBadge" class="badge badge-port">ID: -</span>
        </div>

        <div id="reviewOutcomeBanner" class="outcome-banner">
          <div class="outcome-text">
            <h3 id="outcomeTitle">Evaluating...</h3>
            <p id="outcomeSubtitle"></p>
            <div class="repairs-pill-list" id="selectedRepairsPillList"></div>
          </div>
          <div id="approvalActionGroup" style="display:none; gap:0.5rem;">
            <button class="btn btn-success" onclick="approveCurrentRequest()">✓ Human Approve</button>
            <button class="btn btn-danger" onclick="rejectCurrentRequest()">✕ Reject</button>
          </div>
        </div>

        <!-- Pipeline Steps Tracker -->
        <div style="font-size:0.75rem; text-transform:uppercase; font-weight:600; color:var(--text-dim); margin-bottom:0.4rem;">Orchestration Lifecycle Trace</div>
        <div class="pipeline-steps" id="pipelineStepsTracker"></div>

        <!-- 8 Hard Gates Section -->
        <div style="margin-top:1.5rem;">
          <div class="panel-header" style="margin-bottom:0.75rem;">
            <h2><span>03</span> The 8 Mandatory Hard Gates Evaluation</h2>
            <span style="font-size:0.75rem; color:var(--text-muted);">Zero-tolerance policy: ALL 8 gates must pass for human review approval</span>
          </div>
          <div class="gates-grid" id="hardGatesGrid"></div>
        </div>
      </div>
    </div>

    <!-- TAB 2: PHASE 4 INTERACTIONS & CONFLICTS -->
    <div id="interactionTab" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <h2><span>01</span> Factorial Interaction Matrix & Conflict Discovery</h2>
          <button class="btn" onclick="runPhase4Plan()">⚡ Analyze Interactions & Plan Repairs</button>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.5rem;">
          <div>
            <h3 style="font-size:0.9rem; margin-bottom:0.75rem; color:#a5b4fc;">2^k Factorial Multi-Fault Outcomes</h3>
            <div class="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Stage Subset</th>
                    <th>Outcome</th>
                    <th>Interpretation</th>
                  </tr>
                </thead>
                <tbody id="factorialTableBody">
                  <tr><td colspan="3" style="text-align:center; padding:1.5rem;">Run scenario to view 2^k factorial outcomes</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3 style="font-size:0.9rem; margin-bottom:0.75rem; color:#fca5a5;">Detected Hazards & Conflicts</h3>
            <div id="conflictsList" style="display:flex; flex-direction:column; gap:0.5rem;">
              <div style="padding:1rem; border-radius:8px; background:rgba(255,255,255,0.02); color:var(--text-dim); font-size:0.85rem;">
                No conflicts evaluated yet.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: PHASE 3 ROOT CAUSE DIAGNOSIS -->
    <div id="diagnosisTab" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <h2><span>01</span> Controlled Counterfactual Experiments</h2>
          <button class="btn" onclick="runPhase3Diagnosis()">🧪 Execute Counterfactual Diagnosis</button>
        </div>
        <div id="diagnosisDetails" style="font-size:0.9rem; color:var(--text-muted);">
          Select an incident and click above to run stage-level counterfactual experiments.
        </div>
      </div>
    </div>

    <!-- TAB 4: FAILURE MEMORY -->
    <div id="memoryTab" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <h2><span>01</span> Failure Memory Store & Jaccard Symptom Cache</h2>
          <button class="btn" onclick="refreshMemoryRecords()">🔄 Refresh Memory Records</button>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Record ID</th>
                <th>Agent Version</th>
                <th>Suspected Stages</th>
                <th>Repairs</th>
                <th>Status</th>
                <th>Uses</th>
                <th>Successes</th>
              </tr>
            </thead>
            <tbody id="memoryRecordsTable">
              <tr><td colspan="7" style="text-align:center; padding:1.5rem;">No memory records loaded</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 5: API & PORT SPECS -->
    <div id="apiTab" class="tab-content">
      <div class="panel">
        <div class="panel-header">
          <h2><span>01</span> Project Port & System Topology</h2>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:1rem;">
          <div style="background:rgba(255,255,255,0.02); padding:1rem; border-radius:8px; border:1px solid var(--border-color);">
            <div style="color:var(--text-dim); font-size:0.75rem; text-transform:uppercase;">Active HTTP Port</div>
            <div style="font-size:1.8rem; font-weight:700; color:var(--primary); font-family:var(--font-mono); margin-top:0.25rem;">{DEFAULT_PORT}</div>
            <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">Configurable via <code>PORT</code> environment variable</div>
          </div>
          <div style="background:rgba(255,255,255,0.02); padding:1rem; border-radius:8px; border:1px solid var(--border-color);">
            <div style="color:var(--text-dim); font-size:0.75rem; text-transform:uppercase;">Base URL</div>
            <div style="font-size:1.1rem; font-weight:600; color:#fff; font-family:var(--font-mono); margin-top:0.5rem;">http://127.0.0.1:{DEFAULT_PORT}</div>
            <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">Local loopback interface & 0.0.0.0 binding</div>
          </div>
          <div style="background:rgba(255,255,255,0.02); padding:1rem; border-radius:8px; border:1px solid var(--border-color);">
            <div style="color:var(--text-dim); font-size:0.75rem; text-transform:uppercase;">Swagger UI Docs</div>
            <div style="font-size:1.1rem; font-weight:600; color:var(--cyan); font-family:var(--font-mono); margin-top:0.5rem;">/docs</div>
            <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">Interactive OpenAPI specifications</div>
          </div>
        </div>

        <h3 style="font-size:0.95rem; margin-top:1.5rem; margin-bottom:0.75rem;">Live Registered API Endpoints</h3>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Method</th>
                <th>Endpoint Path</th>
                <th>Phase</th>
                <th>Purpose</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="badge" style="background:#1e3a8a; color:#93c5fd;">POST</span></td>
                <td><code>/api/jobs/review</code></td>
                <td>Phase 5</td>
                <td>Submit review job (monitoring, diagnosis, interaction, planning, gates)</td>
              </tr>
              <tr>
                <td><span class="badge" style="background:#064e3b; color:#6ee7b7;">GET</span></td>
                <td><code>/api/jobs/{{id}}</code></td>
                <td>Phase 5</td>
                <td>Fetch background review job progress and result</td>
              </tr>
              <tr>
                <td><span class="badge" style="background:#1e3a8a; color:#93c5fd;">POST</span></td>
                <td><code>/api/approvals/{{id}}/approve</code></td>
                <td>Phase 5</td>
                <td>Human reviewer approval with named sign-off</td>
              </tr>
              <tr>
                <td><span class="badge" style="background:#1e3a8a; color:#93c5fd;">POST</span></td>
                <td><code>/api/approvals/{{id}}/apply</code></td>
                <td>Phase 5</td>
                <td>Apply approved repair patch set to target agent</td>
              </tr>
              <tr>
                <td><span class="badge" style="background:#1e3a8a; color:#93c5fd;">POST</span></td>
                <td><code>/api/agents/{{agent_id}}/repair-plan</code></td>
                <td>Phase 4</td>
                <td>Factorial interaction analysis, repair generation & conflict check</td>
              </tr>
              <tr>
                <td><span class="badge" style="background:#1e3a8a; color:#93c5fd;">POST</span></td>
                <td><code>/api/agents/{{agent_id}}/diagnose</code></td>
                <td>Phase 3</td>
                <td>Controlled counterfactual experiments for root cause diagnosis</td>
              </tr>
              <tr>
                <td><span class="badge" style="background:#064e3b; color:#6ee7b7;">GET</span></td>
                <td><code>/api/memory/{{agent_id}}</code></td>
                <td>Phase 5</td>
                <td>Query failure memory cache & reuse statistics</td>
              </tr>
              <tr>
                <td><span class="badge" style="background:#064e3b; color:#6ee7b7;">GET</span></td>
                <td><code>/api/health</code></td>
                <td>System</td>
                <td>Health check and port verification status</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </main>

  <footer>
    <div>AI Agent Review & Performance Improvement System &copy; 2026</div>
    <div style="font-family:var(--font-mono);">PORT {DEFAULT_PORT} &bull; FASTAPI &bull; UVICORN</div>
  </footer>

  <script>
    let SCENARIOS = [];
    let activeScenario = null;
    let activeApprovalId = null;

    function switchTab(tabId, btn) {{
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      btn.classList.add('active');
    }}

    async function loadScenarios() {{
      try {{
        const res = await fetch('/api/scenarios');
        const data = await res.json();
        SCENARIOS = data.incidents || [];
        window.REGRESSION_SUITE = data.regression_suite || [];
        window.HELDOUT_SUITE = data.heldout_suite || [];

        const select = document.getElementById('scenarioSelect');
        select.innerHTML = '';
        SCENARIOS.forEach((s, idx) => {{
          const opt = document.createElement('option');
          opt.value = idx;
          opt.textContent = s.name;
          select.appendChild(opt);
        }});

        if (SCENARIOS.length > 0) {{
          onScenarioChange();
        }}
        refreshMemoryRecords();
      }} catch (err) {{
        console.error('Failed to load scenarios:', err);
      }}
    }}

    function onScenarioChange() {{
      const select = document.getElementById('scenarioSelect');
      const idx = parseInt(select.value, 10);
      activeScenario = SCENARIOS[idx];

      document.getElementById('scenarioDescription').textContent = activeScenario.description;

      const container = document.getElementById('faultChipsContainer');
      container.innerHTML = '';
      (activeScenario.faults || []).forEach(f => {{
        const chip = document.createElement('span');
        chip.className = 'fault-chip selected';
        chip.textContent = f;
        chip.setAttribute('data-fault', f);
        container.appendChild(chip);
      }});
    }}

    async function runOrchestratedReview() {{
      if (!activeScenario) return;

      const resultsPanel = document.getElementById('reviewResultsPanel');
      resultsPanel.style.display = 'block';

      const outcomeBanner = document.getElementById('reviewOutcomeBanner');
      outcomeBanner.className = 'outcome-banner';
      document.getElementById('outcomeTitle').textContent = 'Submitting & Executing Review...';
      document.getElementById('outcomeSubtitle').textContent = 'Job running background worker threads across pipeline stages';
      document.getElementById('selectedRepairsPillList').innerHTML = '';
      document.getElementById('approvalActionGroup').style.display = 'none';

      const payload = {{
        agent_id: 'toy',
        target: activeScenario.target,
        faults: activeScenario.faults,
        regression: window.REGRESSION_SUITE,
        heldout: window.HELDOUT_SUITE,
        use_memory: document.getElementById('useMemoryCheckbox').checked
      }};

      try {{
        const submitResp = await fetch('/api/jobs/review', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});
        const submitData = await submitResp.json();
        const jobId = submitData.job_id;

        // Poll job until finished
        let attempts = 0;
        while (attempts < 30) {{
          await new Promise(r => setTimeout(r, 200));
          const jobResp = await fetch(`/api/jobs/${{jobId}}`);
          const jobData = await jobResp.json();
          if (jobData.status === 'completed') {{
            renderReviewResult(jobData.result);
            break;
          }} else if (jobData.status === 'failed') {{
            alert('Job failed: ' + jobData.error);
            break;
          }}
          attempts++;
        }}
      }} catch (err) {{
        alert('Review execution error: ' + err.message);
      }}
    }}

    function renderReviewResult(res) {{
      document.getElementById('reviewIdBadge').textContent = 'REV: ' + res.review_id;

      const outcomeBanner = document.getElementById('reviewOutcomeBanner');
      const title = document.getElementById('outcomeTitle');
      const sub = document.getElementById('outcomeSubtitle');
      const pillsContainer = document.getElementById('selectedRepairsPillList');
      const actionGroup = document.getElementById('approvalActionGroup');

      outcomeBanner.className = 'outcome-banner ' + res.outcome;
      pillsContainer.innerHTML = '';

      if (res.outcome === 'approval_pending') {{
        title.textContent = 'Approval Pending (8 Gates Passed)';
        sub.textContent = 'Validated candidate repairs satisfy all 8 hard gates. Awaiting named human sign-off.';
        actionGroup.style.display = 'flex';
        activeApprovalId = res.approval_request_id;
      }} else if (res.outcome === 'no_validated_fix') {{
        title.textContent = 'No Validated Fix';
        sub.textContent = 'One or more mandatory hard gates failed or no candidate repairs passed regression tests.';
        actionGroup.style.display = 'none';
      }} else if (res.outcome === 'no_failure') {{
        title.textContent = 'No Failure Detected';
        sub.textContent = 'Target input runs cleanly without error.';
        actionGroup.style.display = 'none';
      }} else {{
        title.textContent = 'Outcome: ' + res.outcome;
        sub.textContent = '';
        actionGroup.style.display = 'none';
      }}

      (res.selected_repairs || []).forEach(r => {{
        const p = document.createElement('span');
        p.className = 'repair-pill';
        p.textContent = `${{r.repair_id}} (${{r.stage}})`;
        pillsContainer.appendChild(p);
      }});

      // Steps tracker
      const tracker = document.getElementById('pipelineStepsTracker');
      tracker.innerHTML = '';
      (res.steps || []).forEach(s => {{
        const node = document.createElement('div');
        node.className = `step-node ${{s.status === 'ok' ? 'completed' : 'active'}}`;
        node.innerHTML = `
          <div class="step-icon">${{s.status === 'ok' ? '✓' : '⚠️'}}</div>
          <div class="step-label">${{s.step.replace('_', ' ').toUpperCase()}}</div>
          <div class="step-status">${{s.ms}}ms</div>
        `;
        tracker.appendChild(node);
      }});

      // Hard Gates Grid
      const gatesGrid = document.getElementById('hardGatesGrid');
      gatesGrid.innerHTML = '';
      const gates = res.gates ? res.gates.gates : [];
      gates.forEach(g => {{
        const card = document.createElement('div');
        card.className = `gate-card ${{g.passed ? 'passed' : 'failed'}}`;
        card.innerHTML = `
          <div class="gate-header">
            <span class="gate-name">${{g.gate}}</span>
            <span class="gate-badge ${{g.passed ? 'pass' : 'fail'}}">${{g.passed ? 'PASSED' : 'BLOCKED'}}</span>
          </div>
          <div class="gate-reason">${{g.reason}}</div>
        `;
        gatesGrid.appendChild(card);
      }});

      refreshMemoryRecords();
    }}

    async function approveCurrentRequest() {{
      if (!activeApprovalId) return;
      try {{
        const res = await fetch(`/api/approvals/${{activeApprovalId}}/approve`, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ reviewer: 'alice (QA Lead)', note: 'Validated against regression and heldout suites.' }})
        }});
        const data = await res.json();

        // Apply immediately
        const applyRes = await fetch(`/api/approvals/${{activeApprovalId}}/apply`, {{
          method: 'POST'
        }});
        const applyData = await applyRes.json();

        const outcomeBanner = document.getElementById('reviewOutcomeBanner');
        outcomeBanner.className = 'outcome-banner applied';
        document.getElementById('outcomeTitle').textContent = 'Approved & Applied';
        document.getElementById('outcomeSubtitle').textContent = `Applied by alice. Repair patches: ${{applyData.repairs.map(r => r.repair_id).join(', ')}}`;
        document.getElementById('approvalActionGroup').style.display = 'none';
        refreshMemoryRecords();
      }} catch (err) {{
        alert('Approval failed: ' + err.message);
      }}
    }}

    async function rejectCurrentRequest() {{
      if (!activeApprovalId) return;
      try {{
        await fetch(`/api/approvals/${{activeApprovalId}}/reject`, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ reviewer: 'alice (QA Lead)', note: 'Manual rejection by operator.' }})
        }});
        const outcomeBanner = document.getElementById('reviewOutcomeBanner');
        outcomeBanner.className = 'outcome-banner rejected';
        document.getElementById('outcomeTitle').textContent = 'Rejected by Reviewer';
        document.getElementById('outcomeSubtitle').textContent = 'Decision recorded and saved to failure memory audit trail.';
        document.getElementById('approvalActionGroup').style.display = 'none';
        refreshMemoryRecords();
      }} catch (err) {{
        alert('Rejection failed: ' + err.message);
      }}
    }}

    async function runPhase4Plan() {{
      if (!activeScenario) return;
      try {{
        const res = await fetch('/api/agents/toy/repair-plan', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            target: activeScenario.target,
            faults: activeScenario.faults,
            regression: window.REGRESSION_SUITE
          }})
        }});
        const data = await res.json();

        // Render factorial
        const tbody = document.getElementById('factorialTableBody');
        tbody.innerHTML = '';
        const outcomes = data.interaction ? data.interaction.outcomes : [];
        if (outcomes.length === 0) {{
          tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:1.5rem;">Single fault detected; no multi-factor factorial needed.</td></tr>`;
        }} else {{
          outcomes.forEach(o => {{
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td style="font-family:var(--font-mono);">${{o.present.length ? o.present.join(', ') : '(Clean Reference)'}}</td>
              <td><span class="gate-badge ${{o.fails ? 'fail' : 'pass'}}">${{o.fails ? 'FAIL' : 'PASS'}}</span></td>
              <td>${{o.fails ? 'Failure Condition' : 'Passing Subset'}}</td>
            `;
            tbody.appendChild(tr);
          }});
        }}

        // Render conflicts & warnings
        const confDiv = document.getElementById('conflictsList');
        confDiv.innerHTML = '';
        const conflicts = (data.plan && data.plan.conflicts) ? data.plan.conflicts : [];
        const warnings = (data.plan && data.plan.warnings) ? data.plan.warnings : [];

        if (conflicts.length === 0 && warnings.length === 0) {{
          confDiv.innerHTML = `<div style="padding:1rem; border-radius:8px; background:rgba(16,185,129,0.1); color:#6ee7b7; font-size:0.85rem;">No repair conflicts detected for this scenario.</div>`;
        }} else {{
          conflicts.forEach(c => {{
            const el = document.createElement('div');
            el.style = 'padding:0.85rem; border-radius:8px; background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.4); font-size:0.85rem;';
            el.innerHTML = `<strong>⚡ Conflict:</strong> ${{c.repair_a}} & ${{c.repair_b}} conflict (${{c.kind}}). ${{c.detail}}`;
            confDiv.appendChild(el);
          }});
          warnings.forEach(w => {{
            const el = document.createElement('div');
            el.style = 'padding:0.85rem; border-radius:8px; background:rgba(245,158,11,0.15); border:1px solid rgba(245,158,11,0.4); font-size:0.85rem;';
            el.innerHTML = `<strong>⚠️ Warning:</strong> ${{w}}`;
            confDiv.appendChild(el);
          }});
        }}
      }} catch (err) {{
        alert('Phase 4 planning error: ' + err.message);
      }}
    }}

    async function runPhase3Diagnosis() {{
      if (!activeScenario) return;
      try {{
        const res = await fetch('/api/agents/toy/diagnose', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            input: activeScenario.target.input,
            expected: activeScenario.target.expected,
            faults: activeScenario.faults,
            run_ref: 'phase3-interactive-demo'
          }})
        }});
        const data = await res.json();
        const details = document.getElementById('diagnosisDetails');
        details.innerHTML = `
          <div style="background:rgba(255,255,255,0.02); padding:1.25rem; border-radius:8px; border:1px solid var(--border-color);">
            <div style="display:flex; justify-content:space-between; margin-bottom:1rem;">
              <div><strong>Verdict:</strong> <span style="color:var(--primary);">${{data.verdict}}</span></div>
              <div><strong>Confidence:</strong> ${{data.confidence}}</div>
              <div><strong>Experiments Run:</strong> ${{data.experiments_run}}</div>
            </div>
            <div style="margin-bottom:0.75rem;"><strong>Suspected Faulty Stages:</strong> <span style="font-family:var(--font-mono); color:#6ee7b7;">${{data.suspected_stages.join(', ') || 'None'}}</span></div>
            <div><strong>Evidence & Invariant Checks:</strong></div>
            <ul style="margin-top:0.5rem; margin-left:1.5rem; font-size:0.85rem; color:var(--text-muted); line-height:1.5;">
              ${{(data.evidence || []).map(e => `<li>${{e}}</li>`).join('')}}
            </ul>
          </div>
        `;
      }} catch (err) {{
        alert('Phase 3 diagnosis error: ' + err.message);
      }}
    }}

    async function refreshMemoryRecords() {{
      try {{
        const res = await fetch('/api/memory/toy');
        const rows = await res.json();
        const tbody = document.getElementById('memoryRecordsTable');
        tbody.innerHTML = '';
        if (rows.length === 0) {{
          tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem;">No memory records recorded yet. Run a review and approve it to record memory.</td></tr>`;
          return;
        }}
        rows.forEach(r => {{
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td style="font-family:var(--font-mono); font-weight:600;">#${{r.id}}</td>
            <td>${{r.agent_version}}</td>
            <td><span style="font-family:var(--font-mono); color:#93c5fd;">${{r.suspected_stages.join(', ')}}</span></td>
            <td><span class="repair-pill">${{r.repair_ids.join(', ')}}</span></td>
            <td><span class="gate-badge ${{r.status === 'approved' ? 'pass' : 'fail'}}">${{r.status}}</span></td>
            <td>${{r.uses}}</td>
            <td>${{r.successes}}</td>
          `;
          tbody.appendChild(tr);
        }});
      }} catch (err) {{
        console.error('Failed to fetch memory records:', err);
      }}
    }}

    window.addEventListener('DOMContentLoaded', loadScenarios);
  </script>
</body>
</html>
"""


def _free_port(port: int):
    """Frees up the port if an orphaned process is holding it."""
    import subprocess
    try:
        out = subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True, stderr=subprocess.DEVNULL)
        for pid_str in out.strip().split():
            try:
                pid = int(pid_str)
                if pid != os.getpid():
                    os.kill(pid, 9)
                    time.sleep(0.1)
            except (ValueError, OSError):
                pass
    except Exception:
        pass


def main():
    import uvicorn
    host = "0.0.0.0"
    port = DEFAULT_PORT

    _free_port(port)

    print("=" * 76)
    print(" REPAIRS, CONFLICTS, VALIDATION & ORCHESTRATION SYSTEM")
    print(f" Server Port:      {port}")
    print(f" Base URL:         http://127.0.0.1:{port}")
    print(f" Web Dashboard:    http://127.0.0.1:{port}/")
    print(f" Interactive Docs: http://127.0.0.1:{port}/docs")
    print(f" ReDoc Docs:       http://127.0.0.1:{port}/redoc")
    print("=" * 76)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
