"""Build the agent registry from the agents configuration file.

agents.yaml is a trusted, local file. Two kinds of entries are supported:

* ``type: factory``: ``factory: "package.module:function"``. The function is
  called as ``function(settings, **options)`` and returns an adapter.
* ``type: http``: connects an existing agent exposed over HTTP.

Entries with ``enabled: false`` are skipped.
"""
from __future__ import annotations

import importlib
import re
from typing import Any, Dict

from ..config import Settings
from .adapters.http_adapter import HttpAgentAdapter
from .agent_registry import AgentRegistry
from .base_adapter import BaseAgentAdapter
from .config_utils import load_yaml
from .errors import AdapterConfigError

_FACTORY_REF = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")


def _build_factory(entry: Dict[str, Any], settings: Settings) -> BaseAgentAdapter:
    ref = entry.get("factory", "")
    if not _FACTORY_REF.match(ref):
        raise AdapterConfigError(f"Invalid factory reference '{ref}' (expected 'package.module:function')")
    module_name, func_name = ref.split(":")
    try:
        factory = getattr(importlib.import_module(module_name), func_name)
    except (ImportError, AttributeError) as exc:
        raise AdapterConfigError(f"Cannot load factory '{ref}': {exc}") from exc
    try:
        adapter = factory(settings, **(entry.get("options") or {}))
    except Exception as exc:  # a broken factory must surface as a configuration error
        raise AdapterConfigError(f"Factory '{ref}' failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(adapter, BaseAgentAdapter):
        raise AdapterConfigError(f"Factory '{ref}' did not return a BaseAgentAdapter")
    return adapter


def load_registry(settings: Settings) -> AgentRegistry:
    path = settings.agents_config_path
    if not path.exists():
        raise AdapterConfigError(f"Agents configuration file not found: {path}")
    config = load_yaml(path) or {}
    entries = config.get("agents")
    if not isinstance(entries, list):
        raise AdapterConfigError("agents.yaml must contain an 'agents' list")

    registry = AgentRegistry()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise AdapterConfigError(f"agents.yaml entry {index} must be a mapping")
        if entry.get("enabled", True) is False:
            continue
        kind = entry.get("type")
        try:
            if kind == "factory":
                adapter = _build_factory(entry, settings)
            elif kind == "http":
                adapter = HttpAgentAdapter.from_config(entry)
            else:
                raise AdapterConfigError(f"Unknown agent type '{kind}' (use 'factory' or 'http')")
        except AdapterConfigError as exc:
            raise AdapterConfigError(f"agents.yaml entry {index}: {exc}") from exc
        registry.register(adapter)
    return registry
