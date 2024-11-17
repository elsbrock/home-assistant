# custom_components/omada_direct/__init__.py

"""The Omada EAP integration."""
from __future__ import annotations

import logging

from homeassistant.components.omada_direct.device import register_device
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .client import FetchDataError, LoginError, LogoutError, OmadaClient
from .const import DOMAIN
from .coordinator import OmadaClientUpdateCoordinator

# Define the platforms that you want to support
PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]

# Initialize the logger
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Omada EAP from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Extract configuration data
    host = entry.data.get(CONF_HOST)
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    # Initialize the OmadaClient with the configuration data
    client = OmadaClient(
        host=host,
        username=username,
        password=password,
        ssl_verify=False,  # Adjust if you have SSL verification
        logger=_LOGGER,  # Pass Home Assistant's logger
    )

    try:
        await client.connect()  # Establish the HTTP session
        await client.login()  # Attempt to log in

        # Register the Omada EAP
        access_point_response = await client.fetch_device_info()
        access_point_info = access_point_response.get("data", {})
        access_point_mac = await register_device(hass, entry.entry_id, access_point_info)
    except (LoginError, FetchDataError) as e:
        _LOGGER.error(f"Failed to set up Omada EAP integration: {e}")
        return False
    except Exception:
        _LOGGER.exception("An unexpected error occurred during setup")
        return False
    finally:
        await client.logout()
        await client.close()

    # Initialize the ClientUpdateCoordinator
    coordinator = OmadaClientUpdateCoordinator(hass, client, access_point_mac)

    # Store the coordinator instance in hass.data for access by platforms
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug("OmadaClientUpdateCoordinator instance stored in hass.data")

    # Start the coordinator's update loop
    await coordinator.async_config_entry_first_refresh()

    # Forward the setup to the supported platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload the platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Remove the coordinator instance from hass.data
        hass.data[DOMAIN].pop(
            entry.entry_id
        )
        _LOGGER.debug("OmadaClientUpdateCoordinator instance removed from hass.data")

    return unload_ok
