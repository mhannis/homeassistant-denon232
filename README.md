# Home Assistant Denon RS232

This is a Denon AVR / Receiver Custom Component for Home Assistant that allows you to control a receiver through RS232. This custom component should support any Denon receiver with a serial port.
As I only have my own device to test (AVR-3805), development focuses specifically on this device's features. 
This implementation is a fork of the original implementation by [bluepixel00](https://github.com/bluepixel00/HomeAssistant_Denon_RS232) and takes inspiration from other Home Assistant media player integrations.

## Setup:
1) If not present create the custom component folder structure under your Home Assistant config directory.
`config/custom_components/denon232/`

2) Place `__init__.py`, `media_player.py` and `denon232_receiver.py` in the denon232 folder under custom components folder.

3) Add configuration details to configuration.yaml located in the config directory:

```
media_player:
  - platform: denon232
    serial_port: socket://your.network.device:portnumber
    name: Receiver
```

The `serial_port` device referenced should be changed to match what is being used in your setup. In this example a USB to serial converter was used on a remote machine and exported through ser2net. A local USB device can also be used.
