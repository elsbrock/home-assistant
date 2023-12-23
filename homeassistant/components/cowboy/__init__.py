"""The cowboy integration."""
from __future__ import annotations

import logging

from cowboybike import Cowboy

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_API, CONF_COORDINATOR, DOMAIN
from .coordinator import CowboyUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
]


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
