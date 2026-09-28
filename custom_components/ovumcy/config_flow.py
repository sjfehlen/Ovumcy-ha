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
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import OvumcyApiError, OvumcyAuthError, OvumcyClient
from .const import CONF_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
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
            await self.async_set_unique_id(f"{base_url}::{user_input[CONF_EMAIL]}")
            self._abort_if_unique_id_configured()

            # A dedicated, cookie-jar-enabled session just for the connection
            # test; the integration's runtime session is created in __init__.py.
            session = async_create_clientsession(self.hass)
            client = OvumcyClient(
                session, base_url, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )
            try:
                await client.async_test_connection()
            except OvumcyAuthError:
                errors["base"] = "invalid_auth"
            except (OvumcyApiError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Ovumcy ({user_input[CONF_EMAIL]})",
                    data={
                        CONF_BASE_URL: base_url,
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
