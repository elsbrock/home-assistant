from homeassistant.components.device_tracker.config_entry import (
    SourceType,
    TrackerEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LOCATION_NAME,
    ATTR_LONGITUDE,
    CONF_COORDINATOR,
    DOMAIN,
)
from .coordinator import _LOGGER, CowboyCoordinatedEntity, CowboyUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cowboy sensor entries."""
    cowboy_coordinator = hass.data[DOMAIN][config_entry.entry_id][CONF_COORDINATOR]
    async_add_entities([CowboyTracker(cowboy_coordinator)])


class CowboyTracker(CowboyCoordinatedEntity, TrackerEntity):
    """Cowboy device tracker."""

    _attr_force_update = False
    _attr_icon = "mdi:bike"
    _attr_name = None

    def __init__(
        self,
        coordinator: CowboyUpdateCoordinator,
    ) -> None:
        """Initialize the Tracker."""
        super().__init__(coordinator)
        self._attr_extra_state_attributes = {}
        self._attr_unique_id = coordinator.config_entry.title + "foo"
        self._attr_name = None

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self._attr_extra_state_attributes.get(ATTR_LATITUDE, None)

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self._attr_extra_state_attributes.get(ATTR_LONGITUDE, None)

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device.

        Value in meters.
        """
        return self._attr_extra_state_attributes.get(ATTR_ACCURACY, None)

    @property
    def location_name(self) -> str | None:
        """Return a location name for the current location of the device."""
        return self._attr_extra_state_attributes.get(ATTR_LOCATION_NAME, None)

    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_extra_state_attributes.update(
            {
                ATTR_LATITUDE: self.coordinator.data["position"]["latitude"],
                ATTR_LONGITUDE: self.coordinator.data["position"]["longitude"],
                ATTR_ACCURACY: self.coordinator.data["position"]["accuracy"],
                ATTR_LOCATION_NAME: self.coordinator.data["position"]["address"],
            }
        )
        self.async_write_ha_state()
