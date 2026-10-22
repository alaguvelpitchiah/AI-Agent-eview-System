"""Shared helpers for agents that keep a versioned, overridable configuration."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _nest(overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Turn {'ranking.weights.education': 0.3} into nested dictionaries."""
    nested: Dict[str, Any] = {}
    for key, value in overrides.items():
        parts = key.split(".")
        node = nested
        for part in parts[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise ValueError(f"Conflicting override for '{key}'")
        node[parts[-1]] = value
    return nested


def _merge(target: Dict[str, Any], source: Dict[str, Any], path: List[str], open_sections: Iterable[str]) -> None:
    for key, value in source.items():
        here = path + [key]
        if key not in target and not (path and path[0] in open_sections):
            raise ValueError(f"Unknown config key '{'.'.join(here)}'")
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value, here, open_sections)
        else:
            target[key] = copy.deepcopy(value)


def apply_overrides(
    config: Dict[str, Any],
    overrides: Optional[Dict[str, Any]],
    open_sections: Iterable[str] = (),
) -> Dict[str, Any]:
    """Return a modified deep copy of ``config``; the original is never changed.

    Keys may be dotted paths or nested dictionaries. Unknown keys raise
    ValueError so a typo can never silently pass as a valid experiment.
    ``open_sections`` lists top-level sections whose keys are free-form.
    """
    result = copy.deepcopy(config)
    if overrides:
        _merge(result, _nest(overrides), [], tuple(open_sections))
    return result


def config_version(config: Dict[str, Any]) -> str:
    """Stable identifier: declared version plus a short hash of the full content."""
    digest = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:8]
    return f"{config.get('version', '0')}+{digest}"
