"""Authentication and Secrets Manager for External AI Agents.

Securely handles credentials, headers, and secret redaction for:
- None (Public endpoints)
- Bearer Token (e.g. OpenAI / Anthropic / HuggingFace)
- API Key via Custom Header (e.g. 'x-api-key', 'X-Auth-Token')
- API Key via Query Parameter (e.g. '?key=...')
- HTTP Basic Auth (Username / Password)
- Custom Arbitrary Headers
"""

from __future__ import annotations

import base64
import os
import re
from enum import Enum
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field


class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY_HEADER = "api_key_header"
    API_KEY_QUERY = "api_key_query"
    BASIC = "basic"
    CUSTOM_HEADERS = "custom_headers"


class AuthConfig(BaseModel):
    auth_type: AuthType = Field(default=AuthType.NONE)
    token: Optional[str] = Field(default=None, description="Bearer token or API key value")
    api_key_header_name: Optional[str] = Field(default="x-api-key", description="Header name for API key")
    api_key_query_name: Optional[str] = Field(default="api_key", description="Query param name for API key")
    username: Optional[str] = Field(default=None, description="Username for Basic auth")
    password: Optional[str] = Field(default=None, description="Password for Basic auth")
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers dict")

    def to_masked_dict(self) -> Dict[str, Any]:
        """Return safe representation of auth config with secrets redacted for UI and logs."""
        d = self.model_dump()
        if self.token:
            d["token"] = mask_secret(self.token)
        if self.password:
            d["password"] = mask_secret(self.password)
        if self.custom_headers:
            d["custom_headers"] = {
                k: mask_secret(v) if is_sensitive_key(k) else v
                for k, v in self.custom_headers.items()
            }
        return d


_SENSITIVE_KEYWORDS = {"auth", "token", "key", "secret", "password", "credential", "bearer", "cookie"}


def is_sensitive_key(key_name: str) -> bool:
    """Return True if header name indicates sensitive credentials."""
    lowered = key_name.lower()
    return any(kw in lowered for kw in _SENSITIVE_KEYWORDS)


def mask_secret(secret: str) -> str:
    """Mask secret value preserving only first 3 and last 4 chars if length allows."""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "********"
    return f"{secret[:3]}...{secret[-4:]}"


class AuthManager:
    """Applies authentication to outgoing HTTP client requests and redacts secrets."""

    @staticmethod
    def resolve_value(val: Optional[str]) -> Optional[str]:
        """Expand ${ENV_VAR} syntax if present."""
        if not val:
            return val
        match = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", val)
        if match:
            env_var = match.group(1)
            return os.environ.get(env_var, val)
        return val

    @classmethod
    def apply_auth(
        cls,
        auth_config: Optional[AuthConfig],
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Inject appropriate auth headers or query parameters into request dicts."""
        out_headers = dict(headers or {})
        out_params = dict(params or {})

        if not auth_config or auth_config.auth_type == AuthType.NONE:
            return out_headers, out_params

        token = cls.resolve_value(auth_config.token) or ""

        if auth_config.auth_type == AuthType.BEARER:
            if token:
                out_headers["Authorization"] = f"Bearer {token}"

        elif auth_config.auth_type == AuthType.API_KEY_HEADER:
            header_name = auth_config.api_key_header_name or "x-api-key"
            if token:
                out_headers[header_name] = token

        elif auth_config.auth_type == AuthType.API_KEY_QUERY:
            param_name = auth_config.api_key_query_name or "api_key"
            if token:
                out_params[param_name] = token

        elif auth_config.auth_type == AuthType.BASIC:
            username = cls.resolve_value(auth_config.username) or ""
            password = cls.resolve_value(auth_config.password) or ""
            creds = f"{username}:{password}".encode("utf-8")
            b64_creds = base64.b64encode(creds).decode("ascii")
            out_headers["Authorization"] = f"Basic {b64_creds}"

        elif auth_config.auth_type == AuthType.CUSTOM_HEADERS:
            for k, v in auth_config.custom_headers.items():
                out_headers[k] = cls.resolve_value(v) or v

        return out_headers, out_params

    @classmethod
    def redact_headers(cls, headers: Dict[str, str]) -> Dict[str, str]:
        """Return a copy of headers dictionary with all credentials masked for safe logging."""
        sanitized = {}
        for k, v in headers.items():
            if is_sensitive_key(k):
                sanitized[k] = mask_secret(v)
            else:
                sanitized[k] = v
        return sanitized
