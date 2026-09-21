"""Data update coordinator for the Danfoss DLX integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DlxApiClient, DlxApiError, DlxSystemInfo
from .const import DEFAULT_SCAN_INTERVAL, SENSOR_TYPES, DlxSensorDescription

_LOGGER = logging.getLogger(__name__)


def _build_path(enexus_id: str, system: int, system_type: int, extra: str | None) -> str:
    parts = [f"s:{system}", f"t:{system_type}"]
    if extra:
        parts.append(extra)
    return f"eNEXUS_{enexus_id}[{','.join(parts)}]"


class DlxDataUpdateCoordinator(DataUpdateCoordinator[dict[str, float | str | None]]):
    """Polls the inverter and parses raw eNEXUS values into sensor-ready values."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: DlxApiClient,
        system_info: DlxSystemInfo,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="danfoss_dlx",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.system_info = system_info
        self._paths = {
            description.key: _build_path(
                description.enexus_id,
                system_info.system,
                system_info.system_type,
                description.extra_path,
            )
            for description in SENSOR_TYPES
        }

    async def _async_update_data(self) -> dict[str, float | str | None]:
        try:
            raw = await self.client.async_read(
                [
                    (self._paths[description.key], description.datatype)
                    for description in SENSOR_TYPES
                ]
            )
        except DlxApiError as err:
            raise UpdateFailed(str(err)) from err

        return {
            description.key: _parse_value(raw.get(self._paths[description.key]), description)
            for description in SENSOR_TYPES
        }


def _parse_value(raw_value: str | None, description: DlxSensorDescription) -> float | str | None:
    if raw_value is None:
        return None
    try:
        number = int(raw_value)
    except ValueError:
        return raw_value or None

    if description.value_map is not None:
        return description.value_map.get(number)

    scaled = number / description.divisor
    return round(scaled, 3) if description.divisor != 1 else scaled
