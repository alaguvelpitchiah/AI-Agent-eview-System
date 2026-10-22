"""Connect any existing agent that is exposed over HTTP (black-box integration).

Agents are registered from the trusted agents.yaml file, never from an API
request, because letting callers choose URLs would allow server-side request
forgery against internal services.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import httpx

from ..base_adapter import (
    TRACE_EVENTS,
    TRACE_IO,
    AdapterOutput,
    AgentCapabilities,
    AgentInfo,
    BaseAgentAdapter,
    TraceEvent,
)
from ..errors import AdapterConfigError, AgentRunError

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand_env(value: str) -> str:
    """Replace ${NAME} with the environment variable, so secrets stay out of files."""

    def repl(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name not in os.environ:
            raise AdapterConfigError(f"Environment variable '{name}' is not set")
        return os.environ[name]

    return _ENV_REF.sub(repl, value)


def get_path(data: Any, path: Optional[str]) -> Any:
    """Read a dotted path such as 'result.items.0.text'. An empty path returns data."""
    if not path:
        return data
    node = data
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            raise KeyError(path)
    return node


class HttpAgentAdapter(BaseAgentAdapter):
    REQUIRED = ("agent_id", "name", "url")

    def __init__(
        self,
        *,
        agent_id: str,
        name: str,
        url: str,
        agent_type: str = "custom",
        version: str = "unknown",
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        example_inputs: Optional[List[Dict[str, Any]]] = None,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 30.0,
        send_as: str = "wrapped",
        output_path: Optional[str] = None,
        events_path: Optional[str] = None,
        usage_path: Optional[str] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        if not url.startswith(("http://", "https://")):
            raise AdapterConfigError(f"Agent '{agent_id}': url must start with http:// or https://")
        if method.upper() not in ("POST", "GET"):
            raise AdapterConfigError(f"Agent '{agent_id}': method must be POST or GET")
        if send_as not in ("wrapped", "raw"):
            raise AdapterConfigError(f"Agent '{agent_id}': send_as must be 'wrapped' or 'raw'")

        self._url = url
        self._method = method.upper()
        self._headers = {k: expand_env(str(v)) for k, v in (headers or {}).items()}
        self._timeout = float(timeout_seconds)
        self._send_as = send_as
        self._output_path = output_path
        self._events_path = events_path
        self._usage_path = usage_path
        self._client = client or httpx.Client(timeout=self._timeout)
        self._info = AgentInfo(
            agent_id=agent_id,
            name=name,
            agent_type=agent_type,
            version=version,
            description=description or f"HTTP agent at {url}",
            input_schema=input_schema or {"fields": {}, "allow_extra": True},
            capabilities=AgentCapabilities(trace_level=TRACE_EVENTS if events_path else TRACE_IO),
            example_inputs=example_inputs or [],
        )

    @classmethod
    def from_config(cls, entry: Dict[str, Any], client: Optional[httpx.Client] = None) -> "HttpAgentAdapter":
        missing = [k for k in cls.REQUIRED if not entry.get(k)]
        if missing:
            raise AdapterConfigError(f"HTTP agent entry is missing: {', '.join(missing)}")
        allowed = {
            "agent_type", "version", "description", "input_schema", "example_inputs", "method",
            "headers", "timeout_seconds", "send_as", "output_path", "events_path", "usage_path",
        }
        unknown = set(entry) - allowed - set(cls.REQUIRED) - {"type", "enabled"}
        if unknown:
            raise AdapterConfigError(f"Unknown keys for HTTP agent '{entry['agent_id']}': {sorted(unknown)}")
        kwargs = {k: entry[k] for k in allowed if k in entry}
        return cls(agent_id=entry["agent_id"], name=entry["name"], url=entry["url"], client=client, **kwargs)

    def info(self) -> AgentInfo:
        return self._info

    def run(self, task_input: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None) -> AdapterOutput:
        body = task_input if self._send_as == "raw" else {"input": task_input}
        try:
            if self._method == "GET":
                response = self._client.get(self._url, params=task_input, headers=self._headers, timeout=self._timeout)
            else:
                response = self._client.post(self._url, json=body, headers=self._headers, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise AgentRunError(f"Could not reach agent: {type(exc).__name__}", error_type="ConnectionError") from exc

        if response.status_code >= 400:
            raise AgentRunError(
                f"Agent returned HTTP {response.status_code}: {response.text[:200]}", error_type="HTTPError"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise AgentRunError("Agent response was not valid JSON", error_type="InvalidResponse") from exc

        try:
            output = get_path(payload, self._output_path)
        except KeyError as exc:
            raise AgentRunError(f"Output path {exc} not found in agent response", error_type="InvalidResponse") from exc

        return AdapterOutput(
            output=output,
            events=self._read_events(payload),
            agent_version=self._info.version,
            usage=self._read_usage(payload),
        )

    def _read_events(self, payload: Any) -> List[TraceEvent]:
        if not self._events_path:
            return []
        try:
            raw = get_path(payload, self._events_path)
        except KeyError:
            return []
        events = []
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict):
                continue
            events.append(
                TraceEvent(
                    kind=str(item.get("kind", "stage")),
                    name=str(item.get("name", "step")),
                    input=item.get("input"),
                    output=item.get("output"),
                    duration_ms=float(item.get("duration_ms", 0.0) or 0.0),
                    error=item.get("error"),
                    metadata=item.get("metadata") or {},
                )
            )
        return events

    def _read_usage(self, payload: Any) -> Dict[str, Any]:
        if not self._usage_path:
            return {}
        try:
            usage = get_path(payload, self._usage_path)
        except KeyError:
            return {}
        return usage if isinstance(usage, dict) else {}
