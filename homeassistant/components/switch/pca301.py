"""
Support for PCA301 plugs

using standard firmware from FHEM
https://svn.fhem.de/trac/browser/trunk/fhem/contrib/arduino/36_PCA301-pcaSerial.zip

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.pca301/
"""
import os
import re
import logging

from datetime import datetime

import voluptuous as vol

from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_DEVICE, EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['pyserial==3.1.1']

_LOGGER = logging.getLogger(__name__)

CONF_BAUD = 'baud'
CONF_MAPPING = 'mapping'
CONF_TIMEOUT = 'timeout'
CONF_WRITE_TIMEOUT = 'write_timeout'

DEFAULT_DEVICE = '/dev/ttyUSB0'
DEFAULT_BAUD = 57600
DEFAULT_TIMEOUT = 1
DEFAULT_WRITE_TIMEOUT = 1

OUTLET_STATUS_MSG = re.compile(
    r'^OK (?:\d+) (?P<nodeid>\d+) (?:\d+) (?:\d+ \d+ \d+) (?P<state>1|0) ' +
    r'(?P<total>\d+ \d+) (?P<current>\d+ \d+)')

def isdevice(dev):
    """Check if dev a real device."""
    try:
        os.stat(dev)
        return str(dev)
    except OSError:
        raise vol.Invalid("No device found!")

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICE, default=DEFAULT_DEVICE): isdevice,
    vol.Optional(CONF_BAUD, default=DEFAULT_BAUD): cv.string,
    #vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
    vol.Optional(CONF_WRITE_TIMEOUT, default=DEFAULT_WRITE_TIMEOUT):
        cv.positive_int,
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Initialize the PCA301 Controller"""
    serial_port = config.get(CONF_DEVICE)
    baud = config.get(CONF_BAUD)
    timeout = config.get(CONF_TIMEOUT)
    write_timeout = config.get(CONF_WRITE_TIMEOUT)
    mapping = config.get(CONF_MAPPING, {})

    import serial

    try:
        ctrl = PCA301Ctrl(serial_port, baud, mapping, timeout, write_timeout, add_devices)
        _LOGGER.debug("PCA301Ctrl started")
    except serial.SerialException as exc:
        _LOGGER.exception("Unable to open serial port for pca301: %s", exc)
        return False

    def dispose(event):
        """Shutdown the PCA301 Controller thread."""
        ctrl.shutdown()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, dispose)

class PCA301Ctrl():
    """The PCA301 controller is responsible for communication with the plugs
    via serial provided by a Jeelink."""
    def __init__(self, serial_port, baud, mapping, timeout, write_timeout, add_devices, **kwargs):
        devcb = add_devices
        devices = {}

        import serial
        import serial.threaded
        serial_device = serial.Serial(
            port=serial_port, baudrate=baud, timeout=timeout, write_timeout=write_timeout,
            **kwargs)

        class JeelinkHandler(serial.threaded.LineReader):
            """The JeelinkHandler parses the output provided by the Jeelink
            over serial and looks for status updates of plugs. For this it
            spins up a thread that is used for the serial I/O."""
            def connection_made(self, transport):
                super(JeelinkHandler, self).connection_made(transport)
                _LOGGER.debug('port opened\n')

            def handle_line(self, line):
                line = line.strip()
                status_report = OUTLET_STATUS_MSG.match(line)
                if status_report:
                    _LOGGER.debug(line)

                    nodeid = status_report.group('nodeid')
                    is_on = status_report.group('state') == '1'

                    _LOGGER.debug('state is ' + nodeid + ' state ' + str(is_on))

                    # total
                    total_tuple = [int(x) for x in status_report.group('total').split(' ')]
                    total_consumption = (total_tuple[0] << 8 | total_tuple[1]) / 10

                    # current
                    current_tuple = [int(x) for x in status_report.group('current').split(' ')]
                    curr_consumption = (current_tuple[0] << 8 | current_tuple[1]) / 100

                    # check if current state matches target state
                    if devices.get(nodeid, None):
                        devices[nodeid].set_state(is_on)
                    # check for new device
                    else:
                        _LOGGER.debug("discovered new device with id " + nodeid)
                        name = mapping.get(int(nodeid), 'pca301_node' + str(nodeid))
                        devices[nodeid] = PCA301Plug(
                            self, name, nodeid, is_on, curr_consumption, total_consumption)
                        devcb([devices[nodeid]])

            def write_line(self, data):
                self.transport.write(data.encode(
                    self.ENCODING, self.UNICODE_HANDLING) + self.TERMINATOR)

            def connection_lost(self, exc):
                if exc:
                    _LOGGER.debug(exc)
                _LOGGER.debug('port closed\n')

        self.thread = serial.threaded.ReaderThread(serial_device, JeelinkHandler)
        self.thread.start()
        _LOGGER.debug("thread started")

    def shutdown(self):
        """Shuts down the serial I/O thread."""
        self.thread.stop()

class PCA301Plug(SwitchDevice):
    """Representation of a pca301 plug."""

    def __init__(self, ctrl, name, device_id, state, curr_consumption, total_consumption):
        """Initialize the pca301 device."""
        self._ctrl = ctrl
        self._name = name
        self._id = device_id
        self._state = state
        self._available = True
        self._lastupdate = datetime.utcnow()
        self._current = curr_consumption
        self._total = total_consumption

    @property
    def name(self):
        return self._name

    @property
    def available(self):
        return self._available

    @property
    def is_on(self):
        return self._state

    @property
    def device_state_attributes(self):
        return {
            'current_consumption': self._current,
            'total_consumption': self._total,
        }

    def set_state(self, state):
        """Sets the state of the plug (based on a received status update) """
        self._state = state
        self._lastupdate = datetime.utcnow()
        self.schedule_update_ha_state(True)

    def turn_on(self):
        """Set plug status to on."""
        _LOGGER.debug('about to turn on plug ' + self._id)
        self._state = True
        self._ctrl.write_line(self._id+'e')
        self.schedule_update_ha_state()

    def turn_off(self):
        """Set plug status to off."""
        _LOGGER.debug('about to turn off plug ' + self._id)
        self._state = False
        self._ctrl.write_line(self._id+'d')
        self.schedule_update_ha_state()

    def update(self):
        diff = (datetime.utcnow() - self._lastupdate).total_seconds()
        if diff > 30:
            self._available = False
            self.schedule_update_ha_state()
