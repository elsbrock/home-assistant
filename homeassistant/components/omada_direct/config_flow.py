# custom_components/omada_direct/config_flow.py

"""Config flow for Omada EAP integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .client import OmadaClient, LoginError, FetchDataError, LogoutError  # Correct import

_LOGGER = logging.getLogger(__name__)

# Define the data schema for user input
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]

    # prepend the protocol if it's missing
    if not host.startswith(("http://", "https://")):
        host = "https://" + host
        data[CONF_HOST] = host

    # Initialize a temporary OmadaClient for validation
    temp_client = OmadaClient(
        host=host,
        username=username,
        password=password,
        ssl_verify=False,  # Adjust if you have SSL verification
        logger=_LOGGER  # Use Home Assistant's logger
    )

    try:
        await temp_client.connect()  # Establish the HTTP session
        await temp_client.login()    # Attempt to log in

    except LoginError as e:
        _LOGGER.error(f"Login failed: {e}")
        raise InvalidAuth from e
    except FetchDataError as e:
        _LOGGER.error(f"Failed to fetch data during validation: {e}")
        raise CannotConnect from e
    except Exception as e:
        _LOGGER.exception("Unexpected error during validation")
        raise CannotConnect from e
    finally:
        await temp_client.close()  # Ensure the temporary session is closed

    # If login is successful, return a title for the config entry
    return {"title": host}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Omada EAP."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL  # Adjust based on your integration's connection type

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # Catch any other unexpected exceptions
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"
            else:
                # If validation is successful, create the config entry
                return self.async_create_entry(title=info["title"], data=user_input)

        # Show the form to the user for input
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
