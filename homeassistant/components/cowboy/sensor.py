"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CowboyCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up an entry."""
    async_add_entities(
        [
            CowboySensor(hass, "total_distance", "map-marker-distance", "KM"),
            CowboySensor(hass, "total_duration", "clock-outline", "s"),
            CowboySensor(hass, "total_co2_saved", "cloud-check", "g"),
            CowboySensor(hass, "bike_total_distance", "map-marker-distance", "KM"),
            CowboySensor(hass, "bike_total_duration", "clock-outline", "s"),
            CowboySensor(hass, "bike_total_co2_saved", "cloud-check", "g"),
            CowboySensor(hass, "bike_state_of_charge", "battery", "%"),
            CowboySensor(hass, "bike_state_of_charge_internal", "battery", "%"),
        ],
        True,
    )


class CowboySensor(SensorEntity):
    """Representation of a Cowboy Bike."""

    def __init__(self, hass, name, icon, unit_of_measurement):
        """Initialize the sensor."""
        self._state = None
        self._icon = "mdi:" + icon
        self._unit_of_measurement = unit_of_measurement
        self._name = name

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._attr_native_value = 23
