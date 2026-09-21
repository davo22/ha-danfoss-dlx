"""Config flow for the Danfoss DLX integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DlxApiClient, DlxApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class DlxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Danfoss DLX."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the inverter's IP address and validate it."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            session = async_get_clientsession(self.hass)
            client = DlxApiClient(host, session)
            try:
                system_info = await client.async_get_default_inverter()
            except DlxApiError:
                _LOGGER.debug("Cannot reach Danfoss DLX at %s", host, exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{host}:{system_info.system}:{system_info.system_type}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=system_info.name,
                    data={
                        CONF_HOST: host,
                        "system_name": system_info.name,
                        "system": system_info.system,
                        "system_type": system_info.system_type,
                        "nominal_power": system_info.nominal_power,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
