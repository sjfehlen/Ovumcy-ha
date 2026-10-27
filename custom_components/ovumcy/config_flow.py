"""Config flow for Ovumcy.

Setup asks for the instance URL and an API key created in Ovumcy under
Settings → API key. The key is validated live against
GET /api/v1/stats/overview before the entry is created. A key that is later
revoked or replaced starts Home Assistant's re-authentication flow.
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol

from homeassistant import config_entries

from .api import (
    OvumcyApiError,
    OvumcyAuthError,
    OvumcyClient,
    build_session,
    looks_like_api_key,
)
from .const import CONF_API_KEY, CONF_BASE_URL, CONF_IP_OVERRIDE, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_IP_OVERRIDE): str,
    }
)

STEP_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


async def _validate_key(
    hass, base_url: str, api_key: str, ip_override: str | None
) -> str | None:
    """Return a config-flow error key, or None when the key works."""
    if not looks_like_api_key(api_key):
        return "invalid_key_format"
    # A throwaway session just for the connection test; the integration's real
    # runtime session is created in __init__.py.
    session = build_session(hass, base_url, ip_override)
    try:
        await OvumcyClient(session, base_url, api_key).async_test_connection()
    except OvumcyAuthError:
        return "invalid_auth"
    except (OvumcyApiError, aiohttp.ClientError) as err:
        # Log the real exception so a DNS failure, a TLS error and a refused
        # connection do not all look identical.
        _LOGGER.error(
            "Ovumcy connection test failed for %s (ip_override=%s): %r",
            base_url,
            ip_override,
            err,
        )
        return "cannot_connect"
    finally:
        # build_session may have returned HA's shared session (not ours to
        # close) or a dedicated one (ip_override case) — only close what we own.
        if ip_override:
            await session.close()
    return None


class OvumcyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup and re-authentication steps."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].rstrip("/")
            api_key = user_input[CONF_API_KEY].strip()
            ip_override = user_input.get(CONF_IP_OVERRIDE) or None

            # One entry per instance and key. The key itself is never used as the
            # id: a short digest tells two accounts on one instance apart without
            # copying any of the secret into the registry.
            fingerprint = hashlib.sha256(api_key.encode()).hexdigest()[:12]
            await self.async_set_unique_id(f"{base_url}::{fingerprint}")
            self._abort_if_unique_id_configured()

            error = await _validate_key(self.hass, base_url, api_key, ip_override)
            if error is None:
                host = urlparse(base_url).hostname or base_url
                return self.async_create_entry(
                    title=f"Ovumcy ({host})",
                    data={
                        CONF_BASE_URL: base_url,
                        CONF_API_KEY: api_key,
                        CONF_IP_OVERRIDE: ip_override,
                    },
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Start re-authentication: the key was revoked, replaced or never set."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            error = await _validate_key(
                self.hass,
                entry.data[CONF_BASE_URL],
                api_key,
                entry.data.get(CONF_IP_OVERRIDE),
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_KEY: api_key}
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            description_placeholders={"base_url": entry.data[CONF_BASE_URL]},
            errors=errors,
        )
