"""Run every benchmark case of every registered agent and print a summary table.

Usage (from the backend folder):  python scripts/run_phase1_demo.py
Works for any agent in agents.yaml. Outcome scoring arrives in Phase 2; here a case
"behaves as expected" when it succeeds, or fails with the error type its
expected block names (expect_error).
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402
from app.integration import AgentExecutor, build_default_registry  # noqa: E402
from app.integration.case_loader import load_cases  # noqa: E402


def main() -> int:
    settings = get_settings()
    registry = build_default_registry(settings)
    executor = AgentExecutor(registry)
    problems = 0

    print(f"{'agent':20} {'type':12} {'trace':7} {'cases':>5} {'ok':>4} {'events':>6} {'avg ms':>7}")
    for info in registry.list_info():
        cases = load_cases(settings.data_dir, info.agent_id)
        ok = events = 0
        total_ms = 0.0
        for case in cases:
            result = executor.execute(info.agent_id, case["input"], expected=case["expected"])
            expected_error = case["expected"].get("expect_error")
            behaved = (result.status == "success" and not expected_error) or (
                result.status == "error" and result.error["type"] == expected_error
            )
            ok += behaved
            events += len(result.events)
            total_ms += result.duration_ms
            if not behaved:
                problems += 1
                print(f"  ! {info.agent_id} {case['case_id']}: {result.status} {result.error}")
        avg = total_ms / len(cases) if cases else 0.0
        print(
            f"{info.agent_id:20} {info.agent_type:12} {info.capabilities.trace_level:7} "
            f"{len(cases):>5} {ok:>4} {events:>6} {avg:>7.2f}"
        )

    executor.shutdown()
    print("\nAll cases behaved as expected." if not problems else f"\n{problems} case(s) did not behave as expected.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
