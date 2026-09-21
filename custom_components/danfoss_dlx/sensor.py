"""Sensor platform for the Danfoss DLX integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DlxConfigEntry
from .const import DOMAIN, SENSOR_TYPES, DlxSensorDescription
from .coordinator import DlxDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DlxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Danfoss DLX sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        DlxSensor(coordinator, entry.entry_id, description) for description in SENSOR_TYPES
    )


class DlxSensor(CoordinatorEntity[DlxDataUpdateCoordinator], SensorEntity):
    """A single Danfoss DLX data point."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DlxDataUpdateCoordinator,
        entry_id: str,
        description: DlxSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

        system_info = coordinator.system_info
        model = system_info.name.split(" - ")[-1] if " - " in system_info.name else "DLX"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            manufacturer="Danfoss",
            model=model,
            name=system_info.name,
        )

    @property
    def native_value(self):
        return self.coordinator.data.get(self.entity_description.key)
