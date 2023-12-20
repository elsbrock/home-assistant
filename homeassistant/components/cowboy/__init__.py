"""The cowboy integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from cowboybike import Cowboy

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_API, CONF_COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR]  # , Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up cowboy from a config entry."""
    cowboy_api = await hass.async_add_executor_job(
        Cowboy.with_auth, entry.data["username"], entry.data["password"]
    )
    cowboy_coordinator = CowboyUpdateCoordinator(hass, cowboy_api, entry)

    await cowboy_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_API: cowboy_api,
        CONF_COORDINATOR: cowboy_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class CowboyUpdateCoordinator(DataUpdateCoordinator):
    """Cowboy coordinator to fetch data from the inofficial API at a set interval."""

    def __init__(
        self, hass: HomeAssistant, cowboy_api: Cowboy, config_entry: ConfigEntry
    ) -> None:
        """Initialize the coordinator with the given API client."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=5),
        )
        _LOGGER.info("Initializing CowboyCoordinator")
        self.cowboy_api = cowboy_api

    async def _async_update_data(self) -> dict:
        """Fetch data from API endpoint."""
        try:
            _LOGGER.info("Fetching data from Cowboy API")
            async with asyncio.timeout(10):
                return await self.hass.async_add_executor_job(self.fetch_data)

            self._update_auth_token()

        except KeyError:
            raise UpdateFailed("Unable to fetch data from Cowboy API")  # noqa: TRY200
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        #     raise UpdateFailed(f"Error communicating with API: {err}")

    def fetch_data(self):
        """Fetch the data from the Cowboy API and return a flat dict with only needed sensor data."""
        self.cowboy_api.refreshData()
        bike = self.cowboy_api.getBike()
        _LOGGER.info("Fetched data from Cowboy API")
        return {"BIKE": bike}

    @callback
    def _update_auth_token(self):
        """Set the updated authentication token."""
        # updated_token = self.picnic_api_client.session.auth_token
        # if self.config_entry.data.get(CONF_ACCESS_TOKEN) != updated_token:
        #     # Create an updated data dict
        #     data = {**self.config_entry.data, CONF_ACCESS_TOKEN: updated_token}

        #     # Update the config entry
        #     self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        pass
