"""Phase 2 demo: benchmark every agent clean, then with each known fault.

Usage (from the backend folder):  python scripts/run_phase2_demo.py
Uses a temporary database, so it never touches review.db.
"""
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402
from app.integration import AgentExecutor, build_default_registry  # noqa: E402
from app.services.monitoring_service import MonitoringService  # noqa: E402
from app.storage import Database, TraceStore  # noqa: E402


def main() -> int:
    settings = get_settings()
    executor = AgentExecutor(build_default_registry(settings))
    with tempfile.TemporaryDirectory() as tmp:
        service = MonitoringService(executor, TraceStore(Database(Path(tmp) / "demo.db")), settings.data_dir)
        print(f"{'agent / fault':34} {'success':>8} {'failed':>7} {'p95 ms':>7}  failure categories")
        problems = 0
        for info in executor.registry.list_info():
            runs = [(None, "healthy")] + [(f.fault_id, f.name) for f in service.faults.list_faults(info.agent_id)]
            for fault_id, label in runs:
                summary = service.run_benchmark(info.agent_id, fault_id=fault_id)
                m = summary["metrics"]
                name = f"{info.agent_id}: {fault_id or 'no fault'}"
                print(f"{name:34} {m['task_success_rate']:>8.2f} {m['runs']['failed'] + m['runs']['unexpected_errors']:>7} "
                      f"{m['latency_ms']['p95']:>7.2f}  {m['failures_by_category'] or '-'}")
                healthy_ok = fault_id is None and m["task_success_rate"] == 1.0
                fault_seen = fault_id is not None and m["task_success_rate"] < 1.0
                problems += 0 if (healthy_ok or fault_seen) else 1
    executor.shutdown()
    print("\nHealthy agents pass everything and every injected fault is detected." if not problems
          else f"\n{problems} unexpected result(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
