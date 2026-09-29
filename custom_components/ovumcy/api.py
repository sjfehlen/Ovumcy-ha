"""Thin async client for the Ovumcy session-auth API.

Ovumcy has no API-key/service-account auth — only browser-style session
cookies (`ovumcy_auth`) protected by a double-submit CSRF cookie
(`ovumcy_csrf`). This client reproduces that flow: fetch a CSRF token via a
GET, POST credentials with the token to establish a session, and re-run that
dance automatically whenever a request comes back 401 (session expired or
never established).

Endpoints referenced (see docs/openapi.yaml in ovumcy/ovumcy-web):
  GET  /login                       - any GET issues the ovumcy_csrf cookie
  POST /api/v1/sessions             - login, body: {email, password, remember_me}
  GET  /api/v1/stats/overview       - StatsOverview: cycle day/phase/predictions
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp
from yarl import URL

from .const import AUTH_COOKIE, CSRF_COOKIE, CSRF_HEADER
from .resolver import StaticHostResolver

_LOGGER = logging.getLogger(__name__)


def build_session(hass, base_url: str, ip_override: str | None) -> aiohttp.ClientSession:
    """Build a cookie-jar-enabled session, optionally pinning base_url's host to an IP.

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


class OvumcyAuthError(Exception):
    """Raised when login fails (bad credentials, disabled local sign-in, etc.)."""


class OvumcyApiError(Exception):
    """Raised for any other non-2xx response from the Ovumcy API."""


class OvumcyClient:
    """Session-authenticated client for a single Ovumcy instance."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        email: str,
        password: str,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._email = email
        self._password = password
        self._authenticated = False

    async def _get_csrf_token(self) -> str:
        """Issue a GET to obtain a fresh ovumcy_csrf cookie, return its value."""
        async with self._session.get(f"{self._base_url}/login") as resp:
            resp.raise_for_status()
            cookie = self._session.cookie_jar.filter_cookies(URL(self._base_url)).get(
                CSRF_COOKIE
            )
            if cookie is None:
                raise OvumcyApiError("no CSRF cookie returned by /login")
            return cookie.value

    async def async_login(self) -> None:
        """Authenticate and establish a 30-day session (remember_me=true)."""
        csrf_token = await self._get_csrf_token()
        payload = {
            "email": self._email,
            "password": self._password,
            "remember_me": True,
        }
        headers = {
            CSRF_HEADER: csrf_token,
            "Accept": "application/json",
            # Ovumcy's CSRF check also validates Origin/Referer against the
            # real host — a browser sends these on every form POST, but a
            # bare aiohttp client doesn't send either unless told to. Without
            # this, every state-changing request 403s with an empty/HTML
            # body regardless of the CSRF token being otherwise correct.
            "Origin": self._base_url,
            "Referer": f"{self._base_url}/login",
        }
        async with self._session.post(
            f"{self._base_url}/api/v1/sessions", json=payload, headers=headers
        ) as resp:
            if resp.status == 401:
                raise OvumcyAuthError("invalid Ovumcy credentials")
            if resp.status == 403:
                try:
                    body = await resp.json(content_type=None)
                    message = body.get("error", "local sign-in unavailable on this deployment")
                except (ValueError, aiohttp.ContentTypeError):
                    message = "CSRF/origin check rejected the request (HTTP 403, non-JSON body)"
                raise OvumcyAuthError(message)
            resp.raise_for_status()
            body = await resp.json(content_type=None)
            if body.get("requires_totp"):
                raise OvumcyAuthError(
                    "account has 2FA enabled — not supported by this integration"
                )

        auth_cookie = self._session.cookie_jar.filter_cookies(URL(self._base_url)).get(
            AUTH_COOKIE
        )
        if auth_cookie is None:
            raise OvumcyApiError("login succeeded but no session cookie was issued")
        self._authenticated = True

    async def _request(self, method: str, path: str) -> dict[str, Any]:
        if not self._authenticated:
            await self.async_login()

        async with self._session.request(
            method, f"{self._base_url}{path}", headers={"Accept": "application/json"}
        ) as resp:
            if resp.status == 401:
                # Session expired server-side; re-authenticate once and retry.
                self._authenticated = False
                await self.async_login()
                async with self._session.request(
                    method,
                    f"{self._base_url}{path}",
                    headers={"Accept": "application/json"},
                ) as retry_resp:
                    retry_resp.raise_for_status()
                    return await retry_resp.json(content_type=None)
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def async_get_stats_overview(self) -> dict[str, Any]:
        """Fetch /api/v1/stats/overview — cycle day, phase, predictions."""
        return await self._request("GET", "/api/v1/stats/overview")

    async def async_test_connection(self) -> None:
        """Used by the config flow to validate credentials before saving."""
        await self.async_login()
        await self.async_get_stats_overview()
