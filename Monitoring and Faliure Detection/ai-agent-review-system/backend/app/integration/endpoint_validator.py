"""Endpoint Validator for External AI Agents.

Provides:
- SSRF (Server-Side Request Forgery) protection:
  Checks target host against loopback, link-local, private IP ranges (10.0.0.0/8, 172.16.0.0/12,
  192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16, IPv6 ::1).
  Allows local testing if allow_local=True or ENV ALLOW_LOCAL_TESTING=1.
- URL syntax and scheme validation (http, https).
- Network reachability probe with latency measurement.
- Response header & content-type inspection.
- Diagnostic summary report.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel, Field


class EndpointValidationResult(BaseModel):
    is_valid: bool
    is_reachable: bool
    url: str
    scheme: str
    host: str
    port: int
    resolved_ip: Optional[str] = None
    latency_ms: Optional[float] = None
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    server_header: Optional[str] = None
    ssrf_safe: bool = True
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    supported_methods: List[str] = Field(default_factory=list)


# Private / reserved network definitions
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # RFC 1918 Private
    ipaddress.ip_network("172.16.0.0/12"),    # RFC 1918 Private
    ipaddress.ip_network("192.168.0.0/16"),   # RFC 1918 Private
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("::1/128"),          # IPv6 Loopback
    ipaddress.ip_network("fe80::/10"),        # IPv6 Link-Local
    ipaddress.ip_network("fc00::/7"),         # IPv6 Unique Local
]


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP string belongs to a private, loopback, or link-local address block."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return True


def check_ssrf_safety(host: str, allow_local: bool = False) -> tuple[bool, Optional[str], Optional[str]]:
    """Validate host for SSRF vulnerability.
    
    Returns (is_safe, resolved_ip, error_message).
    """
    if allow_local or os.environ.get("ALLOW_LOCAL_TESTING", "0") == "1":
        try:
            ip = socket.gethostbyname(host)
            return True, ip, None
        except socket.gaierror as e:
            return False, None, f"DNS resolution failed for '{host}': {str(e)}"

    # Check common local aliases
    lowered = host.lower().strip()
    if lowered in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "localtest.me", "vhost.local"):
        return False, "127.0.0.1", "Targeting localhost or loopback address is prohibited for SSRF safety."

    if lowered.endswith(".internal") or lowered.endswith(".local") or lowered.endswith(".corp"):
        return False, None, f"Targeting internal/intranet domain '{host}' is prohibited."

    try:
        ip_str = socket.gethostbyname(host)
    except socket.gaierror as e:
        return False, None, f"Could not resolve host '{host}': {str(e)}"

    if is_private_ip(ip_str):
        return False, ip_str, f"Host '{host}' resolved to restricted private IP '{ip_str}'."

    return True, ip_str, None


async def validate_ai_endpoint(
    url: str,
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    timeout_seconds: float = 10.0,
    allow_local: bool = False,
    probe_payload: Optional[Dict[str, Any]] = None,
) -> EndpointValidationResult:
    """Perform comprehensive validation and reachability probe for an external AI endpoint."""
    if not url or not isinstance(url, str):
        return EndpointValidationResult(
            is_valid=False,
            is_reachable=False,
            url=str(url),
            scheme="",
            host="",
            port=0,
            error_message="URL cannot be empty.",
        )

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as e:
        return EndpointValidationResult(
            is_valid=False,
            is_reachable=False,
            url=url,
            scheme="",
            host="",
            port=0,
            error_message=f"Malformed URL: {str(e)}",
        )

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return EndpointValidationResult(
            is_valid=False,
            is_reachable=False,
            url=url,
            scheme=scheme,
            host=parsed.netloc,
            port=0,
            error_message=f"Unsupported scheme '{scheme}'. Must be 'http://' or 'https://'.",
        )

    host = parsed.hostname or ""
    if not host:
        return EndpointValidationResult(
            is_valid=False,
            is_reachable=False,
            url=url,
            scheme=scheme,
            host="",
            port=0,
            error_message="URL must contain a valid hostname.",
        )

    port = parsed.port or (443 if scheme == "https" else 80)

    # Check SSRF safety
    is_safe, resolved_ip, ssrf_error = check_ssrf_safety(host, allow_local=allow_local)
    if not is_safe:
        return EndpointValidationResult(
            is_valid=False,
            is_reachable=False,
            url=url,
            scheme=scheme,
            host=host,
            port=port,
            resolved_ip=resolved_ip,
            ssrf_safe=False,
            error_message=ssrf_error,
        )

    req_headers = dict(headers or {})
    if "User-Agent" not in req_headers:
        req_headers["User-Agent"] = "AIAgentReviewSystem-EndpointValidator/1.0"

    t0 = time.perf_counter()
    latency_ms = None
    status_code = None
    content_type = None
    server_header = None
    error_message = None
    is_reachable = False
    warnings = []

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            # First try OPTIONS or HEAD to discover supported methods
            supported_methods = []
            try:
                options_resp = await client.options(url, headers=req_headers)
                allow_header = options_resp.headers.get("allow", "")
                if allow_header:
                    supported_methods = [m.strip().upper() for m in allow_header.split(",")]
            except Exception:
                pass

            # Now probe with configured method
            probe_data = probe_payload or {"probe": "health_check", "ping": True}
            t_probe_start = time.perf_counter()
            
            if method.upper() == "GET":
                resp = await client.get(url, params={"probe": "ping"}, headers=req_headers)
            else:
                resp = await client.post(url, json=probe_data, headers=req_headers)

            latency_ms = (time.perf_counter() - t_probe_start) * 1000.0
            status_code = resp.status_code
            content_type = resp.headers.get("content-type", "")
            server_header = resp.headers.get("server")

            # 2xx, 3xx, 400, 422, 405 are considered reachable HTTP services
            if status_code < 500:
                is_reachable = True
            else:
                is_reachable = True
                warnings.append(f"Endpoint returned HTTP {status_code} on probe request.")

            if status_code == 401 or status_code == 403:
                warnings.append("Authentication required: Endpoint returned HTTP 401/403. Configure credentials.")
            elif status_code == 404:
                warnings.append("Endpoint path returned HTTP 404 Not Found. Verify the full endpoint path.")

            if content_type and "application/json" not in content_type:
                warnings.append(f"Response Content-Type is '{content_type}', expected 'application/json'.")

            if method.upper() not in supported_methods and supported_methods:
                supported_methods.append(method.upper())

    except httpx.ConnectTimeout:
        error_message = f"Connection timed out after {timeout_seconds:.1f}s."
    except httpx.ConnectError as e:
        error_message = f"Connection failed to '{host}:{port}': {str(e)}"
    except httpx.HTTPError as e:
        error_message = f"HTTP error during endpoint probe: {str(e)}"
    except Exception as e:
        error_message = f"Unexpected error during probe: {str(e)}"

    return EndpointValidationResult(
        is_valid=is_reachable and (status_code is not None and status_code < 500),
        is_reachable=is_reachable,
        url=url,
        scheme=scheme,
        host=host,
        port=port,
        resolved_ip=resolved_ip,
        latency_ms=round(latency_ms, 2) if latency_ms is not None else None,
        status_code=status_code,
        content_type=content_type,
        server_header=server_header,
        ssrf_safe=True,
        error_message=error_message,
        warnings=warnings,
        supported_methods=supported_methods or [method.upper()],
    )
