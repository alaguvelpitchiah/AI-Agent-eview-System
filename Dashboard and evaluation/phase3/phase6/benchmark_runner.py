"""Benchmark Runner (Phase 6 Module).

Executes repeatable benchmark evaluation suites:
- Runs all 39 benchmark scenarios (single faults, held-out, conflict traps, double synergistic).
- Executes proposed pipeline and baseline reviewer in parallel/sequence.
- Records step latencies, stage attributions, and gate decisions.
- Saves benchmark results to JSON and triggers report generation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from .runner import run_all
from .benchmark import build
from .report import build_report


class BenchmarkRunner:
    """Orchestrates benchmark runs and persists results."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.environ.get("PHASE6_OUT") or str(Path(__file__).parent / "phase6_results")
        os.makedirs(self.output_dir, exist_ok=True)

    def run_full_benchmark(self, seed: int = 7) -> Dict[str, Any]:
        """Execute benchmark suite and generate JSON + Markdown + HTML artifacts."""
        adapter, pool, reg_suite, held_suite, hidden_suite, scenarios = build(seed)
        results = run_all(adapter, pool, reg_suite, held_suite, scenarios)

        # Build comprehensive report dictionary
        report_data = build_report(results)
        
        # Save to output files
        json_path = os.path.join(self.output_dir, "results.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        md_path = os.path.join(self.output_dir, "results.md")
        if "markdown" in report_data:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(report_data["markdown"])

        html_path = os.path.join(self.output_dir, "report.html")
        if "html" in report_data:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(report_data["html"])

        return report_data
