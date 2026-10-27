"""Thin async client for the Ovumcy API, authenticated with a per-account API key.

Ovumcy (the sjfehlen fork, and any build that includes per-account API keys)
accepts `Authorization: Bearer <key>` on a short list of read endpoints. There
is no login, no session cookie and no CSRF token: every request names the key
and is authorised by it alone. A key is created in Ovumcy under
Settings → API key and is shown once.

Endpoints referenced (see docs/openapi.yaml in the Ovumcy fork):
  GET  /api/v1/stats/overview   - StatsOverview: cycle day/phase/predictions
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .const import API_KEY_PREFIX
from .resolver import StaticHostResolver

_LOGGER = logging.getLogger(__name__)


def build_session(hass, base_url: str, ip_override: str | None) -> aiohttp.ClientSession:
    """Build a client session, optionally pinning base_url's host to an IP.

    Without `ip_override`, uses Home Assistant's shared `async_create_clientsession`
    helper (closed by HA itself on shutdown). With it, connector customization is
    required, which that helper doesn't expose, so this returns a dedicated session
    the caller owns and must close (see `async_unload_entry` in __init__.py).
    """
    if not ip_override:
        from homeassistant.helpers.aiohttp_client import async_create_clientsession

        return async_create_clientsession(hass)

    hostname = urlparse(base_url).hostname
    if not hostname:
        raise ValueError(f"could not parse hostname out of base_url: {base_url}")
    connector = aiohttp.TCPConnector(resolver=StaticHostResolver(hostname, ip_override))
    return aiohttp.ClientSession(connector=connector)


def looks_like_api_key(value: str) -> bool:
    """Cheap shape check so an obviously wrong paste is caught before a request."""
    return value.startswith(API_KEY_PREFIX) and len(value) > len(API_KEY_PREFIX)


class OvumcyAuthError(Exception):
    """Raised when the key is rejected (revoked, replaced, or never valid)."""


class OvumcyApiError(Exception):
    """Raised for any other non-2xx response from the Ovumcy API."""


class OvumcyClient:
    """API-key client for a single Ovumcy account."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def _request(self, method: str, path: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        async with self._session.request(
            method, f"{self._base_url}{path}", headers=headers
        ) as resp:
            if resp.status == 401:
                # Ovumcy answers an unknown, revoked and malformed key identically.
                raise OvumcyAuthError("the API key was rejected (revoked, replaced or invalid)")
            if resp.status == 403:
                # A key reaches only the routes its scope allows; a 403 here means
                # this build or this account refuses it (for example onboarding is
                # not finished), not that the key is wrong.
                try:
                    body = await resp.json(content_type=None)
                    message = body.get("error", "forbidden")
                except (ValueError, aiohttp.ContentTypeError):
                    message = "forbidden (non-JSON body)"
                raise OvumcyApiError(f"Ovumcy refused the request: {message}")
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def async_get_stats_overview(self) -> dict[str, Any]:
        """Fetch /api/v1/stats/overview — cycle day, phase, predictions."""
        return await self._request("GET", "/api/v1/stats/overview")

    async def async_test_connection(self) -> None:
        """Used by the config flow to validate the key before saving."""
        await self.async_get_stats_overview()
