import logging
import voluptuous as vol

from homeassistant import config_entries

from .const import (
    DOMAIN,
    CONF_DEVICE,
    CONF_NAME,
    CONF_ZONES,
    CONF_ZONE_SETUP,
    CONF_ZONE_NAME
)
from .denon232_receiver import Denon232Receiver

USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_DEVICE): str}
)

SETUP_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): str,
        vol.Optional(CONF_ZONE_SETUP): bool
    }
)

ZONE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ZONE_NAME): str,
        vol.Optional(CONF_ZONE_SETUP): bool
    }
)

_LOGGER = logging.getLogger(__name__)

class Denon232ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Denon232 config flow."""

    VERSION=1

    def __init__(self) -> None:
        """Initialize the Denon AVR flow."""
        self.device = None
        self.data = {}
        self.zones = []

    def determine_zones(self):
        """Attempt to find the available zones and their identifiers."""
        zones = []
        _LOGGER.debug("Checking zone 2 capability")
        if len(self.device.serial_command('Z2?', response=True, all_lines=True)) > 0:
            zones.append('Z2')
            _LOGGER.debug("Found zone 2 with zone id Z2")
        _LOGGER.debug("Checking zone 3 capability")
        if len(self.device.serial_command('Z3?', response=True, all_lines=True)) > 0:
            zones.append('Z3')
            _LOGGER.debug("Found zone 3 with zone id Z3")
        elif len(self.device.serial_command('Z1?', response=True, all_lines=True)) > 0:
            zones.append('Z1')
            _LOGGER.debug("Found zone 3 with zone id Z1")

        return zones

    async def async_step_user(self, user_input=None, errors=None):
        """Initial device setup flow upon user initiation."""
        if user_input is not None:
            if device := user_input[CONF_DEVICE]:
                self.device = Denon232Receiver(device)
                if self.device.serial_command('PW?', response=True) in ['PWSTANDBY', 'PWON']:
                    self.data[CONF_DEVICE] = device
                    return await self.async_step_setup()
                else:
                    return await self.async_step_user(errors={"base": "not_supported"})

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_setup(self, user_input=None, errors=None):
        """Device configuration flow."""

        if user_input is not None:
            self.data[CONF_NAME] = user_input.get(CONF_NAME, "Denon232 Receiver")

            # Discover zones
            self.zones = self.determine_zones()
            if user_input.get(CONF_ZONE_SETUP, False) and self.zones is not {}:
                self.data[CONF_ZONES] = []
                return await self.async_step_zone()

        return self.async_show_form(step_id="setup", data_schema=SETUP_SCHEMA, errors=errors)

    async def async_step_zone(self, user_input=None, errors=None):
        """Zone configuration flow."""

        if user_input is not None:
            self.data[CONF_ZONES].append(
                {
                    "zone_name": user_input.get(CONF_ZONE_NAME, "Zone " + str(len(self.data[CONF_ZONES]))),
                    "zone_id": self.zones[len(self.data[CONF_ZONES])]
                }
            )

            if user_input.get(CONF_ZONE_SETUP, False) and len(self.zones) > len(self.data[CONF_ZONES]):
                return await self.async_step_zone()
            else:
                return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)

        return self.async_show_form(step_id="zone", data_schema=ZONE_SCHEMA, errors=errors)