"""Config flow for Ovumcy.

Ovumcy has no API-key auth, so setup asks for the same email/password used
to sign into the web UI. Credentials are stored in the config entry like any
other username/password integration (e.g. many camera/NAS integrations);
they are validated live against POST /api/v1/sessions before the entry is
created.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .api import OvumcyApiError, OvumcyAuthError, OvumcyClient, build_session
from .const import CONF_BASE_URL, CONF_IP_OVERRIDE, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_IP_OVERRIDE): str,
    }
)


class OvumcyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup step."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].rstrip("/")
            ip_override = user_input.get(CONF_IP_OVERRIDE) or None
            await self.async_set_unique_id(f"{base_url}::{user_input[CONF_EMAIL]}")
            self._abort_if_unique_id_configured()

            # A throwaway session just for the connection test; the
            # integration's real runtime session is created in __init__.py.
            session = build_session(self.hass, base_url, ip_override)
            try:
                client = OvumcyClient(
                    session, base_url, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
                try:
                    await client.async_test_connection()
                except OvumcyAuthError:
                    errors["base"] = "invalid_auth"
                except (OvumcyApiError, aiohttp.ClientError) as err:
                    # This is the one place a silent "cannot_connect" was
                    # previously indistinguishable from a real bug — log the
                    # real exception so a DNS failure, TLS error, and a
                    # genuine connection refusal don't all look identical.
                    _LOGGER.error(
                        "Ovumcy connection test failed for %s (ip_override=%s): %r",
                        base_url,
                        ip_override,
                        err,
                    )
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=f"Ovumcy ({user_input[CONF_EMAIL]})",
                        data={
                            CONF_BASE_URL: base_url,
                            CONF_EMAIL: user_input[CONF_EMAIL],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            CONF_IP_OVERRIDE: ip_override,
                        },
                    )
            finally:
                # build_session may have returned HA's shared session (not
                # ours to close) or a dedicated one (ip_override case) —
                # only close what we own.
                if ip_override:
                    await session.close()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
