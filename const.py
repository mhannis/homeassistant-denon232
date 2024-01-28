"""Constants for the denon232 integration."""
import logging

LOGGER = logging.getLogger(__package__)

DOMAIN = 'denon232'

CONF_DEVICE = "serial_port"
CONF_NAME = "device_name"
CONF_ZONES = "device_zones"
CONF_ZONE_SETUP = "zone_setup"
CONF_ZONE_NAME = "zone_name"

RECEIVER_INPUTS = {'CD': 'CD', 'DVD': 'DVD', 'TV': 'TV', 'Video Aux': 'V.AUX', 'DBS':'DBS/SAT',
                 'Phono': 'PHONO', 'Tuner': 'TUNER', 'VDP': 'VDP', 'VCR-1': 'VCR-1', 'VCR-2': 'VCR-2',
                 'CDR/Tape': 'CDR/TAPE1'}
SOUND_MODES = {'Stereo': 'STEREO', 'Direct': 'DIRECT', 'Pure Direct': 'PURE DIRECT',
               'Dolby Digital': 'DOLBY DIGITAL', 'DTS Surround': 'DTS SURROUND', 'Rock Arena': 'ROCK ARENA',
               'Jazz Club': 'JAZZ CLUB', 'Mono Movie': 'MONO MOVIE', 'Matrix': 'MATRIX',
               'Video Game': 'VIDEO GAME', 'Virtual': 'VIRTUAL', 'Multi-channel Stereo': '5CH STEREO',
               'Classic Concert': 'CLASSIC CONCERT'}