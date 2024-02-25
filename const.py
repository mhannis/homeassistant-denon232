"""Constants for the denon232 integration."""
import logging

LOGGER = logging.getLogger(__package__)

DOMAIN = 'denon232'

CONF_DEVICE = "serial_port"
CONF_NAME = "device_name"
CONF_ZONES = "device_zones"
CONF_ZONE_SETUP = "zone_setup"
CONF_ZONE_NAME = "zone_name"

RECEIVER_INPUTS = {
    "PHONO": "PHONO",
    "CD": "CD",
    "TUNER": "TUNER",
    "DVD": "DVD",
    "VDP": "VDP",
    "TV": "TV",
    "DBS/SAT": "DBS/SAT",
    "VCR-1": "VCR-1",
    "VCR-2": "VCR-2",
    "VCR-3": "VCR-3",
    "V.AUX": "V.AUX",
    "CDR/TAPE1": "CDR/TAPE1",
    "MD/TAPE2": "MD/TAPE2",
	}
SOUND_MODES = {
    "DIRECT": "DIRECT",
    "PURE DIRECT": "PURE DIRECT",
    "STEREO": "STEREO",
    "MULTI CH IN": "MULTI CH IN",
    "MULTI CH DIRECT": "MULTI CH DIRECT",
    "MULTI CH PURE DIRECT": "MULTI CH PURE D",
    "DOLBY PRO LOGIC": "DOLBY PRO LOGIC",
    "DOLBY PL2": "DOLBY PL2",
    "DOLBY PL2X": "DOLBY PL2X",
    "DOLBY DIGITAL": "DOLBY DIGITAL",
    "DOLBY D EX": "DOLBY D EX",
    "DTS NEO:6": "DTS NEO:6",
    "DTS SURROUND": "DTS SURROUND",
    "DTS ES DISCRETE 6.1": "DTS ES DSCRT6.1",
    "DTS ES MATRIX 6.1": "DTS ES MTRX6.1",
    "THX CINEMA": "THX CINEMA",
    "THX SURROUND EX": "THX SURROUND EX",
    "ROCK ARENA": "ROCK ARENA",
    "JAZZ CLUB": "JAZZ CLUB",
    "CLASSIC CONCERT": "CLASSIC CONCERT",
    "MONO MOVIE": "MONO MOVIE",
    "MATRIX": "MATRIX",
    "VIDEO GAME": "VIDEO GAME",
    "VIRTUAL": "VIRTUAL",
	"7CH STEREO": "7CH STEREO",
	}
