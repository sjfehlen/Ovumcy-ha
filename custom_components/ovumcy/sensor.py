"""Sensor entities for Ovumcy, backed by /api/v1/stats/overview."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
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
class OvumcySensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[OvumcySensorEntityDescription, ...] = (
    OvumcySensorEntityDescription(
        key="current_cycle_day",
        translation_key="current_cycle_day",
        icon="mdi:calendar-clock",
        value_fn=lambda d: d.get("current_cycle_day"),
    ),
    OvumcySensorEntityDescription(
        key="current_phase",
        translation_key="current_phase",
        icon="mdi:progress-clock",
        device_class="enum",
        options=["menstrual", "follicular", "ovulation", "luteal", "unknown"],
        value_fn=lambda d: d.get("current_phase"),
    ),
    OvumcySensorEntityDescription(
        key="current_fertility",
        translation_key="current_fertility",
        icon="mdi:egg",
        device_class="enum",
        options=["fertile", "not_fertile", "unknown"],
        value_fn=lambda d: d.get("current_fertility"),
    ),
    OvumcySensorEntityDescription(
        key="next_period_start",
        translation_key="next_period_start",
        icon="mdi:calendar-arrow-right",
        device_class="date",
        value_fn=lambda d: d.get("next_period_start"),
    ),
    OvumcySensorEntityDescription(
        key="ovulation_date",
        translation_key="ovulation_date",
        icon="mdi:calendar-star",
        device_class="date",
        value_fn=lambda d: d.get("ovulation_date"),
    ),
    OvumcySensorEntityDescription(
        key="fertility_window_start",
        translation_key="fertility_window_start",
        icon="mdi:calendar-start",
        device_class="date",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("fertility_window_start"),
    ),
    OvumcySensorEntityDescription(
        key="fertility_window_end",
        translation_key="fertility_window_end",
        icon="mdi:calendar-end",
        device_class="date",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("fertility_window_end"),
    ),
    OvumcySensorEntityDescription(
        key="average_cycle_length",
        translation_key="average_cycle_length",
        icon="mdi:chart-bell-curve",
        native_unit_of_measurement="d",
        state_class="measurement",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("average_cycle_length"),
    ),
    OvumcySensorEntityDescription(
        key="luteal_phase",
        translation_key="luteal_phase",
        icon="mdi:calendar-minus",
        native_unit_of_measurement="d",
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("luteal_phase"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: OvumcyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OvumcySensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class OvumcySensor(CoordinatorEntity[OvumcyDataUpdateCoordinator], SensorEntity):
    """A single stats field from /api/v1/stats/overview."""

    entity_description: OvumcySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OvumcyDataUpdateCoordinator,
        entry: ConfigEntry,
        description: OvumcySensorEntityDescription,
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
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})
