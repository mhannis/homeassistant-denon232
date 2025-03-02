"""Config flow for Denon232 integration."""
import voluptuous as vol

from homeassistant import config_entries

from .const import (
    DOMAIN,
    CONF_DEVICE,
    CONF_NAME,
    CONF_ZONES,
    CONF_ZONE_SETUP,
    CONF_ZONE_NAME,
    LOGGER
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

class Denon232ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Denon232 config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the Denon AVR flow."""
        self.device = None
        self.data = {}
        self.zones = []
        self.data[CONF_ZONES] = []

    def determine_zones(self):
        """Attempt to find the available zones and their identifiers."""
        LOGGER.debug("Determining available zones")
        zones = []
        
        # Try to detect Zone 2
        LOGGER.debug("Checking zone 2 capability")
        if len(self.device.serial_command('Z2?', response=True, all_lines=True, update_state=False)) > 0:
            zones.append('Z2')
            LOGGER.debug("Found zone 2 with zone id Z2")
        
        # Try to detect Zone 3 (or alternative Zone 1)
        LOGGER.debug("Checking zone 3 capability")
        if len(self.device.serial_command('Z3?', response=True, all_lines=True, update_state=False)) > 0:
            zones.append('Z3')
            LOGGER.debug("Found zone 3 with zone id Z3")
        elif len(self.device.serial_command('Z1?', response=True, all_lines=True, update_state=False)) > 0:
            zones.append('Z1')
            LOGGER.debug("Found zone 3 with zone id Z1")

        return zones

    async def async_step_user(self, user_input=None, errors=None):
        """Initial device setup flow upon user initiation."""
        if user_input is not None:
            if device := user_input[CONF_DEVICE]:
                try:
                    self.device = Denon232Receiver(device)
                    # Check if device is responsive and supports the protocol
                    response = self.device.serial_command('PW?', response=True, update_state=False)
                    
                    if response in ['PWSTANDBY', 'PWON']:
                        self.data[CONF_DEVICE] = device
                        return await self.async_step_setup()
                    else:
                        LOGGER.error(f"Unexpected response from device: {response}")
                        return await self.async_step_user(errors={"base": "not_supported"})
                except Exception as exc:
                    LOGGER.exception("Error connecting to device", exc_info=exc)
                    return await self.async_step_user(errors={"base": "connection_error"})

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_setup(self, user_input=None, errors=None):
        """Device configuration flow."""
        if user_input is not None:
            self.data[CONF_NAME] = user_input.get(CONF_NAME, "Denon232 Receiver")
            
            # Not exactly recommended, but we have _no_ way of automatically detecting
            # any device identifiers
            await self.async_set_unique_id(self.data[CONF_NAME])
            self._abort_if_unique_id_configured()

            # Discover zones
            self.zones = await self.hass.async_add_executor_job(self.determine_zones)
            
            if user_input.get(CONF_ZONE_SETUP, False) and self.zones:
                return await self.async_step_zone()
            else:
                return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)

        return self.async_show_form(step_id="setup", data_schema=SETUP_SCHEMA, errors=errors)

    async def async_step_zone(self, user_input=None, errors=None):
        """Zone configuration flow."""
        if user_input is not None:
            zone_name = user_input.get(CONF_ZONE_NAME, f"Zone {len(self.data[CONF_ZONES]) + 1}")
            
            self.data[CONF_ZONES].append({
                "zone_name": zone_name,
                "zone_id": self.zones[len(self.data[CONF_ZONES])]
            })
            
            LOGGER.debug(f"Added zone: {zone_name} with ID: {self.zones[len(self.data[CONF_ZONES]) - 1]}")

            if user_input.get(CONF_ZONE_SETUP, False) and len(self.zones) > len(self.data[CONF_ZONES]):
                return await self.async_step_zone()
            else:
                return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)

        return self.async_show_form(step_id="zone", data_schema=ZONE_SCHEMA, errors=errors)
