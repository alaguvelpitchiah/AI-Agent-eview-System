"""Compare an agent's actual result with its expected outcome, for any agent type.

The ``expected`` block of a case is agent-independent::

    {
      "checks": [
        {"path": "result", "op": "equals", "value": 72},
        {"path": "answer", "op": "not_contains", "value": "password", "category": "safety"},
        {"path": "match_score", "op": "gte", "value": 90, "severity": "minor"}
      ],
      "expect_error": "ToolError",     # run must fail with this error type (true = any)
      "max_latency_ms": 2000,           # optional performance expectation
      "custom": "my_evaluator"          # optional registered evaluator for complex rules
    }

A check reads ``path`` (dotted, list indices allowed) from ``source``:
``output`` (default), ``usage``, ``events`` or ``error``.
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..integration.errors import TaskValidationError
from .trace_collector import TraceRecord

CATEGORIES = ("correctness", "completeness", "safety")
SEVERITIES = ("minor", "major", "critical")
SOURCES = ("output", "usage", "events", "error")
_MISSING = object()


class ExpectationSpecError(TaskValidationError):
    """The expected-outcome block is malformed (a problem with the case, not the agent)."""


@dataclass
class CheckResult:
    name: str
    path: str
    source: str
    op: str
    expected: Any
    actual: Any
    passed: bool
    message: str
    category: str = "correctness"
    severity: str = "major"
    missing: bool = False  # the path did not exist in the result

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OutcomeEvaluation:
    execution_id: str
    verdict: str  # pass | fail | error | no_expectation
    score: Optional[float]
    checks: List[CheckResult] = field(default_factory=list)
    message: str = ""
    evaluated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["checks"] = [c.to_dict() for c in self.checks]
        return data


# ---- path resolution -----------------------------------------------------------------

def resolve_path(data: Any, path: str) -> Any:
    """Return the value at a dotted path, or _MISSING when it does not exist."""
    node = data
    if path in ("", None):
        return node
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return _MISSING
    return node


# ---- operators --------------------------------------------------------------------------

def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _contains(actual: Any, value: Any, case_sensitive: bool) -> bool:
    if isinstance(actual, str) and isinstance(value, str):
        return value in actual if case_sensitive else value.lower() in actual.lower()
    if isinstance(actual, (list, tuple)):
        return value in actual
    if isinstance(actual, dict):
        return value in actual
    return False


_TYPE_NAMES = {"str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict}


def _type_is(actual: Any, name: str) -> bool:
    if name == "null":
        return actual is None
    if name == "number":
        return _num(actual)
    if name in ("int", "float") and isinstance(actual, bool):
        return False
    return isinstance(actual, _TYPE_NAMES[name])


def _equals(actual: Any, value: Any) -> bool:
    # bool is a subclass of int in Python; do not let True equal 1.
    return actual == value and isinstance(actual, bool) == isinstance(value, bool)


def _approx(actual: Any, check: Dict[str, Any]) -> bool:
    if not _num(actual):
        return False
    abs_tol = check.get("tolerance", 1e-6)
    return math.isclose(actual, check["value"], rel_tol=check.get("rel_tolerance", 0.0), abs_tol=abs_tol)


# op name -> (needs_value, function(actual, check) -> bool)
_OPS: Dict[str, Tuple[bool, Callable[[Any, Dict[str, Any]], bool]]] = {
    "equals": (True, lambda a, c: _equals(a, c["value"])),
    "not_equals": (True, lambda a, c: a != c["value"]),
    "approx": (True, _approx),
    "gt": (True, lambda a, c: _num(a) and a > c["value"]),
    "gte": (True, lambda a, c: _num(a) and a >= c["value"]),
    "lt": (True, lambda a, c: _num(a) and a < c["value"]),
    "lte": (True, lambda a, c: _num(a) and a <= c["value"]),
    "between": (True, lambda a, c: _num(a) and c["value"][0] <= a <= c["value"][1]),
    "contains": (True, lambda a, c: _contains(a, c["value"], c.get("case_sensitive", False))),
    "not_contains": (True, lambda a, c: not _contains(a, c["value"], c.get("case_sensitive", False))),
    "regex": (True, lambda a, c: isinstance(a, str) and re.search(c["value"], a) is not None),
    "in": (True, lambda a, c: a in c["value"]),
    "not_in": (True, lambda a, c: a not in c["value"]),
    "type_is": (True, lambda a, c: _type_is(a, c["value"])),
    "min_length": (True, lambda a, c: isinstance(a, (str, list, dict)) and len(a) >= c["value"]),
    "max_length": (True, lambda a, c: isinstance(a, (str, list, dict)) and len(a) <= c["value"]),
    "is_null": (False, lambda a, c: a is None),
    "not_null": (False, lambda a, c: a is not None),
    "exists": (False, lambda a, c: True),   # a missing path is reported before the operator runs
    "absent": (False, lambda a, c: False),  # passes only when the path is missing
}
# These operators pass when the path is missing; every other operator fails and flags it.
_MISSING_OK = {"not_equals", "not_contains", "not_in", "absent"}


# ---- specification validation ---------------------------------------------------------------

def validate_expected(expected: Optional[Dict[str, Any]], customs: Optional[Dict[str, Any]] = None) -> None:
    """Raise ExpectationSpecError describing every problem in an expected block."""
    if expected is None:
        return
    errors: List[str] = []
    if not isinstance(expected, dict):
        raise ExpectationSpecError(["'expected' must be an object"])
    known = {"checks", "expect_error", "max_latency_ms", "custom"}
    errors += [f"Unknown expected key '{k}'" for k in expected if k not in known]

    ee = expected.get("expect_error")
    if ee is not None and not (ee is True or isinstance(ee, str)):
        errors.append("'expect_error' must be an error type name or true")
    ml = expected.get("max_latency_ms")
    if ml is not None and not (_num(ml) and ml > 0):
        errors.append("'max_latency_ms' must be a positive number")
    custom = expected.get("custom")
    if custom is not None and (not isinstance(custom, str) or (customs is not None and custom not in customs)):
        errors.append(f"Unknown custom evaluator '{custom}'")

    checks = expected.get("checks", [])
    if not isinstance(checks, list):
        errors.append("'checks' must be a list")
        checks = []
    for i, check in enumerate(checks, start=1):
        label = f"check {i}"
        if not isinstance(check, dict):
            errors.append(f"{label} must be an object")
            continue
        op = check.get("op")
        if op not in _OPS:
            errors.append(f"{label}: unknown op '{op}'")
            continue
        needs_value = _OPS[op][0]
        if needs_value and "value" not in check:
            errors.append(f"{label}: op '{op}' needs a 'value'")
        if "path" not in check or not isinstance(check["path"], str):
            errors.append(f"{label}: 'path' is required")
        if check.get("source", "output") not in SOURCES:
            errors.append(f"{label}: source must be one of {list(SOURCES)}")
        if check.get("category", "correctness") not in CATEGORIES:
            errors.append(f"{label}: category must be one of {list(CATEGORIES)}")
        if check.get("severity", "major") not in SEVERITIES:
            errors.append(f"{label}: severity must be one of {list(SEVERITIES)}")
        if op == "regex" and isinstance(check.get("value"), str):
            try:
                re.compile(check["value"])
            except re.error as exc:
                errors.append(f"{label}: invalid regex ({exc})")
        if op == "between" and not (isinstance(check.get("value"), list) and len(check["value"]) == 2):
            errors.append(f"{label}: 'between' needs a [low, high] list")
        if op == "type_is" and check.get("value") not in set(_TYPE_NAMES) | {"null", "number"}:
            errors.append(f"{label}: unknown type name '{check.get('value')}'")
    if errors:
        raise ExpectationSpecError(errors)


# ---- evaluator ----------------------------------------------------------------------------------

CustomEvaluator = Callable[[TraceRecord, Dict[str, Any]], List[CheckResult]]


class OutcomeEvaluator:
    """Evaluates a trace against its expected block. Custom evaluators are pluggable."""

    def __init__(self) -> None:
        self._customs: Dict[str, CustomEvaluator] = {}

    def register_custom(self, name: str, fn: CustomEvaluator) -> None:
        self._customs[name] = fn

    def validate(self, expected: Optional[Dict[str, Any]]) -> None:
        validate_expected(expected, self._customs)

    def evaluate(self, record: TraceRecord) -> OutcomeEvaluation:
        expected = record.expected
        self.validate(expected)
        stamp = datetime.now(timezone.utc).isoformat()
        if not expected:
            return OutcomeEvaluation(record.execution_id, "no_expectation", None, [], "No expected outcome was provided", stamp)

        expect_error = expected.get("expect_error")
        checks: List[CheckResult] = []

        if record.status == "error":
            err = record.error or {}
            err_type = err.get("type", "Unknown")
            if expect_error is None:
                checks.append(CheckResult(
                    "run_completed", "", "error", "equals", "success", "error", False,
                    f"Run failed with {err_type}: {err.get('message', '')}", "execution", "critical",
                ))
                return self._finish(record, checks, stamp, forced="error")
            matched = expect_error is True or err_type == expect_error
            checks.append(CheckResult(
                "expected_error", "type", "error", "equals", expect_error, err_type, matched,
                "Run failed as expected" if matched else f"Expected error '{expect_error}' but got '{err_type}'",
                "correctness" if matched else "wrong_error_type", "major",
            ))
            return self._finish(record, checks, stamp)

        if expect_error is not None:
            checks.append(CheckResult(
                "expected_error", "type", "error", "equals", expect_error, None, False,
                "Run was expected to fail but succeeded", "unexpected_success", "major",
            ))
            return self._finish(record, checks, stamp)

        context = {"output": record.output, "usage": record.usage, "events": record.events, "error": record.error}
        for index, spec in enumerate(expected.get("checks", []), start=1):
            checks.append(self._run_check(spec, index, context))

        if expected.get("max_latency_ms") is not None:
            limit = expected["max_latency_ms"]
            ok = record.duration_ms <= limit
            checks.append(CheckResult(
                "latency_within_limit", "duration_ms", "run", "lte", limit, record.duration_ms, ok,
                "Within latency limit" if ok else f"Took {record.duration_ms} ms (limit {limit} ms)",
                "performance", "minor",
            ))
        if expected.get("custom"):
            checks += self._customs[expected["custom"]](record, expected)

        if not checks:
            return OutcomeEvaluation(record.execution_id, "no_expectation", None, [], "The expected block contains no checks", stamp)
        return self._finish(record, checks, stamp)

    @staticmethod
    def _finish(record: TraceRecord, checks: List[CheckResult], stamp: str, forced: Optional[str] = None) -> OutcomeEvaluation:
        passed = sum(1 for c in checks if c.passed)
        verdict = forced or ("pass" if passed == len(checks) else "fail")
        score = passed / len(checks) if checks else None
        failed = [c for c in checks if not c.passed]
        message = "All checks passed" if not failed else f"{len(failed)} of {len(checks)} checks failed"
        return OutcomeEvaluation(record.execution_id, verdict, round(score, 4) if score is not None else None, checks, message, stamp)

    @staticmethod
    def _run_check(spec: Dict[str, Any], index: int, context: Dict[str, Any]) -> CheckResult:
        op = spec["op"]
        source = spec.get("source", "output")
        path = spec["path"]
        category = spec.get("category", "correctness")
        severity = spec.get("severity", "critical" if category == "safety" else "major")
        name = spec.get("name") or f"{source}.{path or '*'} {op}"
        value = resolve_path(context[source], path)
        missing = value is _MISSING

        if missing and op not in _MISSING_OK:
            return CheckResult(name, path, source, op, spec.get("value"), None, False,
                               f"'{path}' is missing from the {source}", category, severity, missing=True)
        actual = None if missing else value
        passed = True if missing else bool(_OPS[op][1](actual, spec))
        message = "OK" if passed else f"Expected {op} {spec.get('value')!r}, got {actual!r}"
        return CheckResult(name, path, source, op, spec.get("value"), actual, passed, message, category, severity)
