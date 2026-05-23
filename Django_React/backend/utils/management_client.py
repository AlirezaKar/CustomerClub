"""
HTTP client for the management CustomerClub API (server-to-server).
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ManagementAPIError(Exception):
    """Management API returned an error or was unreachable."""

    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


def management_configured() -> bool:
    base_url = (getattr(settings, "MANAGEMENT_API_BASE_URL", "") or "").strip()
    api_key = (getattr(settings, "MANAGEMENT_SERVICE_API_KEY", "") or "").strip()
    return bool(base_url and api_key)


def management_base_url() -> str:
    return (getattr(settings, "MANAGEMENT_API_BASE_URL", "") or "").rstrip("/")


def management_headers() -> dict[str, str]:
    api_key = getattr(settings, "MANAGEMENT_SERVICE_API_KEY", "") or ""
    return {"X-Management-API-Key": api_key}


def management_timeout() -> int:
    return int(getattr(settings, "MANAGEMENT_API_TIMEOUT", 15))


def management_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    if not management_configured():
        raise ManagementAPIError("Management API is not configured.")

    url = f"{management_base_url()}{path}"
    try:
        response = requests.request(
            method,
            url,
            params=params,
            json=json,
            headers={**management_headers(), "Content-Type": "application/json"},
            timeout=management_timeout(),
        )
    except requests.RequestException as exc:
        logger.exception("Management API request failed: %s %s", method, url)
        raise ManagementAPIError("Could not reach management server.") from exc

    try:
        payload = response.json() if response.content else {}
    except ValueError:
        payload = {}

    if response.ok:
        if isinstance(payload, (dict, list)):
            return payload
        return {}

    error = payload.get("error") if isinstance(payload, dict) else None
    if not error:
        error = f"Management API error ({response.status_code})"
    raise ManagementAPIError(str(error), status_code=response.status_code, payload=payload)
