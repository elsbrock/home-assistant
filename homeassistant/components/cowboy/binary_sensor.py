"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_COORDINATOR, DOMAIN
from .coordinator import _LOGGER, CowboyCoordinatedEntity, CowboyUpdateCoordinator
from .sensor import CowboySensorEntityDescription

SENSOR_TYPES: tuple[CowboySensorEntityDescription, ...] = (
    CowboySensorEntityDescription(
        key="stolen",
        translation_key="stolen",
        icon="mdi:car-emergency",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cowboy sensor entries."""
    cowboy_coordinator = hass.data[DOMAIN][config_entry.entry_id][CONF_COORDINATOR]
    async_add_entities(
        CowboyBinarySensor(cowboy_coordinator, description)
        for description in SENSOR_TYPES
    )


class CowboyBinarySensor(CowboyCoordinatedEntity, BinarySensorEntity):
    """Representation of a Cowboy Bike."""

    entity_description: CowboySensorEntityDescription

    def __init__(
        self,
        coordinator: CowboyUpdateCoordinator,
        description: CowboySensorEntityDescription,
    ) -> None:
        """Initialize a Cowboy sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.entity_description.attrs(self.coordinator.data)
        self.async_write_ha_state()
