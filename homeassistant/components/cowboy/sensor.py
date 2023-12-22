"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import _LOGGER, CowboyUpdateCoordinator
from .const import ATTRIBUTION, CONF_COORDINATOR, DOMAIN


@dataclass
class CowboyRequiredKeysMixin:
    """Mixin for required keys."""

    data_type: Literal["data_type",]
    value_fn: Callable[[Any], StateType | datetime]


@dataclass
class CowboySensorEntityDescription(SensorEntityDescription, CowboyRequiredKeysMixin):
    """Describes Cowboy sensor entity."""

    entity_registry_enabled_default: bool = False


SENSOR_TYPES: tuple[CowboySensorEntityDescription, ...] = (
    CowboySensorEntityDescription(
        key="total_distance",
        translation_key="total_distance",
        native_unit_of_measurement="km",
        suggested_display_precision=0,
        icon="mdi:map-marker-distance",
        data_type="total_distance",
        value_fn=lambda bike: bike.total_distance or 0,
    ),
    CowboySensorEntityDescription(
        key="total_duration",
        translation_key="total_duration",
        native_unit_of_measurement="s",
        icon="mdi:clock-outline",
        data_type="total_duration",
        value_fn=lambda bike: bike.total_duration or 0,
    ),
    CowboySensorEntityDescription(
        key="total_co2_saved",
        translation_key="total_co2_saved",
        native_unit_of_measurement="g",
        icon="mdi:cloud-check",
        data_type="total_co2_saved",
        value_fn=lambda bike: bike.total_co2_saved or 0,
    ),
    CowboySensorEntityDescription(
        key="stolen",
        translation_key="stolen",
        icon="mdi:handcuffs",
        data_type="stolen",
        value_fn=lambda bike: bike.stolen or False,
    ),
    CowboySensorEntityDescription(
        key="state_of_charge",
        translation_key="state_of_charge",
        native_unit_of_measurement="%",
        icon="mdi:battery",
        data_type="state_of_charge",
        value_fn=lambda bike: bike.state_of_charge or 0,
    ),
    CowboySensorEntityDescription(
        key="state_of_charge_internal",
        translation_key="state_of_charge_internal",
        native_unit_of_measurement="%",
        icon="mdi:battery-outline",
        data_type="state_of_charge_internal",
        value_fn=lambda bike: bike.state_of_charge_internal or 0,
    ),
    CowboySensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        icon="mdi:chip",
        data_type="firmware_version",
        value_fn=lambda bike: bike.firmware_version or 0,
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
        CowboySensor(cowboy_coordinator, config_entry, description)
        for description in SENSOR_TYPES
    )


class CowboySensor(SensorEntity, CoordinatorEntity[CowboyUpdateCoordinator]):
    """Representation of a Cowboy Bike."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: CowboySensorEntityDescription

    def __init__(
        self,
        coordinator: CowboyUpdateCoordinator,
        config_entry: ConfigEntry,
        description: CowboySensorEntityDescription,
    ) -> None:
        """Initialize a Cowboy sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        self._attr_unique_id = f"{config_entry.unique_id}.{description.key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, cast(str, config_entry.unique_id))},
            manufacturer="Cowboy",
            model=config_entry.unique_id,
        )

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {}

        attrs["nickname"] = "fixme"
        attrs["device_id"] = "bike_id"
        attrs["firmware"] = "bike_firmware"

        return attrs

    @property
    def native_value(self) -> StateType | datetime:
        """Return the value reported by the sensor."""
        data_set = self.coordinator.data.get("BIKE")
        return self.entity_description.value_fn(data_set)
