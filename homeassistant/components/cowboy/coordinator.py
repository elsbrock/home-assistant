"""Define a custom data update coordinator for Cowboy."""

import asyncio
from datetime import timedelta
import logging

from cowboybike import Cowboy

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


class CowboyUpdateCoordinator(DataUpdateCoordinator):
    """Cowboy coordinator to fetch data from the inofficial API at a set interval."""

    config_entry: ConfigEntry
    device_info: DeviceInfo

    def __init__(
        self, hass: HomeAssistant, cowboy_api: Cowboy, config_entry: ConfigEntry
    ) -> None:
        """Initialize the coordinator with the given API client."""
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=5)
        )
        _LOGGER.info("Initializing CowboyCoordinator")
        self.cowboy_api = cowboy_api
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.title,
            manufacturer=MANUFACTURER,
        )

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
        self.device_info["sw_version"] = bike.firmware_version
        # dump bike object as JSON
        _LOGGER.info(vars(bike))
        return vars(bike)

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


class CowboyCoordinatedEntity(CoordinatorEntity[CowboyUpdateCoordinator]):
    """Defines a base Cowboy entity."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CowboyUpdateCoordinator,
    ) -> None:
        """Initialize the coordinated Cowboy Device."""
        CoordinatorEntity.__init__(self, coordinator=coordinator)
        self._attr_device_info = coordinator.device_info
