"""The Ovumcy integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .api import OvumcyClient, build_session
from .const import CONF_BASE_URL, CONF_IP_OVERRIDE, DOMAIN
from .coordinator import OvumcyDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ovumcy from a config entry."""
    ip_override = entry.data.get(CONF_IP_OVERRIDE)
    # A session-per-entry so each account's cookie jar stays isolated —
    # important if this instance is ever configured for more than one owner.
    # When ip_override is set, this session is self-owned (not HA's shared
    # one) and must be closed explicitly on unload, below.
    session = build_session(hass, entry.data[CONF_BASE_URL], ip_override)
    client = OvumcyClient(
        session,
        entry.data[CONF_BASE_URL],
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )

    coordinator = OvumcyDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "session": session,
        "owns_session": bool(ip_override),
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        stored = hass.data[DOMAIN].pop(entry.entry_id)
        if stored["owns_session"]:
            await stored["session"].close()
    return unload_ok
