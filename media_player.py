import voluptuous as vol
from datetime import timedelta
import logging

from homeassistant.components.media_player import (MediaPlayerEntity, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import MediaPlayerEntityFeature
from homeassistant.const import (CONF_NAME, STATE_OFF, STATE_ON)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.device_registry import DeviceInfo
import homeassistant.helpers.config_validation as cv

from .denon232_receiver import Denon232Receiver
from .const import (DOMAIN, CONF_ZONES, CONF_DEVICE, CONF_NAME, RECEIVER_INPUTS, SOUND_MODES, LOGGER)
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

SIGNAL_DENON_UPDATE = "denon_update"

# Default refresh interval (seconds)
DEFAULT_REFRESH_INTERVAL = 60

SUPPORT_DENON_ZONE = (
    MediaPlayerEntityFeature.VOLUME_SET | 
    MediaPlayerEntityFeature.VOLUME_STEP | 
    MediaPlayerEntityFeature.TURN_ON | 
    MediaPlayerEntityFeature.TURN_OFF | 
    MediaPlayerEntityFeature.SELECT_SOURCE
)

SUPPORT_DENON = (
    SUPPORT_DENON_ZONE | 
    MediaPlayerEntityFeature.VOLUME_MUTE | 
    MediaPlayerEntityFeature.SELECT_SOUND_MODE | 
    MediaPlayerEntityFeature.PLAY_MEDIA
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Denon AVR entities from config entry."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    receiver = Denon232Receiver(config[CONF_DEVICE])
    
    entities = []
    main_entity = Denon232Device(config[CONF_NAME], config_entry.unique_id, receiver, hass)
    entities.append(main_entity)
    
    # Set up zone entities
    for zone in config[CONF_ZONES]:
        entities.append(Denon232Zone(
            f"{config[CONF_NAME]} {zone['zone_name']}", 
            config_entry.unique_id, 
            receiver, 
            zone["zone_id"], 
            hass
        ))
    
    async_add_entities(entities)

class Denon232Device(MediaPlayerEntity):
    """Representation of a Denon AVR device."""
    
    def __init__(self, name, unique_id, receiver, hass):
        """Initialize the device."""
        super().__init__()
        self._attr_unique_id = unique_id
        self._name = name
        self._denon232_receiver = receiver
        self._hass = hass
        
        # Flag to track when a full refresh is needed
        self._full_refresh_needed = True
        
        # Track periodic refresh registration
        self._refresh_unsub = None
        
        # Initialize state from cached values
        self._initialize_from_cache()
        
        # Connect the update signal
        async_dispatcher_connect(self._hass, SIGNAL_DENON_UPDATE, self._handle_denon_update)
    
    async def async_added_to_hass(self):
        """Set up the entity when added to hass."""
        await super().async_added_to_hass()
        
        # Set up periodic refresh
        self._refresh_unsub = async_track_time_interval(
            self.hass, 
            self._handle_periodic_refresh,
            timedelta(seconds=DEFAULT_REFRESH_INTERVAL)
        )
    
    async def async_will_remove_from_hass(self):
        """Clean up when entity is removed."""
        await super().async_will_remove_from_hass()
        
        # Cancel periodic refresh
        if self._refresh_unsub:
            self._refresh_unsub()
            self._refresh_unsub = None
    
    def _initialize_from_cache(self):
        """Initialize state values from the receiver cache."""
        state = self._denon232_receiver.state
        self._pwstate = state['power']
        self._volume = state['volume']
        self._volume_max = state['volume_max']
        self._muted = state['muted']
        self._mediasource = state['source'] 
        self._denon_sound_mode = state['sound_mode']
        self._source_list = RECEIVER_INPUTS.copy()
        self._sound_mode_list = SOUND_MODES.copy()
    
    async def _handle_denon_update(self):
        """Handle external update signal."""
        self._full_refresh_needed = True
        await self.async_update_ha_state()
    
    async def _handle_periodic_refresh(self, _now=None):
        """Handle periodic state refresh."""
        # Request a full state refresh from the device
        LOGGER.debug("Performing periodic state refresh")
        self._full_refresh_needed = True
        
        # Refresh state from receiver
        await self.hass.async_add_executor_job(self._denon232_receiver.initialize_state)
        
        # Update HA state
        await self.async_update_ha_state()
    
    async def async_update(self):
        """Update state from the receiver cache."""
        if self._full_refresh_needed:
            LOGGER.debug("Refreshing device state from cache")
            self._initialize_from_cache()
            self._full_refresh_needed = False
    
    @property
    def device_info(self):
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self.name,
            manufacturer="Denon",
        )
    
    @property
    def name(self):
        """Return the name of the device."""
        return self._name
    
    @property
    def state(self):
        """Return the state of the device."""
        return STATE_ON if self._pwstate == 'PWON' else STATE_OFF
    
    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume / self._volume_max
    
    @property
    def is_volume_muted(self):
        """Return boolean if volume is currently muted."""
        return self._muted
    
    @property
    def source_list(self):
        """Return the list of available input sources."""
        return sorted(list(self._source_list.keys()))
    
    @property
    def sound_mode_list(self):
        """Return the list of available sound modes."""
        return sorted(list(self._sound_mode_list.keys()))
    
    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_DENON
    
    @property
    def source(self):
        """Return the current input source."""
        for pretty_name, name in self._source_list.items():
            if self._mediasource == name:
                return pretty_name
        return None
    
    @property
    def sound_mode(self):
        """Return the current sound mode."""
        for pretty_name, name in self._sound_mode_list.items():
            if self._denon_sound_mode == name:
                return pretty_name
        return None
    
    async def async_turn_on(self):
        """Turn the media player on."""
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, 'PWON')
        # State is updated in the receiver, refresh our local copy
        self._pwstate = self._denon232_receiver.state['power']
        self.async_write_ha_state()
    
    async def async_turn_off(self):
        """Turn off media player."""
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, 'PWSTANDBY')
        # State is updated in the receiver, refresh our local copy
        self._pwstate = self._denon232_receiver.state['power']
        self.async_write_ha_state()
    
    async def async_volume_up(self):
        """Volume up media player asynchronously."""
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, 'MVUP')
        # State is updated in the receiver, refresh our local copy
        self._volume = self._denon232_receiver.state['volume']
        LOGGER.debug("Volume up pressed. New volume level: %s", self._volume)
        self.async_write_ha_state()
    
    async def async_volume_down(self):
        """Volume down media player asynchronously."""
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, 'MVDOWN')
        # State is updated in the receiver, refresh our local copy
        self._volume = self._denon232_receiver.state['volume']
        LOGGER.debug("Volume down pressed. New volume level: %s", self._volume)
        self.async_write_ha_state()
    
    async def async_set_volume_level(self, volume):
        """Set volume level asynchronously."""
        absolute_volume = round(volume * self._volume_max)
        command = 'MV' + str(absolute_volume).zfill(2)
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, command)
        # State is updated in the receiver, refresh our local copy
        self._volume = self._denon232_receiver.state['volume']
        LOGGER.debug("Volume Level Set: %s", self._volume)
        self.async_write_ha_state()
    
    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player asynchronously."""
        command = 'MU' + ('ON' if mute else 'OFF')
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, command)
        # State is updated in the receiver, refresh our local copy
        self._muted = self._denon232_receiver.state['muted']
        self.async_write_ha_state()
    
    async def async_select_source(self, source):
        """Select input source asynchronously."""
        command = 'SI' + self._source_list.get(source)
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, command)
        # State is updated in the receiver, refresh our local copy
        self._mediasource = self._denon232_receiver.state['source']
        self.async_write_ha_state()
    
    async def async_select_sound_mode(self, sound_mode):
        """Select sound mode asynchronously."""
        command = self._sound_mode_list.get(sound_mode)
        if command:
            await self.hass.async_add_executor_job(
                self._denon232_receiver.serial_command, f'MS{command}'
            )
            # State is updated in the receiver, refresh our local copy
            self._denon_sound_mode = self._denon232_receiver.state['sound_mode']
            self.async_write_ha_state()
        else:
            LOGGER.error(f'Invalid sound mode selected: {sound_mode}')
    
    async def async_play_media(self, media_type, media_id, **kwargs):
        """Play radio station by preset number or frequency asynchronously."""
        if self.source == 'Tuner':
            if media_type.lower() == "channel" and len(media_id) >= 2:
                valid_prefix = media_id[0] in ['A', 'B', 'C', 'D', 'E', 'F', 'G']
                valid_number = media_id[1].isdigit() and 0 <= int(media_id[1]) <= 8
                if valid_prefix and valid_number:
                    await self.hass.async_add_executor_job(
                        self._denon232_receiver.serial_command, 'TP' + media_id
                    )
                elif media_id.isdigit() and 8800 <= int(media_id) <= 10800:
                    await self.hass.async_add_executor_job(
                        self._denon232_receiver.serial_command, 'TF' + media_id.zfill(6)
                    )
            self.async_write_ha_state()

class Denon232Zone(MediaPlayerEntity):
    """Representation of a Denon Zone."""
    
    def __init__(self, name, unique_id, denon232_receiver, zone_identifier, hass):
        """Initialize the Denon Receiver Zone."""
        super().__init__()
        self._attr_unique_id = f'{unique_id}_{zone_identifier}'
        self._name = name
        self._zid = zone_identifier
        self._denon232_receiver = denon232_receiver
        self._hass = hass
        
        # Flag to track when a full refresh is needed
        self._full_refresh_needed = True
        
        # Initialize state from cached values
        self._initialize_from_cache()
        
        # Connect the update signal
        async_dispatcher_connect(self._hass, SIGNAL_DENON_UPDATE, self._handle_denon_update)
    
    def _initialize_from_cache(self):
        """Initialize state values from the receiver cache."""
        zone_state = self._denon232_receiver.state['zones'].get(self._zid, {})
        
        if zone_state:
            self._pwstate = f"{self._zid}{'ON' if zone_state.get('power') == 'ON' else 'OFF'}"
            self._volume = zone_state.get('volume', 0)
            self._volume_max = 60  # Default value, specific to zones
            self._mediasource = zone_state.get('source', '')
        else:
            # Default values if zone not in cache
            self._pwstate = f'{self._zid}OFF'
            self._volume = 0
            self._volume_max = 60
            self._mediasource = ''
        
        self._source_list = RECEIVER_INPUTS.copy()
    
    async def _handle_denon_update(self):
        """Handle external update signal."""
        self._full_refresh_needed = True
        await self.async_update_ha_state()
    
    async def async_update(self):
        """Update zone state from the receiver cache."""
        if self._full_refresh_needed:
            LOGGER.debug(f"Refreshing zone {self._zid} state from cache")
            self._initialize_from_cache()
            self._full_refresh_needed = False
    
    @property
    def device_info(self):
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self.name,
            manufacturer="Denon",
            via_device=(DOMAIN),
        )
    
    @property
    def name(self):
        """Return the name of the zone."""
        return self._name
    
    @property
    def state(self):
        """Return the state of the zone."""
        return STATE_OFF if self._pwstate.endswith('OFF') else STATE_ON
    
    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume / self._volume_max
    
    @property
    def source_list(self):
        """Return the list of available input sources."""
        return sorted(self._source_list.keys())
    
    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_DENON_ZONE
    
    @property
    def source(self):
        """Return the current input source."""
        return next(
            (pretty_name for pretty_name, name in self._source_list.items() 
             if self._mediasource == name), 
            None
        )
    
    async def async_turn_on(self):
        """Turn the media player zone on asynchronously."""
        await self._hass.async_add_executor_job(
            self._denon232_receiver.serial_command, f'{self._zid}ON'
        )
        # Update internal state
        zone_state = self._denon232_receiver.state['zones'].get(self._zid, {})
        if zone_state:
            self._pwstate = f"{self._zid}{'ON' if zone_state.get('power') == 'ON' else 'OFF'}"
        else:
            self._pwstate = f'{self._zid}ON'  # Fallback
        self.async_write_ha_state()
    
    async def async_turn_off(self):
        """Turn off media player asynchronously."""
        await self._hass.async_add_executor_job(
            self._denon232_receiver.serial_command, f'{self._zid}OFF'
        )
        # Update internal state
        zone_state = self._denon232_receiver.state['zones'].get(self._zid, {})
        if zone_state:
            self._pwstate = f"{self._zid}{'ON' if zone_state.get('power') == 'ON' else 'OFF'}"
        else:
            self._pwstate = f'{self._zid}OFF'  # Fallback
        self.async_write_ha_state()
    
    async def async_volume_up(self):
        """Volume up media player asynchronously."""
        await self._hass.async_add_executor_job(
            self._denon232_receiver.serial_command, f'{self._zid}UP'
        )
        # Update internal state
        zone_state = self._denon232_receiver.state['zones'].get(self._zid, {})
        if zone_state:
            self._volume = zone_state.get('volume', self._volume)
        else:
            self._volume = min(self._volume + 1, self._volume_max)  # Fallback
        self.async_write_ha_state()
    
    async def async_volume_down(self):
        """Volume down media player asynchronously."""
        await self._hass.async_add_executor_job(
            self._denon232_receiver.serial_command, f'{self._zid}DOWN'
        )
        # Update internal state
        zone_state = self._denon232_receiver.state['zones'].get(self._zid, {})
        if zone_state:
            self._volume = zone_state.get('volume', self._volume)
        else:
            self._volume = max(self._volume - 1, 0)  # Fallback
        self.async_write_ha_state()
    
    async def async_set_volume_level(self, volume):
        """Set volume level asynchronously, range 0..1."""
        command = f'{self._zid}{str(round(volume * self._volume_max)).zfill(2)}'
        await self._hass.async_add_executor_job(
            self._denon232_receiver.serial_command, command
        )
        # Update internal state
        zone_state = self._denon232_receiver.state['zones'].get(self._zid, {})
        if zone_state:
            self._volume = zone_state.get('volume', self._volume)
        else:
            self._volume = round(volume * self._volume_max)  # Fallback
        self.async_write_ha_state()
    
    async def async_select_source(self, source):
        """Select input source asynchronously."""
        command = f'{self._zid}{self._source_list.get(source)}'
        await self._hass.async_add_executor_job(
            self._denon232_receiver.serial_command, command
        )
        # Update internal state
        zone_state = self._denon232_receiver.state['zones'].get(self._zid, {})
        if zone_state:
            self._mediasource = zone_state.get('source', self._mediasource)
        else:
            self._mediasource = self._source_list.get(source, self._mediasource)  # Fallback
        self.async_write_ha_state()
