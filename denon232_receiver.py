import logging
import serial
import threading
import time

DEFAULT_TIMEOUT = 1
DEFAULT_WRITE_TIMEOUT = 1
DEFAULT_REFRESH_INTERVAL = 60  # Seconds between full state refreshes

_LOGGER = logging.getLogger(__name__)

class Denon232Receiver(object):
    def __init__(self, serial_port, timeout=DEFAULT_TIMEOUT, write_timeout=DEFAULT_WRITE_TIMEOUT):
        """Initialize the Denon 232 receiver with serial connection and state storage."""
        self.ser = serial.Serial(
            serial_port, 
            baudrate=9600, 
            bytesize=serial.EIGHTBITS, 
            parity=serial.PARITY_NONE, 
            stopbits=serial.STOPBITS_ONE, 
            timeout=timeout, 
            write_timeout=write_timeout
        )
        self.lock = threading.Lock()
        _LOGGER.debug("Serial connection opened.")
        
        # Initialize state cache
        self.state = {
            'power': 'PWSTANDBY',  # Default to standby
            'volume': 0,
            'volume_max': 80,  # Default, will be updated during initialization
            'muted': False,
            'source': '',
            'sound_mode': '',
            'zones': {}  # Storage for zone states
        }
        
        # Initialize the connection
        self.initialize_connection()
        
        # Get initial state
        self.initialize_state()

    def initialize_connection(self):
        """Initialize the connection to the receiver."""
        self.serial_command('PWSTANDBY', response=False)
        # We don't sleep here anymore as we're not immediately requesting state

    def initialize_state(self):
        """Get the initial state from the receiver."""
        _LOGGER.debug("Initializing receiver state")
        
        # Get power state
        self.state['power'] = self.serial_command('PW?', response=True, update_state=False)
        
        # Get volume info including max volume
        volume_lines = self.serial_command('MV?', response=True, all_lines=True, update_state=False)
        for line in volume_lines:
            if line.startswith('MVMAX '):
                try:
                    # Only grab two digit max, don't care about any half digit
                    self.state['volume_max'] = int(line[len('MVMAX '):len('MVMAX XX')])
                    _LOGGER.debug("MVMAX Value Saved: %s", self.state['volume_max'])
                except (ValueError, IndexError):
                    _LOGGER.error("Failed to parse MVMAX value: %s", line)
            elif line.startswith('MV'):
                try:
                    volume = int(line[len('MV'):len('MVXX')])
                    if volume == 99:
                        volume = 0
                    self.state['volume'] = volume
                    _LOGGER.debug("MV Value Saved: %s", self.state['volume'])
                except (ValueError, IndexError):
                    _LOGGER.error("Failed to parse MV value: %s", line)
        
        # Get mute state
        mute_response = self.serial_command('MU?', response=True, update_state=False)
        self.state['muted'] = (mute_response == 'MUON')
        
        # Get current source
        source_response = self.serial_command('SI?', response=True, update_state=False)
        if source_response and source_response.startswith('SI'):
            self.state['source'] = source_response[len('SI'):]
        
        # Get sound mode
        mode_response = self.serial_command('MS?', response=True, update_state=False)
        if mode_response and mode_response.startswith('MS'):
            self.state['sound_mode'] = mode_response[len('MS'):]
        
        # Check available zones and their states
        for zone_id in ['Z2', 'Z3', 'Z1']:  # Try all possible zones
            zone_lines = self.serial_command(f'{zone_id}?', response=True, all_lines=True, update_state=False)
            if zone_lines:
                _LOGGER.debug(f"Found zone {zone_id}")
                self.state['zones'][zone_id] = {
                    'power': 'ON' if any(line.endswith('ON') for line in zone_lines) else 'OFF',
                    'volume': 0,
                    'source': ''
                }
                
                # Parse zone volume and source
                for line in zone_lines:
                    if line.startswith(zone_id):
                        if line[len(zone_id):].isdigit():
                            try:
                                volume = int(line[len(zone_id):len(zone_id) + 2])
                                if volume == 99:
                                    volume = 0
                                self.state['zones'][zone_id]['volume'] = volume
                                _LOGGER.debug(f"{zone_id} Volume value Saved: {volume}")
                            except (ValueError, IndexError):
                                _LOGGER.error(f"Failed to parse {zone_id} volume: {line}")
                        elif not line.endswith('ON') and not line.endswith('OFF'):
                            self.state['zones'][zone_id]['source'] = line[len(zone_id):]
        
        _LOGGER.debug("Receiver state initialized: %s", self.state)
        return self.state

    def serial_command(self, cmd, response=False, all_lines=False, update_state=True):
        """
        Send command to receiver and optionally update internal state.
        
        Args:
            cmd (str): Command to send to the receiver
            response (bool): Whether to wait for a response
            all_lines (bool): Whether to return all response lines or just first one
            update_state (bool): Whether to update internal state based on command
        """
        _LOGGER.debug('Sending command: %s', cmd)
        
        with self.lock:  # Use context manager to ensure the lock is always released
            # Send each character with a carriage return
            for char in f'{cmd}\r':
                self.ser.write(char.encode('utf-8'))
                self.ser.flush()
            
            # Update internal state based on command if requested
            if update_state and not cmd.endswith('?'):
                self._update_state_from_command(cmd)
                
            if response:
                lines = self._read_response()
                
                # If this was a query command and update_state is True,
                # update our state with the response
                if cmd.endswith('?') and update_state and lines:
                    self._update_state_from_response(cmd, lines)
                    
                return lines if all_lines else lines[0] if lines else None

    def _read_response(self):
        """Read response from the receiver."""
        lines = []
        while True:
            line = self.ser.readline().decode().strip()
            if not line:
                break
            lines.append(line)
            _LOGGER.debug("Received line: %s", line)
        return lines
    
    def _update_state_from_command(self, cmd):
        """Update internal state based on command sent."""
        # Power commands
        if cmd == 'PWON':
            self.state['power'] = 'PWON'
        elif cmd == 'PWSTANDBY':
            self.state['power'] = 'PWSTANDBY'
        
        # Volume commands
        elif cmd == 'MVUP':
            # Volume up, increment by 1
            self.state['volume'] = min(self.state['volume'] + 1, self.state['volume_max'])
        elif cmd == 'MVDOWN':
            # Volume down, decrement by 1
            self.state['volume'] = max(self.state['volume'] - 1, 0)
        elif cmd.startswith('MV') and len(cmd) > 2:
            # Direct volume setting (MV70)
            try:
                volume = int(cmd[2:4])
                self.state['volume'] = volume
            except (ValueError, IndexError):
                _LOGGER.debug("Could not parse volume from command: %s", cmd)
        
        # Mute commands
        elif cmd == 'MUON':
            self.state['muted'] = True
        elif cmd == 'MUOFF':
            self.state['muted'] = False
        
        # Source selection
        elif cmd.startswith('SI') and len(cmd) > 2:
            self.state['source'] = cmd[2:]
        
        # Sound mode
        elif cmd.startswith('MS') and len(cmd) > 2:
            self.state['sound_mode'] = cmd[2:]
        
        # Zone commands
        for zone_id in self.state['zones']:
            if cmd.startswith(zone_id):
                if cmd == f'{zone_id}ON':
                    self.state['zones'][zone_id]['power'] = 'ON'
                elif cmd == f'{zone_id}OFF':
                    self.state['zones'][zone_id]['power'] = 'OFF'
                elif cmd == f'{zone_id}UP':
                    # Zone volume up
                    self.state['zones'][zone_id]['volume'] = min(
                        self.state['zones'][zone_id]['volume'] + 1, 
                        self.state['zones'].get('volume_max', 60)
                    )
                elif cmd == f'{zone_id}DOWN':
                    # Zone volume down
                    self.state['zones'][zone_id]['volume'] = max(
                        self.state['zones'][zone_id]['volume'] - 1, 0
                    )
                elif len(cmd) > len(zone_id) and cmd[len(zone_id):].isdigit():
                    # Direct zone volume setting
                    try:
                        volume = int(cmd[len(zone_id):len(zone_id) + 2])
                        self.state['zones'][zone_id]['volume'] = volume
                    except (ValueError, IndexError):
                        _LOGGER.debug("Could not parse zone volume from command: %s", cmd)
                elif len(cmd) > len(zone_id):
                    # Zone source selection
                    self.state['zones'][zone_id]['source'] = cmd[len(zone_id):]
    
    def _update_state_from_response(self, cmd, lines):
        """Update internal state based on response to a query command."""
        if not lines:
            return
        
        # Power state query
        if cmd == 'PW?':
            self.state['power'] = lines[0]
            
        # Volume query
        elif cmd == 'MV?':
            for line in lines:
                if line.startswith('MVMAX '):
                    try:
                        self.state['volume_max'] = int(line[len('MVMAX '):len('MVMAX XX')])
                    except (ValueError, IndexError):
                        pass
                elif line.startswith('MV'):
                    try:
                        volume = int(line[len('MV'):len('MVXX')])
                        if volume == 99:
                            volume = 0
                        self.state['volume'] = volume
                    except (ValueError, IndexError):
                        pass
            
        # Mute query
        elif cmd == 'MU?':
            self.state['muted'] = (lines[0] == 'MUON')
            
        # Source query
        elif cmd == 'SI?':
            if lines[0].startswith('SI'):
                self.state['source'] = lines[0][len('SI'):]
            
        # Sound mode query
        elif cmd == 'MS?':
            if lines[0].startswith('MS'):
                self.state['sound_mode'] = lines[0][len('MS'):]
        
        # Zone queries
        for zone_id in list(self.state['zones'].keys()):
            if cmd == f'{zone_id}?':
                for line in lines:
                    if line.startswith(zone_id):
                        if line.endswith('ON'):
                            self.state['zones'][zone_id]['power'] = 'ON'
                        elif line.endswith('OFF'):
                            self.state['zones'][zone_id]['power'] = 'OFF'
                        elif line[len(zone_id):].isdigit():
                            try:
                                volume = int(line[len(zone_id):len(zone_id) + 2])
                                if volume == 99:
                                    volume = 0
                                self.state['zones'][zone_id]['volume'] = volume
                            except (ValueError, IndexError):
                                pass
                        else:
                            # Assume it's the source
                            self.state['zones'][zone_id]['source'] = line[len(zone_id):]
