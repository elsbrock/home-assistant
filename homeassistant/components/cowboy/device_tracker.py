from
from homeassistant.components.device_tracker.config_entry import TrackerEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an entry."""
    component: EntityComponent[BaseTrackerEntity] | None = hass.data.get(DOMAIN)
    return await component.async_setup_entry(entry)


class CowboyTracker(TrackerEntity):
    pass
