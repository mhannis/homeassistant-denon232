import voluptuous as vol
from homeassistant.components.media_player import (MediaPlayerEntity, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import MediaPlayerEntityFeature
from homeassistant.const import (CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN)
from homeassistant.helpers.device_registry import DeviceInfo
import homeassistant.helpers.config_validation as cv
from .denon232_receiver import Denon232Receiver
from .const import (DOMAIN, CONF_ZONES, CONF_DEVICE, CONF_NAME, RECEIVER_INPUTS, SOUND_MODES, LOGGER)
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send

SIGNAL_DENON_UPDATE = "denon_update"

SUPPORT_DENON_ZONE = MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP | \
    MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF | \
    MediaPlayerEntityFeature.SELECT_SOURCE

SUPPORT_DENON = SUPPORT_DENON_ZONE | MediaPlayerEntityFeature.VOLUME_MUTE | \
    MediaPlayerEntityFeature.SELECT_SOUND_MODE | MediaPlayerEntityFeature.PLAY_MEDIA

async def async_setup_entry(hass, config_entry, async_add_entities):
    config = hass.data[DOMAIN][config_entry.entry_id]
    receiver = Denon232Receiver(config[CONF_DEVICE])
    entities = []
    main_entity = Denon232Device(config[CONF_NAME], config_entry.unique_id, receiver, hass)
    entities.append(main_entity)
    for zone in config[CONF_ZONES]:
        entities.append(Denon232Zone(f"{config[CONF_NAME]} {zone['zone_name']}", config_entry.unique_id, receiver, zone["zone_id"], hass))
    async_add_entities(entities)

class Denon232Device(MediaPlayerEntity):
    def __init__(self, name, unique_id, receiver, hass):
        super().__init__()
        self._attr_unique_id = unique_id
        self._name = name
        self._pwstate = 'PWSTANDBY'
        self._volume = 0
        self._muted = False
        self._volume_max = 80
        self._source_list = RECEIVER_INPUTS.copy()
        self._sound_mode_list = SOUND_MODES.copy()
        self._mediasource = ''
        self._denon_sound_mode = ''
        self._denon232_receiver = receiver
        self._hass = hass
        self._update_required = True
        # Connect the update signal
        async_dispatcher_connect(self._hass, SIGNAL_DENON_UPDATE, self._handle_denon_update)

    async def _handle_denon_update(self):
        """Handle the update signal."""
        self._update_required = True
        await self.async_update_ha_state()

    async def async_update(self):
        """Fetch new state data for this entity."""
        if self._update_required:
                # Fetch data from receiver (e.g., self._denon232_receiver.get_volume())
            self._pwstate = self._denon232_receiver.serial_command('PW?', response=True)
            for line in self._denon232_receiver.serial_command('MV?', response=True, all_lines=True):
                if line.startswith('MVMAX '):
                    # only grab two digit max, don't care about any half digit
                    self._volume_max = int(line[len('MVMAX '):len('MVMAX XX')])
                    LOGGER.debug("MVMAX Value Saved: %s", self._volume_max)
                    continue
                if line.startswith('MV'):
                    self._volume = int(line[len('MV'):len('MVXX')])
                    if self._volume == 99:
                        self._volume = 0
                    LOGGER.debug("MV Value Saved: %s", self._volume)
            self._muted = (self._denon232_receiver.serial_command('MU?', response=True) == 'MUON')
            self._mediasource = self._denon232_receiver.serial_command('SI?', response=True)[len('SI'):]
            self._denon_sound_mode = self._denon232_receiver.serial_command('MS?', response=True)[len('MS'):]
                # Update internal state based on fetched data
        self._update_required = False

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

    @property
    def sound_mode(self):
        """Return the current sound mode."""
        for pretty_name, name in self._sound_mode_list.items():
            if self._denon_sound_mode == name:
                return pretty_name

    async def async_turn_on(self):
        """Turn the media player on."""
        # Execute the command in the executor; simulate with 'PWON' command
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, 'PWON')

        # Optionally, directly update the entity's state if you're confident the command succeeded
        self._pwstate = 'PWON'
        # Notify the system that the entity's state has been updated
        self.async_write_ha_state()
        # Signal other entities to update their state as needed

    async def async_turn_off(self):
        """Turn off media player."""
        # Execute the command in the executor; simulate with 'PWON' command
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, 'PWSTANDBY')

        # Optionally, directly update the entity's state if you're confident the command succeeded
        self._pwstate = 'PWSTANDBY'

        # Notify the system that the entity's state has been updated
        self.async_write_ha_state()
        # Signal other entities to update their state as needed

    async def async_volume_up(self):
        """Volume up media player asynchronously."""
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, 'MVUP')
        receiver_volume = (self._volume * self._volume_max) / 100
        # Increment the receiver's volume by one step
        receiver_volume = min(receiver_volume + 1, self._volume_max)
        # Convert back to 0-100 scale for the slider
        self._volume = (receiver_volume / self._volume_max) * 100
        LOGGER.debug("Volume up pressed. New volume level (fraction): %s", self._volume)
        # Optionally, update any relevant states and notify as needed
        self.async_write_ha_state()

    async def async_volume_down(self):
        """Volume down media player asynchronously."""
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, 'MVDOWN')
        receiver_volume = (self._volume * self._volume_max) / 100
        receiver_volume = max(receiver_volume - 1, 0)
        self._volume = (receiver_volume / self._volume_max) * 100
        LOGGER.debug("Volume down pressed. New volume level (fraction): %s", self._volume)
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume):
        """Set volume level asynchronously"""
        absolute_volume = round(volume * self._volume_max)
        command = 'MV' + str(absolute_volume).zfill(2)
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, command)
        LOGGER.debug("Volume Level Set: %s", command)
        self._volume = absolute_volume
        # Optionally, update any relevant states and notify as needed
        self.async_write_ha_state()

    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player asynchronously."""
        command = 'MU' + ('ON' if mute else 'OFF')
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, command)
        # Optionally, update any relevant states and notify as needed
        self.async_write_ha_state()

    async def async_select_source(self, source):
        """Select input source asynchronously."""
        command = 'SI' + self._source_list.get(source)
        await self.hass.async_add_executor_job(self._denon232_receiver.serial_command, command)
        # Optionally, update any relevant states and notify as needed
        self.async_write_ha_state()

    async def async_select_sound_mode(self, sound_mode):
        """Select sound mode asynchronously."""
        command = self._sound_mode_list.get(sound_mode)
        if command:
            await self.hass.async_add_executor_job(
                self._denon232_receiver.serial_command, f'MS{command}'
            )
            # Optionally, update any relevant states and notify as needed
            self.async_write_ha_state()
        else:
            LOGGER.error(f'Invalid sound mode selected: {sound_mode}')
        # Assuming command_sent() updates some state or logs command sending

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
            # Optionally, update any relevant states and notify as needed
            self.async_write_ha_state()

class Denon232Zone(MediaPlayerEntity):
    """Representation of a Denon Zone."""

    def __init__(self, name, unique_id, denon232_receiver, zone_identifier, hass):
        """Initialize the Denon Receiver Zone."""
        super().__init__()
        self._attr_unique_id = f'{unique_id}_{zone_identifier}'
        self._name = name
        self._zid = zone_identifier
        self._pwstate = f'{self._zid}OFF'
        self._volume = 0
        self._volume_max = 60  # Initial value 60dB, can be changed if we get a MVMAX
        self._source_list = RECEIVER_INPUTS.copy()
        self._mediasource = ''
        self._denon232_receiver = denon232_receiver
        self._hass = hass

    async def async_update(self):
        """Fetch new state data for the zone asynchronously."""
        # Assuming `serial_command` can be modified to be async or run in executor
        lines = await self._hass.async_add_executor_job(
            self._denon232_receiver.serial_command, f'{self._zid}?', response=True, all_lines=True
        )
        for line in lines:
            if line.startswith(self._zid):
                if line.endswith('ON') or line.endswith('OFF'):
                    self._pwstate = line
                elif line[len(self._zid):].isdigit():
                    self._volume = int(line[len(self._zid):len(self._zid) + 2])
                    if self._volume == 99:
                        self._volume = 0
                    LOGGER.debug(f'{self._zid} Volume value Saved: {self._volume}')
                else:
                    self._mediasource = line[len(self._zid):]

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
        """Return the state of the device."""
        return STATE_OFF if self._pwstate == f'{self._zid}OFF' else STATE_ON

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
        return next((pretty_name for pretty_name, name in self._source_list.items() if self._mediasource == name), None)

    async def async_turn_on(self):
        """Turn the media player zone on asynchronously."""
        await self._hass.async_add_executor_job(self._denon232_receiver.serial_command, f'{self._zid}ON')
        self.async_write_ha_state()

    async def async_turn_off(self):
        """Turn off media player asynchronously."""
        await self._hass.async_add_executor_job(self._denon232_receiver.serial_command, f'{self._zid}OFF')
        self.async_write_ha_state()

    async def async_volume_up(self):
        """Volume up media player asynchronously."""
        await self._hass.async_add_executor_job(self._denon232_receiver.serial_command, f'{self._zid}UP')
        self.async_write_ha_state()

    async def async_volume_down(self):
        """Volume down media player asynchronously."""
        await self._hass.async_add_executor_job(self._denon232_receiver.serial_command, f'{self._zid}DOWN')
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume):
        """Set volume level asynchronously, range 0..1."""
        command = f'{self._zid}' + str(round(volume * self._volume_max)).zfill(2)
        await self._hass.async_add_executor_job(self._denon232_receiver.serial_command, command)
        self.async_write_ha_state()

    async def async_select_source(self, source):
        """Select input source asynchronously."""
        command = f'{self._zid}' + self._source_list.get(source)
        await self._hass.async_add_executor_job(self._denon232_receiver.serial_command, command)
        self.async_write_ha_state()
