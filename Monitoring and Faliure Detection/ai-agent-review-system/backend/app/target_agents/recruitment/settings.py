"""Loading, overriding and versioning the recruitment agent's configuration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...integration.config_utils import apply_overrides as _apply_overrides
from ...integration.config_utils import config_version, load_yaml  # noqa: F401  (re-exported)

DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")

# Sections whose keys are free-form (new skills may be added by an override).
_OPEN_SECTIONS = ("skills",)


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    return load_yaml(path or DEFAULT_CONFIG_PATH)


def apply_overrides(config: Dict[str, Any], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return _apply_overrides(config, overrides, open_sections=_OPEN_SECTIONS)


def load_jobs(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        jobs = json.load(fh)
    required = {"id", "title", "required_skills", "preferred_skills", "min_years", "min_education"}
    for job in jobs:
        missing = required - set(job)
        if missing:
            raise ValueError(f"Job {job.get('id', '?')} is missing fields: {sorted(missing)}")
    return jobs
