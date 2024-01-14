"""
Support for Denon Network Receivers.

Based off:
https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/components/media_player/denon.py
https://github.com/joopert/nad_receiver/blob/master/nad_receiver/__init__.py 

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.denon/
"""
import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity, PLATFORM_SCHEMA)

from homeassistant.components.media_player.const import MediaPlayerEntityFeature

from homeassistant.const import (
    CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Denon232 Receiver'

SUPPORT_DENON = MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP | \
    MediaPlayerEntityFeature.VOLUME_MUTE | MediaPlayerEntityFeature.TURN_ON | \
    MediaPlayerEntityFeature.TURN_OFF | MediaPlayerEntityFeature.SELECT_SOURCE | \
    MediaPlayerEntityFeature.SELECT_SOUND_MODE

SUPPORT_DENON_ZONE = MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP | \
    MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF | \
    MediaPlayerEntityFeature.SELECT_SOURCE

CONF_SERIAL_PORT = 'serial_port'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SERIAL_PORT): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

NORMAL_INPUTS = {'CD': 'CD', 'DVD': 'DVD', 'TV': 'TV', 'Video Aux': 'V.AUX', 'DBS':'DBS/SAT',
                 'Phono': 'PHONO', 'Tuner': 'TUNER', 'VDP': 'VDP', 'VCR-1': 'VCR-1', 'VCR-2': 'VCR-2',
                 'CDR/Tape': 'CDR/TAPE1'}
SOUND_MODES = {'Stereo': 'STEREO', 'Direct': 'DIRECT', 'Pure Direct': 'PURE DIRECT',
               'Dolby Digital': 'DOLBY DIGITAL', 'DTS Surround': 'DTS SURROUND', 'Rock Arena': 'ROCK ARENA',
               'Jazz Club': 'JAZZ CLUB', 'Mono Movie': 'MONO MOVIE', 'Matrix': 'MATRIX',
               'Video Game': 'VIDEO GAME', 'Virtual': 'VIRTUAL', 'Multi-channel Stereo': '5CH STEREO'}

# Sub-modes of 'NET/USB'
# {'USB': 'USB', 'iPod Direct': 'IPD', 'Internet Radio': 'IRP',
#  'Favorites': 'FVP'}

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Denon232 platform."""
    from .denon232_receiver import Denon232Receiver

    receiver = Denon232Receiver(config.get(CONF_SERIAL_PORT))
    # Add receiver and configured zones
    add_devices(
        [Denon232Device(
            config.get(CONF_NAME), receiver
        ),
        Denon232Zone(
            f"{config.get(CONF_NAME)} Zone 2", receiver, 'Z2'
        ),
        Denon232Zone(
            f"{config.get(CONF_NAME)} Zone 3", receiver, 'Z1'
        )
        ]
    )

class Denon232Device(MediaPlayerEntity):
    """Representation of a Denon device."""
        
    def __init__(self, name, denon232_receiver):
        """Initialize the Denon Receiver device."""
        self._name = name
        self._pwstate = 'PWSTANDBY'
        self._volume = 0
        # Initial value 60dB, changed if we get a MVMAX
        self._volume_max = 60
        self._source_list = NORMAL_INPUTS.copy()
        self._sound_mode_list = SOUND_MODES.copy()
        self._mediasource = ''
        self._denon_sound_mode = ''
        self._muted = False
        self._denon232_receiver = denon232_receiver

    def update(self):
        """Get the latest details from the device."""

        self._pwstate = self._denon232_receiver.serial_command('PW?', response=True)
        
        for line in self._denon232_receiver.serial_command('MV?', response=True, all_lines=True):
            if line.startswith('MVMAX '):
                # only grab two digit max, don't care about any half digit
                self._volume_max = int(line[len('MVMAX '):len('MVMAX XX')])
                _LOGGER.debug("MVMAX Value Saved: %s", self._volume_max)
                continue
            if line.startswith('MV'):
                self._volume = int(line[len('MV'):len('MVXX')])
                if self._volume == 99:
                    self._volume = 0
                _LOGGER.debug("MV Value Saved: %s", self._volume)
        self._muted = (self._denon232_receiver.serial_command('MU?', response=True) == 'MUON')
        self._mediasource = self._denon232_receiver.serial_command('SI?', response=True)[len('SI'):]
        self._denon_sound_mode = self._denon232_receiver.serial_command('MS?', response=True)[len('MS'):]

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        if self._pwstate == 'PWSTANDBY':
            return STATE_OFF
        else:
            return STATE_ON

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
        self._denon232_receiver.serial_command('PWON')
        
    async def async_turn_off(self):
        """Turn off media player."""
        self._denon232_receiver.serial_command('PWSTANDBY')

    def volume_up(self):
        """Volume up media player."""
        self._denon232_receiver.serial_command('MVUP')

    def volume_down(self):
        """Volume down media player."""
        self._denon232_receiver.serial_command('MVDOWN')

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self._denon232_receiver.serial_command('MV' +
                            str(round(volume * self._volume_max)).zfill(2))

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self._denon232_receiver.serial_command('MU' + ('ON' if mute else 'OFF'))

    def select_source(self, source):
        """Select input source."""
        self._denon232_receiver.serial_command('SI' + self._source_list.get(source))

    def select_sound_mode(self, sound_mode):
        """Select sound mode."""
        self._denon232_receiver.serial_command('MS' + self._sound_mode_list.get(sound_mode))

class Denon232Zone(MediaPlayerEntity):
    """Representation of a Denon Zone."""
    def __init__(self, name, denon232_receiver, zone_identifier):
        """Initialize the Denon Receiver Zone."""
        self._name = name
        self._zid = zone_identifier
        self._pwstate = f'{self._zid}OFF'
        self._volume = 0
        # Initial value 60dB, changed if we get a MVMAX
        self._volume_max = 60
        self._source_list = NORMAL_INPUTS.copy()
        self._mediasource = ''
        self._denon232_receiver = denon232_receiver
    
    def update(self):
        """Get the latest details from the zone."""
        self._pwstate = self._denon232_receiver.serial_command(f'{self._zid}?', response=True)

    @property
    def name(self):
        """Return the name of the zone."""
        return self._name

    @property
    def state(self):
        """Return the state of the zone."""
        if self._pwstate == f'{self._zid}OFF':
            return STATE_OFF
        else:
            return STATE_ON

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume / self._volume_max

    @property
    def source_list(self):
        """Return the list of available input sources."""
        return sorted(list(self._source_list.keys()))

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_DENON_ZONE

    @property
    def source(self):
        """Return the current input source."""
        for pretty_name, name in self._source_list.items():
            if self._mediasource == name:
                return pretty_name

    async def async_turn_on(self):
        """Turn the media player zone on."""
        self._denon232_receiver.serial_command(f'{self._zid}ON')
        
    async def async_turn_off(self):
        """Turn off media player."""
        self._denon232_receiver.serial_command(f'{self._zid}OFF')

    def volume_up(self):
        """Volume up media player."""
        self._denon232_receiver.serial_command(f'{self._zid}UP')

    def volume_down(self):
        """Volume down media player."""
        self._denon232_receiver.serial_command(f'{self._zid}DOWN')

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self._denon232_receiver.serial_command(f'{self._zid}' +
                            str(round(volume * self._volume_max)).zfill(2))

    def select_source(self, source):
        """Select input source."""
        self._denon232_receiver.serial_command(f'{self._zid}' + self._source_list.get(source))