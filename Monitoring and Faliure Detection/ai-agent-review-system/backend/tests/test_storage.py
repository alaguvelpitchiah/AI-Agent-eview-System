import sqlite3

import pytest

from app.reviewer.failure_detector import FailureDetector
from app.reviewer.outcome_evaluator import OutcomeEvaluator
from app.storage import Database, RecordNotFoundError, TraceStore
from helpers import event, make_record

evaluator, detector = OutcomeEvaluator(), FailureDetector()


def save(store, **kw):
    record = make_record(**kw)
    evaluation = evaluator.evaluate(record)
    failure = detector.detect(record, evaluation)
    store.save_monitored(record, evaluation, failure)
    return record, evaluation, failure


FAIL = {"checks": [{"path": "n", "op": "equals", "value": 99}]}
PASS = {"checks": [{"path": "n", "op": "equals", "value": 3}]}


def test_round_trip_of_run_evaluation_and_failure(store):
    record, _, failure = save(store, execution_id="r1", expected=FAIL, events=[event("s", output={"k": 1})], metadata={"case_id": "c1"})
    run = store.get_run("r1")
    assert run["input"] == {"q": 1} and run["output"]["n"] == 3 and run["events"][0]["name"] == "s"
    assert run["metadata"] == {"case_id": "c1"} and run["expected"] == FAIL
    assert run["evaluation"]["verdict"] == "fail" and run["evaluation"]["checks"][0]["passed"] is False
    assert run["failure"]["failure_id"] == failure.failure_id
    assert store.get_failure(failure.failure_id)["category"] == "incorrect_output"


def test_passing_run_has_no_failure(store):
    save(store, execution_id="ok1", expected=PASS)
    assert store.get_run("ok1")["failure"] is None


def test_missing_records_raise(store):
    with pytest.raises(RecordNotFoundError):
        store.get_run("nope")
    with pytest.raises(RecordNotFoundError):
        store.get_failure("nope")


def test_duplicate_execution_ids_are_rejected_atomically(store):
    save(store, execution_id="dup", expected=PASS)
    with pytest.raises(sqlite3.IntegrityError):
        save(store, execution_id="dup", expected=FAIL)
    assert store.count_runs() == 1 and store.list_failures() == []  # the failed save left nothing behind


def test_listing_filters_and_paging(store):
    for i in range(5):
        save(store, execution_id=f"p{i}", agent_id="a1", expected=PASS if i % 2 == 0 else FAIL, batch_id="b1" if i < 3 else None)
    save(store, execution_id="other", agent_id="a2", expected=PASS)
    assert len(store.list_runs()) == 6
    assert len(store.list_runs(agent_id="a1")) == 5
    assert {r["execution_id"] for r in store.list_runs(batch_id="b1")} == {"p0", "p1", "p2"}
    assert {r["execution_id"] for r in store.list_runs(verdict="fail")} == {"p1", "p3"}
    assert [r["execution_id"] for r in store.list_runs(limit=2)] == ["other", "p4"]  # newest first
    assert [r["execution_id"] for r in store.list_runs(limit=2, offset=2)] == ["p3", "p2"]
    assert store.list_runs()[0]["failure_category"] is None
    assert {f["agent_id"] for f in store.list_failures(category="incorrect_output")} == {"a1"}
    assert store.list_failures(severity="critical") == []


def test_sql_injection_attempts_are_inert(store):
    save(store, execution_id="s1", expected=PASS)
    assert store.list_runs(agent_id="a1' OR '1'='1") == []
    assert store.count_runs() == 1


def test_metric_rows_carry_usage_and_counts(store):
    save(store, execution_id="m1", expected=PASS, usage={"latency_ms": 5.0, "tokens": 12},
         events=[event("t", kind="tool_call")], agent_version="v7")
    row = store.metric_rows(agent_version="v7")[0]
    assert row["usage"]["tokens"] == 12 and row["tool_call_count"] == 1 and row["verdict"] == "pass"
    assert store.metric_rows(agent_version="other") == []


def test_data_survives_reopening_the_database(tmp_path):
    path = tmp_path / "persist.db"
    save(TraceStore(Database(path)), execution_id="keep", expected=FAIL)
    again = TraceStore(Database(path))
    assert again.get_run("keep")["failure"] is not None


def test_database_uses_wal_and_foreign_keys(tmp_path):
    db = Database(tmp_path / "w.db")
    with db.connection() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):  # evaluation without a run is refused
            conn.execute("INSERT INTO evaluations VALUES ('ghost','pass',1,'m','[]','t')")
