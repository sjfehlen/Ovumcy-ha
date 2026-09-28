"""Binary sensor entities for Ovumcy."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BASE_URL, DOMAIN
from .coordinator import OvumcyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class OvumcyBinarySensorEntityDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[OvumcyBinarySensorEntityDescription, ...] = (
    OvumcyBinarySensorEntityDescription(
        key="period_active",
        translation_key="period_active",
        icon="mdi:water",
        value_fn=lambda d: d.get("current_phase") == "menstrual",
    ),
    OvumcyBinarySensorEntityDescription(
        key="ovulation_confirmed",
        translation_key="ovulation_confirmed",
        icon="mdi:check-circle",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("ovulation_confirmed"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: OvumcyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OvumcyBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class OvumcyBinarySensor(
    CoordinatorEntity[OvumcyDataUpdateCoordinator], BinarySensorEntity
):
    entity_description: OvumcyBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OvumcyDataUpdateCoordinator,
        entry: ConfigEntry,
        description: OvumcyBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Ovumcy ({entry.data.get(CONF_EMAIL)})",
            manufacturer="Ovumcy",
            configuration_url=entry.data.get(CONF_BASE_URL),
        )

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data or {})
