from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .client import OmadaClient

_LOGGER = logging.getLogger(__name__)

class OmadaClientUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Omada data."""

    def __init__(self, hass, client: OmadaClient, access_point_mac: str):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Omada Client Coordinator",
            update_interval=timedelta(seconds=10),
        )
        self.client = client
        self.access_point_mac = access_point_mac
        self.clients_info = []

    async def _async_update_data(self):
        """Fetch data from Omada controller."""
        try:
            await self.client.ensure_authenticated()

            # Fetch clients info
            clients_response = await self.client.fetch_clients()
            self.clients_info = clients_response.get('data', [])

            return {
                'clients': self.clients_info,
                'access_point_mac': self.access_point_mac,
            }

        except Exception as e:
            raise UpdateFailed(f"Error fetching data: {e}") from e
