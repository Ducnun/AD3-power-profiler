import dwfpy as dwf

from .analog import AnalogInput
from .digital import DigitalInput
from .wavegen import WaveGenerator


class AD3:
    """
    Interface to a Digilent Analog Discovery 3.
    """
    def __init__(self):
        self._device = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self):
        if self._device is not None:
            return

        self._device = dwf.Device()
        self._device.open()

    def close(self):
        if self._device is None:
            return

        self._device.close()
        self._device = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    # ------------------------------------------------------------------
    # Device information
    # ------------------------------------------------------------------

    @property
    def name(self):
        self._check_connected()
        return self._device.name

    @property
    def serial(self):
        self._check_connected()
        return self._device.serial_number

    # ------------------------------------------------------------------
    # Instruments
    # ------------------------------------------------------------------

    @property
    def analog(self):
        self._check_connected()
        return AnalogInput(self._device.analog_input)

    @property
    def digital(self):
        self._check_connected()
        return DigitalInput(self._device.digital_input)

    @property
    def wavegen(self):
        self._check_connected()
        return WaveGenerator(self._device.analog_output)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_connected(self):
        if self._device is None:
            raise RuntimeError("AD3 is not connected")
