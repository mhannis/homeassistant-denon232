import logging
import serial
import threading
import time

DEFAULT_TIMEOUT = 1
DEFAULT_WRITE_TIMEOUT = 1

_LOGGER = logging.getLogger(__name__)

class Denon232Receiver(object):
    def __init__(self, serial_port, timeout=DEFAULT_TIMEOUT, write_timeout=DEFAULT_WRITE_TIMEOUT):
        self.ser = serial.Serial(serial_port, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=timeout, write_timeout=write_timeout)
        self.lock = threading.Lock()
        _LOGGER.debug("Serial connection opened.")
        self.initialize_connection()

    def initialize_connection(self):
        self.serial_command('PWSTANDBY', response=False)
        #time.sleep(2)  # Give the receiver time to wake up

    def serial_command(self, cmd, response=False, all_lines=False):
        _LOGGER.debug('Sending command: %s', cmd)
        with self.lock:  # Use a context manager to ensure the lock is always released
            for char in f'{cmd}\r':  # Include the carriage return in the command
                self.ser.write(char.encode('utf-8'))
                self.ser.flush()
                #time.sleep(.02)  # Delay of 20ms between each character
            if response:
                lines = self._read_response()
                return lines if all_lines else lines[0] if lines else None

    def _read_response(self):
        lines = []
        while True:
            line = self.ser.readline().decode().strip()
            if not line:
                break
            lines.append(line)
            _LOGGER.debug("Received line: %s", line)
        return lines
