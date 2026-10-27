"""DataUpdateCoordinator for Ovumcy."""
from __future__ import annotations

from datetime import timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OvumcyApiError, OvumcyAuthError, OvumcyClient
from .const import DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN

_LOGGER = logging.getLogger(__name__)


class OvumcyDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Polls /api/v1/stats/overview on an interval."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: OvumcyClient) -> None:
        self.client = client
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
        )

    async def _async_update_data(self) -> dict:
        try:
            return await self.client.async_get_stats_overview()
        except OvumcyAuthError as err:
            # A revoked or replaced key will not fix itself: start Home
            # Assistant's re-authentication flow instead of retrying forever.
            raise ConfigEntryAuthFailed(str(err)) from err
        except OvumcyApiError as err:
            raise UpdateFailed(f"Ovumcy API error: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Could not reach Ovumcy: {err}") from err
