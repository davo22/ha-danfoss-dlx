"""The Danfoss DLX solar inverter integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DlxApiClient, DlxSystemInfo
from .const import DOMAIN
from .coordinator import DlxDataUpdateCoordinator

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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DlxConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
