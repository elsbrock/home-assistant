"""The cowboy integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from cowboybike import Cowboy

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR]  # , Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up cowboy from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Creating the class
    # TODO 1. Create API instance
    # TODO 2. Validate the API connection (and authentication)
    cowboy_api = await hass.async_add_executor_job(
        Cowboy.with_auth, entry.data["username"], entry.data["password"]
    )
    coordinator = CowboyCoordinator(hass, cowboy_api)

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    # TODO 3. Store an API object for your platforms to access
    hass.data[DOMAIN][entry.entry_id] = cowboy_api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class CowboyCoordinator(DataUpdateCoordinator):
    """Cowboy data update coordinator."""

    def __init__(self, hass: HomeAssistant, cowboy_api) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.cowboy_api = cowboy_api

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            await self.hass.async_add_executor_job(self.cowboy_api.refreshData)
        except KeyError:
            raise UpdateFailed("Unable to fetch data from Cowboy API")  # noqa: TRY200
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        #     raise UpdateFailed(f"Error communicating with API: {err}")
