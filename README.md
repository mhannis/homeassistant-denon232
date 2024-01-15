# Home Assistant Denon RS232

This is a Denon AVR / Receiver Custom Component for Home Assistant that allows you to control a receiver through RS232.  This custom component should support any Denon receiver with a serial port. This implementation was based off of the following integrations:

https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/components/media_player/denon.py
https://github.com/joopert/nad_receiver/blob/master/nad_receiver/__init__.py 

Setup:
1) If not present create the custom component folder structure under your Home Assistant config directory.
config/custom_components/denon232/

2) Place ``__init__.py``, media_player.py and denon232_receiver.py in the denon232 folder under custom components folder.

3) Add configuration details to configuration.yaml located in the config directory:

```
media_player:
  - platform: denon232
    serial_port: socket://your.network.device:portnumber
    name: Receiver
```

The serial_port device referenced should be changed to match what is being used in your setup. In this example a USB to serial converter was used on a remote machine and exported through ser2net. A local USB device can also be used.

## Zones
This integration supports multiple zones. When configured, zones are added as additional `media_player` entities. Zones can be configured in `configuration.yaml` by adding the `zones` config key. The configuration defines a zone name and its zone identifier used in serial commands. Zone 3 is sometimes seen as 'Z1' as in the example below but also as 'Z3'.

```
    zones:
      "Zone 2": Z2
      "Zone 3": Z1
```