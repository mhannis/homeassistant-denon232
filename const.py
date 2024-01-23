"""Constants for the denon232 integration."""

from homeassistant.components.media_player.const import MediaPlayerEntityFeature
from homeassistant.components.media_player import PLATFORM_SCHEMA
import voluptuous as vol

DOMAIN = 'denon232'

SUPPORT_DENON_ZONE = MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP | \
    MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF | \
    MediaPlayerEntityFeature.SELECT_SOURCE

SUPPORT_DENON = SUPPORT_DENON_ZONE | MediaPlayerEntityFeature.VOLUME_MUTE | \
    MediaPlayerEntityFeature.SELECT_SOUND_MODE | MediaPlayerEntityFeature.PLAY_MEDIA

CONF_DEVICE = "serial_port"
CONF_NAME = "device_name"
CONF_ZONES = "device_zones"
CONF_ZONE_SETUP = "zone_setup"
CONF_ZONE_NAME = "zone_name"

NORMAL_INPUTS = {'CD': 'CD', 'DVD': 'DVD', 'TV': 'TV', 'Video Aux': 'V.AUX', 'DBS':'DBS/SAT',
                 'Phono': 'PHONO', 'Tuner': 'TUNER', 'VDP': 'VDP', 'VCR-1': 'VCR-1', 'VCR-2': 'VCR-2',
                 'CDR/Tape': 'CDR/TAPE1'}
SOUND_MODES = {'Stereo': 'STEREO', 'Direct': 'DIRECT', 'Pure Direct': 'PURE DIRECT',
               'Dolby Digital': 'DOLBY DIGITAL', 'DTS Surround': 'DTS SURROUND', 'Rock Arena': 'ROCK ARENA',
               'Jazz Club': 'JAZZ CLUB', 'Mono Movie': 'MONO MOVIE', 'Matrix': 'MATRIX',
               'Video Game': 'VIDEO GAME', 'Virtual': 'VIRTUAL', 'Multi-channel Stereo': '5CH STEREO',
               'Classic Concert': 'CLASSIC CONCERT'}

# Sub-modes of 'NET/USB'
# {'USB': 'USB', 'iPod Direct': 'IPD', 'Internet Radio': 'IRP',
#  'Favorites': 'FVP'}