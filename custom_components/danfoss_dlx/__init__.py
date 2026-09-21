"""The Danfoss DLX solar inverter integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .api import DlxApiClient, DlxSystemInfo
from .const import CONF_HISTORY_CUTOFF, DOMAIN, SERVICE_IMPORT_HISTORY
from .coordinator import DlxDataUpdateCoordinator
from .statistics import async_has_history, async_import_history, build_statistic_id

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

DlxConfigEntry = ConfigEntry[DlxDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: DlxConfigEntry) -> bool:
    """Set up Danfoss DLX from a config entry."""
    session = async_get_clientsession(hass)
    client = DlxApiClient(entry.data[CONF_HOST], session)

    system_info = DlxSystemInfo(
        name=entry.data["system_name"],
        system=entry.data["system"],
        system_type=entry.data["system_type"],
        nominal_power=entry.data["nominal_power"],
    )

    coordinator = DlxDataUpdateCoordinator(hass, entry, client, system_info)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)

    if not await async_has_history(hass, build_statistic_id(system_info)):
        entry.async_create_background_task(
            hass,
            _async_import(hass, entry, client, system_info),
            name="danfoss_dlx history import",
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: DlxConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_import(
    hass: HomeAssistant,
    entry: DlxConfigEntry,
    client: DlxApiClient,
    system_info: DlxSystemInfo,
) -> None:
    """Import the inverter's production history as long-term statistics.

    The cutoff is stored on the config entry and reused on every later import,
    so re-running this never overlaps the statistics the recorder builds from
    the live sensors.
    """
    cutoff_raw = entry.data.get(CONF_HISTORY_CUTOFF)
    cutoff = dt_util.parse_datetime(cutoff_raw) if cutoff_raw else None
    if cutoff is None:
        cutoff = dt_util.start_of_local_day()
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_HISTORY_CUTOFF: cutoff.isoformat()}
        )

    try:
        await async_import_history(hass, client, system_info, cutoff)
    except Exception:  # noqa: BLE001 - background task must not die silently
        _LOGGER.exception("Importing history from %s failed", entry.data[CONF_HOST])


def _async_register_services(hass: HomeAssistant) -> None:
    """Register the history import service once."""
    if hass.services.has_service(DOMAIN, SERVICE_IMPORT_HISTORY):
        return

    async def _handle_import(call: ServiceCall) -> None:
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            session = async_get_clientsession(hass)
            client = DlxApiClient(entry.data[CONF_HOST], session)
            system_info = DlxSystemInfo(
                name=entry.data["system_name"],
                system=entry.data["system"],
                system_type=entry.data["system_type"],
                nominal_power=entry.data["nominal_power"],
            )
            await _async_import(hass, entry, client, system_info)

    hass.services.async_register(DOMAIN, SERVICE_IMPORT_HISTORY, _handle_import)
