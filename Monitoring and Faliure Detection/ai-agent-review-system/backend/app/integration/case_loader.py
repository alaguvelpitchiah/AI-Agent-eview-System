"""Load benchmark cases for any agent from data/benchmark_cases/<agent_id>/cases.json.

Case format (the same for every agent type)::

    {"agent_id": "...", "cases": [
        {"case_id": "C001", "input": {...}, "expected": {...}, "tags": [...]}]}

``input`` follows the agent's input schema. ``expected`` is interpreted by the
outcome evaluator (Phase 2); its keys depend on the agent type.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_REQUIRED = {"case_id", "input", "expected"}


def load_cases(data_dir: Path, agent_id: str) -> List[Dict[str, Any]]:
    path = Path(data_dir) / "benchmark_cases" / agent_id / "cases.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fh:
        document = json.load(fh)
    cases = document.get("cases", [])
    seen = set()
    for case in cases:
        missing = _REQUIRED - set(case)
        if missing:
            raise ValueError(f"{path}: case {case.get('case_id', '?')} is missing {sorted(missing)}")
        if case["case_id"] in seen:
            raise ValueError(f"{path}: duplicate case_id {case['case_id']}")
        seen.add(case["case_id"])
    return cases
