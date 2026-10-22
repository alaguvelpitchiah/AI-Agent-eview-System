"""Remove secrets from traces before they are stored."""
from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEY = re.compile(r"(password|passwd|secret|token|api[_-]?key|authorization|credential|private[_-]?key)", re.I)
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}")
_API_KEY_LIKE = re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}")
REDACTED = "[REDACTED]"


def redact(value: Any) -> Any:
    """Return a copy of a JSON-like value with sensitive keys and token-like strings masked."""
    if isinstance(value, dict):
        return {k: (REDACTED if _SENSITIVE_KEY.search(str(k)) else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _API_KEY_LIKE.sub(REDACTED, _BEARER.sub(f"Bearer {REDACTED}", value))
    return value
