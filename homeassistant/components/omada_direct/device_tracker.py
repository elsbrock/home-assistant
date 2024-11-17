# device_tracker.py

import logging

from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OmadaClientUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, config_entry, async_add_entities: AddEntitiesCallback
):
    """Set up the Omada device tracker based on a config entry."""
    coordinator: OmadaClientUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    # Create client entities
    access_point_mac = coordinator.data.get("access_point_mac", None)
    clients = coordinator.data.get("clients", [])
    for client in clients:
        mac = client.get("MAC")
        if not mac:
            _LOGGER.warning(
                f"Client {client.get('hostname', 'Unknown')} does not have a MAC address. Skipping."
            )
            continue

        client_entity = OmadaClientEntity(coordinator, access_point_mac, client)
        entities.append(client_entity)

    async_add_entities(entities, True)


class OmadaClientEntity(CoordinatorEntity, ScannerEntity):
    """Representation of a connected client."""

    def __init__(self, coordinator, access_point_mac, client_info):
        """Initialize the client entity."""
        super().__init__(coordinator)
        self.client_info = client_info
        self.access_point_mac = access_point_mac

    @property
    def name(self):
        """Return the name of the client."""
        return self.client_info.get("hostname", self.unique_id)

    @property
    def unique_id(self):
        """Return a unique ID for the client."""
        mac = (
            self.client_info.get("MAC", "unknown")
            .lower()
            .replace(":", "")
            .replace("-", "")
        )
        return f"client_{mac}"

    @property
    def device_info(self):
        """Link the client entity to the access point device.
        By setting 'connections' to the access point's MAC, all clients are associated with the same device.
        """
        if self.access_point_mac and self.access_point_mac != "unknown":
            return DeviceInfo(
                identifiers={(DOMAIN, self.unique_id)},
                connections={
                    (CONNECTION_NETWORK_MAC, self.access_point_mac)
                },  # Associate with access point
            )
        else:
            _LOGGER.warning(f"Access point MAC is invalid for client {self.name}.")
            return DeviceInfo(
                identifiers=set(),
                connections=set(),
            )

    @property
    def is_connected(self):
        """Return if the client is connected."""
        return True  # Client is always connected if present in the response.

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return {
            "mac_address": self.client_info.get("MAC"),
            "ip_address": self.client_info.get("IP"),
            "ssid": self.client_info.get("SSID"),
            "rssi": self.client_info.get("RSSI"),
            "active_time": self.client_info.get("ActiveTime"),
            "download": self.client_info.get("Down"),
            "upload": self.client_info.get("Up"),
            # Add other client-specific attributes here
        }
