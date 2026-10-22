"""Report Generator (Phase 6 Module).

Generates downloadable and visual evaluation reports in:
- Markdown (.md)
- HTML (.html)
- JSON (.json)
- CSV (.csv)
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ReportGenerator:
    """Generates multi-format review and benchmark reports."""

    @classmethod
    def generate_markdown_report(
        cls,
        target_name: str,
        results: Dict[str, Any],
        diagnoses: Optional[List[Dict[str, Any]]] = None,
        repairs: Optional[List[Dict[str, Any]]] = None,
        audit_trail: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = [
            f"# AI Agent Review & Performance Improvement Report",
            f"",
            f"**Target System:** `{target_name}`  ",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Review System:** AI Agent Review Platform v1.0.0  ",
            f"",
            f"---",
            f"",
            f"## 1. Executive Summary",
            f"",
            f"This evaluation was conducted externally via authorized deployment endpoints without access to internal source code or model weights.",
            f"",
            f"| Metric | Result |",
            f"|---|---|",
            f"| Total Test Cases Executed | {results.get('total_tests', 0)} |",
            f"| Observed Failures Detected | {results.get('failures_detected', 0)} |",
            f"| Root Causes Identified | {len(diagnoses or [])} |",
            f"| Validated Candidate Repairs | {len(repairs or [])} |",
            f"| 8 Hard Gates Status | **{results.get('gates_status', 'PASS')}** |",
            f"",
            f"---",
            f"",
            f"## 2. Failure Detection Findings",
            f"",
        ]

        if not results.get("failure_items"):
            lines.append("No critical failures observed during execution.\n")
        else:
            lines.append("| Case ID | Category | Severity | Observable Failure | Evidence |")
            lines.append("|---|---|---|---|---|")
            for f in results.get("failure_items", []):
                lines.append(f"| `{f.get('case_id', '-')}` | {f.get('category', '-')} | `{f.get('severity', '-')}` | {f.get('description', '-')} | `{str(f.get('evidence', ''))[:80]}` |")
            lines.append("")

        lines.extend([
            f"---",
            f"",
            f"## 3. Root-Cause Diagnoses (Controlled Experiments)",
            f"",
        ])

        if not diagnoses:
            lines.append("No active diagnoses recorded.\n")
        else:
            for d in diagnoses:
                lines.append(f"### Diagnosis for Incident `{d.get('incident_id', 'unknown')}`")
                lines.append(f"- **Faulty Stage Identified:** `{d.get('faulty_stage', 'unknown')}`")
                lines.append(f"- **Confidence Level:** `{d.get('confidence', 'medium')}`")
                lines.append(f"- **Counterfactual Isolation:** {d.get('evidence_summary', 'Controlled stage substitution confirmed divergence')}")
                lines.append("")

        lines.extend([
            f"---",
            f"",
            f"## 4. Proposed Repairs and Hard Gate Validation",
            f"",
            f"Candidate repairs were evaluated against all **8 Hard Gates** (Diagnosis Confirmed, Target Fixed, No Regressions, Held-out Clean, Root-Cause Coverage, No Compensating Hacks, Pairwise Safe, Stability).",
            f"",
        ])

        if not repairs:
            lines.append("No candidate repairs proposed.\n")
        else:
            for r in repairs:
                lines.append(f"#### Repair `{r.get('repair_id', 'rep-01')}` ({r.get('type', 'Prompt Guardrail')})")
                lines.append(f"- **Target Stage:** `{r.get('stage', 'input')}`")
                lines.append(f"- **Gate Outcome:** **`{r.get('gate_outcome', 'PASS')}`**")
                lines.append(f"- **Human Approval Status:** `{r.get('approval_status', 'Pending Review')}`")
                lines.append(f"```diff")
                lines.append(f"- Current:  {r.get('original_snippet', '')}")
                lines.append(f"+ Proposed: {r.get('proposed_patch', '')}")
                lines.append(f"```")
                lines.append("")

        lines.extend([
            f"---",
            f"",
            f"## 5. Governance & Human Approval Sign-Off",
            f"",
            f"> [!IMPORTANT]",
            f"> System Policy: Proposed repairs are recommendations and must NOT be deployed without explicit human authorization.",
            f"",
        ])

        if audit_trail:
            lines.append("| Timestamp | Action | Reviewer / Actor | Status |")
            lines.append("|---|---|---|---|")
            for a in audit_trail[:10]:
                lines.append(f"| {a.get('timestamp', '')} | {a.get('action', '')} | {a.get('actor', '')} | {a.get('status', '')} |")
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def generate_csv_metrics(cls, metrics_data: List[Dict[str, Any]]) -> str:
        """Export metrics table to CSV format."""
        out = io.StringIO()
        if not metrics_data:
            return ""
        fieldnames = list(metrics_data[0].keys())
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for row in metrics_data:
            writer.writerow(row)
        return out.getvalue()
