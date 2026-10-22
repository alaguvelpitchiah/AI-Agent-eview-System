"""Dependency-free validation of task inputs against an adapter's schema.

Schema format::

    {"fields": {"name": {"type": "str", "required": True,
                         "min_length": 1, "max_length": 100,
                         "choices": [...], "min": 0, "max": 10,
                         "default": ...}},
     "allow_extra": False}
"""
from __future__ import annotations

import json
from typing import Any, Dict

from .errors import TaskValidationError

_TYPES = {
    "str": str,
    "int": int,
    "float": (int, float),
    "bool": bool,
    "dict": dict,
    "list": list,
    "any": object,
}


def validate_task(task: Any, schema: Dict[str, Any], max_bytes: int = 100_000) -> Dict[str, Any]:
    """Return a cleaned copy of ``task`` or raise TaskValidationError."""
    if not isinstance(task, dict):
        raise TaskValidationError(["Task must be a JSON object"])

    try:
        size = len(json.dumps(task).encode("utf-8"))
    except (TypeError, ValueError):
        raise TaskValidationError(["Task must be JSON-serialisable"])
    if size > max_bytes:
        raise TaskValidationError([f"Task is too large ({size} bytes, limit {max_bytes})"])

    fields = schema.get("fields", {})
    errors = []
    cleaned: Dict[str, Any] = {}

    for name in task:
        if name in fields:
            continue
        if schema.get("allow_extra", False):
            cleaned[name] = task[name]  # open schema: pass unknown fields through unchanged
        else:
            errors.append(f"Unknown field '{name}'")

    for name, rule in fields.items():
        value = task.get(name)
        if value is None:
            if rule.get("required"):
                errors.append(f"Field '{name}' is required")
            elif "default" in rule:
                cleaned[name] = rule["default"]
            continue

        type_name = rule.get("type", "str")
        expected = _TYPES[type_name]
        is_bool_for_number = type_name in ("int", "float") and isinstance(value, bool)
        if is_bool_for_number or not isinstance(value, expected):
            errors.append(f"Field '{name}' must be of type {type_name}")
            continue

        if isinstance(value, str):
            value = value.strip()
            if "min_length" in rule and len(value) < rule["min_length"]:
                errors.append(f"Field '{name}' must be at least {rule['min_length']} characters")
                continue
            if "max_length" in rule and len(value) > rule["max_length"]:
                errors.append(f"Field '{name}' must be at most {rule['max_length']} characters")
                continue

        if type_name in ("int", "float"):
            if "min" in rule and value < rule["min"]:
                errors.append(f"Field '{name}' must be >= {rule['min']}")
                continue
            if "max" in rule and value > rule["max"]:
                errors.append(f"Field '{name}' must be <= {rule['max']}")
                continue

        if "choices" in rule and value not in rule["choices"]:
            errors.append(f"Field '{name}' must be one of {sorted(rule['choices'])}")
            continue

        cleaned[name] = value

    if errors:
        raise TaskValidationError(errors)
    return cleaned
