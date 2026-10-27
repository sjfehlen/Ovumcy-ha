"""The Ovumcy integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import OvumcyClient, build_session
from .const import CONF_API_KEY, CONF_BASE_URL, CONF_IP_OVERRIDE, DOMAIN
from .coordinator import OvumcyDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Move a v1 (email/password) entry to v2 (API key).

    A password cannot be turned into a key, so the stored credentials are
    dropped — the plaintext password should not stay in the config entry — and
    the entry asks for a key through Home Assistant's re-authentication flow.
    """
    if entry.version == 1:
        data = {k: v for k, v in entry.data.items() if k not in (CONF_EMAIL, CONF_PASSWORD)}
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ovumcy from a config entry."""
    api_key = entry.data.get(CONF_API_KEY)
    if not api_key:
        # A migrated entry has no key yet: ask for one.
        raise ConfigEntryAuthFailed("an Ovumcy API key is required")

    ip_override = entry.data.get(CONF_IP_OVERRIDE)
    # When ip_override is set, this session is self-owned (not HA's shared
    # one) and must be closed explicitly on unload, below.
    session = build_session(hass, entry.data[CONF_BASE_URL], ip_override)
    client = OvumcyClient(session, entry.data[CONF_BASE_URL], api_key)

    coordinator = OvumcyDataUpdateCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except BaseException:
        # Setup failed (bad key, instance down): do not leak a session we own.
        if ip_override:
            await session.close()
        raise

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
