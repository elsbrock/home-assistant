"""Module to handle device registration."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, async_get as async_get_device_registry
from .const import DOMAIN

async def register_device(hass: HomeAssistant, config_entry_id: str, device_info: dict):
    """Register the Omada EAP with Home Assistant.

    :param hass: HomeAssistant instance
    :param device_info: Dictionary containing device information
    """
    device_registry = async_get_device_registry(hass)

    access_point_mac = (
        device_info.get("mac", "unknown").lower().replace(":", "").replace("-", "")
    )
    device_registry.async_get_or_create(
        config_entry_id=config_entry_id,
        connections={(CONNECTION_NETWORK_MAC, access_point_mac)},
        identifiers={(DOMAIN, access_point_mac)},  # Use unique_id here
        name=device_info.get("deviceName", "Omada Access Point"),
        manufacturer="TP-Link",
        model=device_info.get("deviceModel", "Omada Device"),
        sw_version=device_info.get("firmwareVersion", "Unknown"),
        hw_version=device_info.get("hardwareVersion", "Unknown"),
    )
    return access_point_mac
