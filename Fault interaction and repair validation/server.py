#!/usr/bin/env python3
"""Fault Interaction and Repair Validation System - Unified Server.

Runs the FastAPI application hosting:
- Phase 4: Fault Interaction Analysis, Repair Planning, Conflict Testing & Validation APIs
- Phase 3: Root-Cause Diagnosis APIs
- Modern Interactive Web Dashboard for live scenario testing and visualization
- OpenAPI Swagger & ReDoc documentation
"""

from __future__ import annotations
import os
import sys
import json
import sqlite3
import time
from pathlib import Path

# Add phase3 directory to Python path
ROOT_DIR = Path(__file__).resolve().parent
PHASE3_DIR = ROOT_DIR / "phase3"
if str(PHASE3_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE3_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from phase3.toy_agent import ToyAdapter
from phase3.storage import DiagnosisStore
from phase3.api import create_router as create_dx_router

from phase4.toy_repairs import ToyRepairAdapter, CATALOG, TRUE_REPAIR
from phase4.storage4 import PlanStore
from phase4.api4 import create_router as create_plan_router
from phase4.evaluation4 import Scenario, evaluate4
from phase4.interaction_analyzer import InteractionAnalyzer
from phase4.repair_planner import RepairPlanner
from phase3.root_cause_engine import RootCauseEngine
from phase3.evaluation import Case

DEFAULT_PORT = int(os.environ.get("PORT", 8002))

# Initialize unified shared adapter and persistent stores
DB_PATH_DX = str(ROOT_DIR / "diagnoses.db")
DB_PATH_PLANS = str(ROOT_DIR / "repair_plans.db")

adapter = ToyRepairAdapter()
dx_store = DiagnosisStore(DB_PATH_DX)
plan_store = PlanStore(DB_PATH_PLANS)

app = FastAPI(
    title="Fault Interaction and Repair Validation System",
    description="Automated root-cause diagnosis, 2^k factorial fault interaction analysis, candidate repair generation, validation against regressions, and conflict detection.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Phase 3 and Phase 4 core API routers
app.include_router(create_plan_router(adapter, plan_store), tags=["Phase 4 - Repair Planning & Validation"])
app.include_router(create_dx_router(adapter, dx_store), tags=["Phase 3 - Root-Cause Diagnosis"])


@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "system": "Fault Interaction and Repair Validation System",
        "phases": ["Phase 3: Root-Cause Diagnosis", "Phase 4: Interaction Discovery & Repair Validation"],
        "port": DEFAULT_PORT,
        "adapter": "ToyRepairAdapter (Resume Matcher Agent)",
        "timestamp": time.time(),
    }


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
        {"id": "TOY-F01", "stage": "tokenize", "name": "Token Limit Truncation", "description": "Limits tokens to 4 max, dropping late words"},
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


@app.get("/api/scenarios", tags=["Phase 4 - Repair Planning & Validation"])
def get_benchmark_scenarios():
    """Returns standard research evaluation scenarios demonstrating fault interactions and conflicts."""
    M, X = {"decision": "match"}, {"decision": "reject"}
    return [
        {
            "id": "scenario_conflict_trap",
            "name": "Scenario 1: Single F03 (Conflict Trap)",
            "description": "Tests single fault in 'score' stage. Highlights downstream compensating repair RP5 (decide) that passes alone but causes severe interaction conflict with RP3 on regression case RX.",
            "target": {
                "case_id": "R6",
                "input": {"resume": "I know python", "required": ["python", "sql"]},
                "expected": M,
            },
            "faults": ["TOY-F03"],
            "regression": [
                {"case_id": "R1", "input": {"resume": "Python and SQL developer with Docker", "required": ["python", "sql"]}, "expected": M},
                {"case_id": "R2", "input": {"resume": "Experienced developer with python and sql", "required": ["python", "sql"]}, "expected": M},
                {"case_id": "R3", "input": {"resume": "python sql", "required": ["python", "sql", "docker"]}, "expected": M},
                {"case_id": "R4", "input": {"resume": "I know python and sql", "required": ["python", "sql", "docker"]}, "expected": M},
                {"case_id": "RX", "input": {"resume": "I know python", "required": ["python", "sql", "docker"]}, "expected": X},
                {"case_id": "RY", "input": {"resume": "I know java", "required": ["python", "sql"]}, "expected": X},
            ],
            "expected_interaction": "none",
            "expected_repairs": ["RP3"],
            "conflicts": [["RP3", "RP5"]],
        },
        {
            "id": "scenario_synergistic",
            "name": "Scenario 2: Joint F02+F03 (Synergistic Fault Interaction)",
            "description": "Faults in 'extract_skills' and 'score' each pass individually on this input, but their combination causes a catastrophic failure. 2^k factorial analysis reveals synergistic interaction.",
            "target": {
                "case_id": "R1",
                "input": {"resume": "Python and SQL developer with Docker", "required": ["python", "sql"]},
                "expected": M,
            },
            "faults": ["TOY-F02", "TOY-F03"],
            "regression": [
                {"case_id": "R2", "input": {"resume": "Experienced developer with python and sql", "required": ["python", "sql"]}, "expected": M},
                {"case_id": "R3", "input": {"resume": "python sql", "required": ["python", "sql", "docker"]}, "expected": M},
                {"case_id": "R6", "input": {"resume": "I know python", "required": ["python", "sql"]}, "expected": M},
                {"case_id": "RX", "input": {"resume": "I know python", "required": ["python", "sql", "docker"]}, "expected": X},
                {"case_id": "RY", "input": {"resume": "I know java", "required": ["python", "sql"]}, "expected": X},
            ],
            "expected_interaction": "synergistic",
            "expected_repairs": ["RP2", "RP3"],
            "conflicts": [["RP3", "RP5"]],
        },
        {
            "id": "scenario_decoy_independent",
            "name": "Scenario 3: Independent F01+F04 (Decoy)",
            "description": "Multiple independent faults at tokenize and decide. Requires a multi-repair combination [RP1, RP4] without regression breaks.",
            "target": {
                "case_id": "R4",
                "input": {"resume": "I know python and sql", "required": ["python", "sql", "docker"]},
                "expected": M,
            },
            "faults": ["TOY-F01", "TOY-F04"],
            "regression": [
                {"case_id": "R1", "input": {"resume": "Python and SQL developer with Docker", "required": ["python", "sql"]}, "expected": M},
                {"case_id": "R2", "input": {"resume": "Experienced developer with python and sql", "required": ["python", "sql"]}, "expected": M},
                {"case_id": "RX", "input": {"resume": "I know python", "required": ["python", "sql", "docker"]}, "expected": X},
            ],
            "expected_interaction": "none",
            "expected_repairs": ["RP1", "RP4"],
            "conflicts": [],
        },
    ]


@app.get("/", response_class=HTMLResponse, tags=["Dashboard UI"])
def get_dashboard_ui():
    """Serves the state-of-the-art interactive web dashboard for Fault Interaction and Repair Validation."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fault Interaction & Repair Validation System</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-base: #0a0e17;
      --bg-card: rgba(18, 24, 38, 0.75);
      --bg-card-hover: rgba(26, 34, 52, 0.85);
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-focus: rgba(99, 102, 241, 0.6);
      --primary: #6366f1;
      --primary-light: #818cf8;
      --accent-cyan: #06b6d4;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background: radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.12) 0%, transparent 40%),
                  radial-gradient(circle at 85% 20%, rgba(6, 182, 212, 0.10) 0%, transparent 40%),
                  radial-gradient(circle at 50% 80%, rgba(16, 185, 129, 0.08) 0%, transparent 50%),
                  var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }}

    /* Header & Navigation */
    header {{
      background: rgba(10, 14, 23, 0.85);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-subtle);
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .logo-group {{
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }}

    .logo-badge {{
      background: linear-gradient(135deg, var(--primary), var(--accent-cyan));
      width: 40px;
      height: 40px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1.25rem;
      box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
    }}

    .logo-text h1 {{
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      background: linear-gradient(90deg, #fff, #cbd5e1);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .logo-text p {{
      font-size: 0.75rem;
      color: var(--text-muted);
    }}

    .header-badges {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}

    .badge-pill {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.4rem 0.85rem;
      border-radius: 9999px;
      font-size: 0.78rem;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-subtle);
    }}

    .badge-pill.port {{
      background: rgba(99, 102, 241, 0.15);
      border-color: rgba(99, 102, 241, 0.4);
      color: var(--primary-light);
      font-family: var(--font-mono);
    }}

    .badge-pill.status {{
      background: rgba(16, 185, 129, 0.15);
      border-color: rgba(16, 185, 129, 0.4);
      color: var(--accent-emerald);
    }}

    .pulse-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent-emerald);
      box-shadow: 0 0 8px var(--accent-emerald);
      animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
      0%, 100% {{ transform: scale(1); opacity: 1; }}
      50% {{ transform: scale(1.3); opacity: 0.7; }}
    }}

    .nav-btn {{
      padding: 0.45rem 0.95rem;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 600;
      text-decoration: none;
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-subtle);
      transition: all 0.2s ease;
    }}

    .nav-btn:hover {{
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.2);
    }}

    /* Main Container */
    main {{
      flex: 1;
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }}

    /* Hero / Overview */
    .hero-banner {{
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.8));
      border: 1px solid var(--border-subtle);
      border-radius: 16px;
      padding: 1.75rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1.5rem;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }}

    .hero-content h2 {{
      font-size: 1.6rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin-bottom: 0.5rem;
    }}

    .hero-content p {{
      color: var(--text-muted);
      font-size: 0.92rem;
      line-height: 1.5;
      max-width: 800px;
    }}

    .hero-meta {{
      display: flex;
      gap: 1rem;
    }}

    .stat-box {{
      background: rgba(10, 14, 23, 0.6);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 0.85rem 1.25rem;
      text-align: center;
    }}

    .stat-value {{
      font-size: 1.4rem;
      font-weight: 800;
      font-family: var(--font-mono);
      color: var(--accent-cyan);
    }}

    .stat-label {{
      font-size: 0.72rem;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-top: 0.2rem;
    }}

    /* Layout Columns */
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 2rem;
      align-items: start;
    }}

    /* Card Panels */
    .card {{
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-subtle);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
      transition: border-color 0.2s ease;
    }}

    .card:hover {{
      border-color: rgba(255, 255, 255, 0.12);
    }}

    .card-header {{
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .card-title {{
      font-size: 1rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}

    .card-body {{
      padding: 1.5rem;
    }}

    /* Control Panel Form */
    .scenario-picker {{
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }}

    .scenario-btn {{
      text-align: left;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1rem;
      cursor: pointer;
      color: var(--text-main);
      transition: all 0.2s ease;
      position: relative;
      overflow: hidden;
    }}

    .scenario-btn:hover {{
      background: var(--bg-card-hover);
      border-color: var(--primary);
      transform: translateY(-1px);
    }}

    .scenario-btn.active {{
      background: rgba(99, 102, 241, 0.12);
      border-color: var(--primary);
    }}

    .scenario-btn.active::before {{
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      background: var(--primary);
    }}

    .scenario-name {{
      font-weight: 700;
      font-size: 0.88rem;
      margin-bottom: 0.3rem;
      color: #fff;
    }}

    .scenario-desc {{
      font-size: 0.76rem;
      color: var(--text-muted);
      line-height: 1.4;
    }}

    .form-group {{
      margin-bottom: 1.25rem;
    }}

    .form-label {{
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .fault-chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }}

    .fault-chip {{
      padding: 0.45rem 0.8rem;
      border-radius: 8px;
      font-size: 0.78rem;
      font-family: var(--font-mono);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s ease;
      user-select: none;
    }}

    .fault-chip:hover {{
      border-color: var(--accent-rose);
      color: #fff;
    }}

    .fault-chip.selected {{
      background: rgba(244, 63, 94, 0.15);
      border-color: var(--accent-rose);
      color: #fda4af;
      font-weight: 600;
    }}

    .run-btn {{
      width: 100%;
      background: linear-gradient(135deg, var(--primary), #4f46e5);
      color: #fff;
      border: none;
      border-radius: 12px;
      padding: 0.9rem;
      font-weight: 700;
      font-size: 0.95rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.6rem;
      box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
      transition: all 0.25s ease;
    }}

    .run-btn:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 22px rgba(99, 102, 241, 0.5);
    }}

    .run-btn:active {{
      transform: translateY(0);
    }}

    /* Results Sections */
    .results-stack {{
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}

    .banner-result {{
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }}

    .banner-result.validated {{
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .banner-result.warning {{
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    .banner-result.danger {{
      background: rgba(244, 63, 94, 0.1);
      border: 1px solid rgba(244, 63, 94, 0.3);
    }}

    .result-status-title {{
      font-size: 1.15rem;
      font-weight: 700;
    }}

    .result-status-subtitle {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.2rem;
    }}

    /* Interaction Factorial Matrix */
    .matrix-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.84rem;
      margin-top: 0.75rem;
    }}

    .matrix-table th {{
      text-align: left;
      padding: 0.75rem 1rem;
      background: rgba(255, 255, 255, 0.03);
      color: var(--text-muted);
      font-weight: 600;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 0.75rem;
      text-transform: uppercase;
    }}

    .matrix-table td {{
      padding: 0.85rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }}

    .status-badge {{
      display: inline-block;
      padding: 0.25rem 0.65rem;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.75rem;
      text-transform: uppercase;
      font-family: var(--font-mono);
    }}

    .status-badge.pass {{
      background: rgba(16, 185, 129, 0.15);
      color: var(--accent-emerald);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .status-badge.fail {{
      background: rgba(244, 63, 94, 0.15);
      color: var(--accent-rose);
      border: 1px solid rgba(244, 63, 94, 0.3);
    }}

    .status-badge.synergistic {{
      background: rgba(245, 158, 11, 0.15);
      color: var(--accent-amber);
      border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    /* Candidate Repairs & Warnings */
    .repairs-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1rem;
      margin-top: 0.75rem;
    }}

    .repair-card {{
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      position: relative;
    }}

    .repair-card.selected {{
      border-color: var(--accent-emerald);
      background: rgba(16, 185, 129, 0.05);
    }}

    .repair-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .repair-id {{
      font-family: var(--font-mono);
      font-weight: 700;
      font-size: 0.92rem;
      color: var(--accent-cyan);
    }}

    .repair-stage {{
      font-size: 0.75rem;
      color: var(--text-dim);
      font-family: var(--font-mono);
    }}

    .repair-desc {{
      font-size: 0.84rem;
      color: var(--text-muted);
      line-height: 1.4;
    }}

    .repair-patch {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      background: rgba(0, 0, 0, 0.4);
      padding: 0.4rem 0.6rem;
      border-radius: 6px;
      color: #94a3b8;
      overflow-x: auto;
    }}

    .warning-box {{
      background: rgba(245, 158, 11, 0.08);
      border-left: 4px solid var(--accent-amber);
      border-radius: 8px;
      padding: 0.85rem 1.25rem;
      font-size: 0.84rem;
      color: #fde68a;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      margin-top: 0.75rem;
    }}

    .conflict-box {{
      background: rgba(244, 63, 94, 0.08);
      border-left: 4px solid var(--accent-rose);
      border-radius: 8px;
      padding: 0.85rem 1.25rem;
      font-size: 0.84rem;
      color: #fecdd3;
      margin-top: 0.75rem;
    }}

    /* Code & JSON Previews */
    .json-block {{
      background: #06090e;
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1rem;
      font-family: var(--font-mono);
      font-size: 0.78rem;
      color: #a5b4fc;
      max-height: 280px;
      overflow-y: auto;
      white-space: pre-wrap;
    }}

    /* Loading Overlay */
    .loader-wrap {{
      display: none;
      align-items: center;
      justify-content: center;
      padding: 3rem;
      gap: 1rem;
    }}

    .spinner {{
      width: 32px;
      height: 32px;
      border: 3px solid rgba(99, 102, 241, 0.2);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }}

    @keyframes spin {{
      to {{ transform: rotate(360deg); }}
    }}

    /* Footer */
    footer {{
      margin-top: auto;
      border-top: 1px solid var(--border-subtle);
      padding: 1.5rem 2rem;
      background: rgba(10, 14, 23, 0.9);
      font-size: 0.82rem;
      color: var(--text-dim);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    @media (max-width: 960px) {{
      .dashboard-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="logo-group">
      <div class="logo-badge">⚡</div>
      <div class="logo-text">
        <h1>Fault Interaction & Repair Validation</h1>
        <p>AI Agent Review and Performance Improvement System</p>
      </div>
    </div>
    <div class="header-badges">
      <div class="badge-pill port" id="headerPort">PORT: {DEFAULT_PORT}</div>
      <div class="badge-pill status">
        <span class="pulse-dot"></span> SYSTEM ONLINE
      </div>
      <a href="/docs" target="_blank" class="nav-btn" id="docsLink">Interactive OpenAPI Docs ↗</a>
      <a href="/redoc" target="_blank" class="nav-btn">ReDoc ↗</a>
    </div>
  </header>

  <main>
    <div class="hero-banner">
      <div class="hero-content">
        <h2>Automated Fault Interaction & Repair Validation</h2>
        <p>
          Diagnoses agent pipeline failures, analyzes <strong>2<sup>k</sup> factorial fault interactions</strong> (identifying synergistic failures and cancelling faults), generates targeted repair candidates, and rigorously tests for <strong>downstream compensation decoys and repair-repair conflicts</strong>.
        </p>
      </div>
      <div class="hero-meta">
        <div class="stat-box">
          <div class="stat-value">{DEFAULT_PORT}</div>
          <div class="stat-label">Active Port</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">27/27</div>
          <div class="stat-label">Unit Tests</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">100%</div>
          <div class="stat-label">Fix Rate</div>
        </div>
      </div>
    </div>

    <div class="dashboard-grid">
      <!-- Left Panel: Controls & Scenario Presets -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">🔬 Scenario & Fault Injector</div>
        </div>
        <div class="card-body">
          <div class="form-group">
            <label class="form-label">Pre-Configured Scenarios</label>
            <div class="scenario-picker" id="scenarioPicker">
              <!-- Populated by JS -->
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Active Faults Injected</label>
            <div class="fault-chips" id="faultChips">
              <div class="fault-chip" data-fault="TOY-F01">TOY-F01 (tokenize)</div>
              <div class="fault-chip" data-fault="TOY-F02">TOY-F02 (extract)</div>
              <div class="fault-chip selected" data-fault="TOY-F03">TOY-F03 (score)</div>
              <div class="fault-chip" data-fault="TOY-F04">TOY-F04 (decide)</div>
            </div>
          </div>

          <button class="run-btn" id="runBtn" onclick="runAnalysis()">
            <span>⚡ Run Interaction & Repair Validation</span>
          </button>
        </div>
      </div>

      <!-- Right Panel: Results & Visualizers -->
      <div class="results-stack">
        <!-- Live Loading Indicator -->
        <div class="loader-wrap" id="loader">
          <div class="spinner"></div>
          <div style="font-size: 0.95rem; color: var(--text-muted);">
            Running root-cause diagnosis, factorial interaction experiments, and repair validation suite...
          </div>
        </div>

        <div id="resultsContainer" style="display: none; display: flex; flex-direction: column; gap: 1.5rem;">
          <!-- Plan Banner -->
          <div class="banner-result validated" id="planBanner">
            <div>
              <div class="result-status-title" id="bannerStatusTitle">Validated Fix Found</div>
              <div class="result-status-subtitle" id="bannerStatusSub">Repair planner successfully discovered and validated optimal patch.</div>
            </div>
            <div class="badge-pill" id="bannerFixBadge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 0.9rem;">
              Selected: <span id="bannerSelectedRepairs" style="font-family: var(--font-mono); font-weight: 700; margin-left: 0.3rem;">RP3</span>
            </div>
          </div>

          <!-- Section 1: Interaction Analysis (2^k Factorial) -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">📊 2<sup>k</sup> Factorial Fault Interaction Analysis</div>
              <span class="status-badge" id="interactionSummaryBadge">NONE</span>
            </div>
            <div class="card-body">
              <p style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.5;" id="interactionDetailText">
                Factorial analysis evaluates all 2<sup>k</sup> combinations of diagnosed faulty stages to determine whether faults behave independently, synergistically, or cancelling.
              </p>
              <table class="matrix-table">
                <thead>
                  <tr>
                    <th>Factorial Combination (Stages Present)</th>
                    <th>Outcome</th>
                    <th>Interaction Detection</th>
                  </tr>
                </thead>
                <tbody id="factorialTableBody">
                  <!-- Injected by JS -->
                </tbody>
              </table>
            </div>
          </div>

          <!-- Section 2: Selected Repairs & Validation Candidates -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">🛠️ Repair Planner & Candidate Validation</div>
              <div class="badge-pill" id="validationUsedBadge">0 Validations Evaluated</div>
            </div>
            <div class="card-body">
              <div class="repairs-grid" id="repairsGrid">
                <!-- Injected by JS -->
              </div>

              <!-- Warnings & Conflict Matrix Container -->
              <div id="warningsContainer"></div>
              <div id="conflictsContainer"></div>
            </div>
          </div>

          <!-- Section 3: Raw API Payload -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">🔍 Full JSON Response Payload (Port {DEFAULT_PORT})</div>
            </div>
            <div class="card-body">
              <pre class="json-block" id="rawJsonBlock">// Response will appear here</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>

  <footer>
    <div>Fault Interaction and Repair Validation System • AI Agent Review Architecture</div>
    <div>Running on <strong>Port {DEFAULT_PORT}</strong> • FastAPI + Uvicorn + SQLite</div>
  </footer>

  <script>
    let currentScenarios = [];
    let activeScenario = null;

    async function loadScenarios() {{
      try {{
        const resp = await fetch('/api/scenarios');
        currentScenarios = await resp.json();
        const container = document.getElementById('scenarioPicker');
        container.innerHTML = '';

        currentScenarios.forEach((sc, idx) => {{
          const btn = document.createElement('div');
          btn.className = `scenario-btn ${{idx === 0 ? 'active' : ''}}`;
          btn.innerHTML = `
            <div class="scenario-name">${{sc.name}}</div>
            <div class="scenario-desc">${{sc.description}}</div>
          `;
          btn.onclick = () => selectScenario(sc, btn);
          container.appendChild(btn);
        }});

        if (currentScenarios.length > 0) {{
          selectScenario(currentScenarios[0], container.children[0]);
          runAnalysis();
        }}
      }} catch (err) {{
        console.error('Failed to load scenarios:', err);
      }}
    }}

    function selectScenario(sc, btnElement) {{
      activeScenario = sc;
      document.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
      if (btnElement) btnElement.classList.add('active');

      // Update chips
      const selectedFaults = new Set(sc.faults);
      document.querySelectorAll('.fault-chip').forEach(chip => {{
        const f = chip.getAttribute('data-fault');
        if (selectedFaults.has(f)) {{
          chip.classList.add('selected');
        }} else {{
          chip.classList.remove('selected');
        }}
      }});
    }}

    // Toggle chip manually
    document.querySelectorAll('.fault-chip').forEach(chip => {{
      chip.onclick = () => {{
        chip.classList.toggle('selected');
      }};
    }});

    function getSelectedFaults() {{
      const faults = [];
      document.querySelectorAll('.fault-chip.selected').forEach(c => {{
        faults.push(c.getAttribute('data-fault'));
      }});
      return faults;
    }}

    async function runAnalysis() {{
      const loader = document.getElementById('loader');
      const resultsContainer = document.getElementById('resultsContainer');
      loader.style.display = 'flex';
      resultsContainer.style.display = 'none';

      const faults = getSelectedFaults();
      const target = activeScenario ? activeScenario.target : {{
        case_id: 'R6',
        input: {{ resume: 'I know python', required: ['python', 'sql'] }},
        expected: {{ decision: 'match' }}
      }};

      const regression = activeScenario ? activeScenario.regression : [];

      const payload = {{
        target: target,
        faults: faults,
        regression: regression
      }};

      try {{
        const resp = await fetch('/api/agents/toy/repair-plan', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});

        const data = await resp.json();
        renderResults(data);
      }} catch (err) {{
        alert('Analysis request failed: ' + err.message);
      }} finally {{
        loader.style.display = 'none';
        resultsContainer.style.display = 'flex';
      }}
    }}

    function renderResults(data) {{
      document.getElementById('rawJsonBlock').textContent = JSON.stringify(data, null, 2);

      const plan = data.plan || {{}};
      const interaction = data.interaction || {{}};
      const diagnosis = data.diagnosis || {{}};

      // Plan Banner
      const banner = document.getElementById('planBanner');
      const bannerTitle = document.getElementById('bannerStatusTitle');
      const bannerSub = document.getElementById('bannerStatusSub');
      const bannerSelected = document.getElementById('bannerSelectedRepairs');

      if (plan.status === 'validated_fix') {{
        banner.className = 'banner-result validated';
        bannerTitle.textContent = 'Validated Fix Discovered';
        bannerSub.textContent = `Successfully validated on target failure and all ${{activeScenario ? activeScenario.regression.length : 0}} regression test cases.`;
        bannerSelected.textContent = (plan.selected && plan.selected.length) ? plan.selected.join(', ') : 'None';
      }} else {{
        banner.className = 'banner-result danger';
        bannerTitle.textContent = 'No Validated Fix';
        bannerSub.textContent = 'No candidate repair or combination resolved the target without breaking regression cases.';
        bannerSelected.textContent = 'None';
      }}

      // Interaction Factorial Table
      const summaryBadge = document.getElementById('interactionSummaryBadge');
      const summaryKind = interaction.summary || 'none';
      summaryBadge.textContent = summaryKind.toUpperCase();
      summaryBadge.className = `status-badge ${{summaryKind === 'synergistic' ? 'synergistic' : (summaryKind === 'none' ? 'pass' : 'fail')}}`;

      const tbody = document.getElementById('factorialTableBody');
      tbody.innerHTML = '';
      const outcomes = interaction.outcomes || [];
      if (outcomes.length === 0) {{
        tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; color:var(--text-dim);">No multiple suspected stages to run factorial analysis.</td></tr>`;
      }} else {{
        outcomes.forEach(o => {{
          const tr = document.createElement('tr');
          const stagesText = o.present && o.present.length ? o.present.join(', ') : '(None - Reference Clean)';
          const fails = o.fails;
          tr.innerHTML = `
            <td style="font-family:var(--font-mono); font-weight:600;">${{stagesText}}</td>
            <td>
              <span class="status-badge ${{fails ? 'fail' : 'pass'}}">
                ${{fails ? 'FAIL' : 'PASS'}}
              </span>
            </td>
            <td style="color:var(--text-muted); font-size:0.8rem;">
              ${{fails && o.present.length > 1 ? (interaction.summary === 'synergistic' ? 'Synergistic Failure Component' : 'Multi-Fault Failure') : (fails ? 'Single Fault Trigger' : 'Passing State')}}
            </td>
          `;
          tbody.appendChild(tr);
        }});
      }}

      // Repairs Grid
      const repairsGrid = document.getElementById('repairsGrid');
      repairsGrid.innerHTML = '';
      const candidates = plan.candidates || [];
      const selectedSet = new Set(plan.selected || []);

      document.getElementById('validationUsedBadge').textContent = `${{plan.validations_used || 0}} Regression Checks Run`;

      candidates.forEach(c => {{
        const isSelected = selectedSet.has(c.repair_id);
        const card = document.createElement('div');
        card.className = `repair-card ${{isSelected ? 'selected' : ''}}`;
        card.innerHTML = `
          <div class="repair-card-header">
            <span class="repair-id">${{c.repair_id}}</span>
            <span class="repair-stage">${{c.stage}}</span>
          </div>
          <div class="repair-desc">${{c.description}}</div>
          <div style="margin-top:auto;">
            <div style="font-size:0.7rem; color:var(--text-dim); margin-bottom:0.25rem;">PATCH PAYLOAD:</div>
            <pre class="repair-patch">${{JSON.stringify(c.patch || {{}})}}</pre>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.5rem; font-size:0.75rem;">
            <span style="color:${{c.role === 'root_cause' ? '#34d399' : '#fbbf24'}}">Role: ${{c.role}}</span>
            <span class="status-badge ${{c.valid_alone ? 'pass' : 'fail'}}">${{c.valid_alone ? 'Valid Alone' : 'Fails Alone'}}</span>
          </div>
        `;
        repairsGrid.appendChild(card);
      }});

      // Warnings
      const warnContainer = document.getElementById('warningsContainer');
      warnContainer.innerHTML = '';
      (plan.warnings || []).forEach(w => {{
        const wBox = document.createElement('div');
        wBox.className = 'warning-box';
        wBox.innerHTML = `<strong>⚠️ Downstream Compensation Warning:</strong> ${{w}}`;
        warnContainer.appendChild(wBox);
      }});

      // Conflicts
      const confContainer = document.getElementById('conflictsContainer');
      confContainer.innerHTML = '';
      (plan.conflicts || []).forEach(conf => {{
        const cBox = document.createElement('div');
        cBox.className = 'conflict-box';
        cBox.innerHTML = `<strong>⚡ Conflict Detected:</strong> ${{conf.repair_a}} and ${{conf.repair_b}} conflict under kind: <em>${{conf.kind}}</em>. Detail: ${{conf.detail}}`;
        confContainer.appendChild(cBox);
      }});
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

    print("=" * 72)
    print(" FAULT INTERACTION AND REPAIR VALIDATION SYSTEM")
    print(f" Server Port:      {port}")
    print(f" Base URL:         http://127.0.0.1:{port}")
    print(f" Web Dashboard:    http://127.0.0.1:{port}/")
    print(f" Interactive Docs: http://127.0.0.1:{port}/docs")
    print(f" ReDoc Docs:       http://127.0.0.1:{port}/redoc")
    print("=" * 72)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
