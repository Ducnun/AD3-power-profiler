from __future__ import annotations

import threading
from collections.abc import Callable, Iterable

from instruments import AD3, SPD3303C
from instruments.power import PowerProfiler, Shunt

# Import tests
from lab.tests import PowerSweepResult, PowerSweepTest, SweepPoint
from lab.tests.power_profile import PowerProfileTest



class LabController:
    """
    High-level controller for the laboratory equipment.

    The controller owns instrument lifecycles and provides a common
    interface for the GUI and automated tests.

    Direct hardware access remains available through:

        controller.ad3
        controller.psu

    High-level experiments are exposed as controller methods:

        controller.run_power_sweep(...)
    """

    def __init__(self, *, psu_channel: int = 1, shunt_resistance: float = 10.0, shunt_channel: int = 0, voltage_channel: int = 0):
        self.psu_channel = psu_channel
        self.shunt_resistance = shunt_resistance
        self.shunt_channel = shunt_channel
        self.voltage_channel = voltage_channel

        self._ad3: AD3 | None = None
        self._psu: SPD3303C | None = None

        self._profiler: PowerProfiler | None = None
        self._power_sweep: PowerSweepTest | None = None
        self._power_profile: PowerProfileTest | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Return True if the laboratory hardware is connected."""

        return (self._ad3 is not None and self._psu is not None)

    def connect(self) -> None:
        """
        Connect to the laboratory equipment.

        If initialization fails, already-connected hardware is cleaned
        up before the exception is re-raised.
        """

        if self.connected:
            return

        ad3 = AD3()
        psu = SPD3303C()

        try:
            ad3.connect()
            psu.connect()

            profiler = PowerProfiler(analog=ad3.analog, shunt=Shunt(self.shunt_resistance))
            power_sweep = PowerSweepTest(profiler=profiler, psu=psu, psu_channel=self.psu_channel)
            power_profile = PowerProfileTest(profiler=profiler, psu=psu, psu_channel=self.psu_channel)

        except Exception:
            try:
                psu.close()
            finally:
                ad3.close()

            raise

        self._ad3 = ad3
        self._psu = psu
        self._profiler = profiler
        self._power_sweep = power_sweep
        self._power_profile = power_profile

    def disconnect(self) -> None:
        """
        Safely disconnect all laboratory equipment.

        The PSU output is disabled before disconnecting it.
        """

        if self._psu is not None:
            try:
                self._psu.output_off(self.psu_channel)
            except Exception:
                pass

            self._psu.close()

        if self._ad3 is not None:
            self._ad3.close()

        self._ad3 = None
        self._psu = None
        self._profiler = None
        self._power_sweep = None
        self._power_profile = None

    def __enter__(self) -> LabController:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------

    @property
    def ad3(self) -> AD3:
        """
        Connected Analog Discovery 3.
        """
        if self._ad3 is None:
            raise RuntimeError("Lab controller is not connected")

        return self._ad3

    @property
    def psu(self) -> SPD3303C:
        """
        Connected SPD3303C power supply.
        """
        if self._psu is None:
            raise RuntimeError("Lab controller is not connected")

        return self._psu

    @property
    def profiler(self) -> PowerProfiler:
        """
        Connected power profiler.
        """

        if self._profiler is None:
            raise RuntimeError("Lab controller is not connected")

        return self._profiler

    # ------------------------------------------------------------------
    # PSU
    # ------------------------------------------------------------------

    def set_voltage(self, voltage: float) -> None:
        self.psu.set_voltage(self.psu_channel, voltage)

    def get_voltage(self) -> float:
        return self.psu.get_voltage(self.psu_channel)

    def set_current_limit(self, current: float) -> None:
        self.psu.set_current(self.psu_channel, current)

    def get_current_limit(self) -> float:
        return self.psu.get_current(self.psu_channel)

    def measure_voltage(self) -> float:
        return self.psu.measure_voltage(self.psu_channel)

    def measure_current(self) -> float:
        return self.psu.measure_current(self.psu_channel)

    def output_on(self) -> None:
        self.psu.output_on(self.psu_channel)

    def output_off(self) -> None:
        self.psu.output_off(self.psu_channel)

    # ------------------------------------------------------------------
    # Power measurement
    # ------------------------------------------------------------------

    def measure_power(self, *, sample_rate: float = 100_000, sample_count: int = 10_000,):
        """
        Perform one power capture.
        """
        return self.profiler.capture(sample_rate, sample_count, self.get_voltage())

    # ------------------------------------------------------------------
    # Power sweep
    # ------------------------------------------------------------------
    def run_power_sweep(
        self,
        voltages: Iterable[float],
        *,
        current_limit: float = 0.1,
        settle_time: float = 0.5,
        sample_rate: float = 100_000,
        sample_count: int = 10_000,
        on_point: Callable[[SweepPoint], None] | None = None,
        stop_event: threading.Event | None = None) -> PowerSweepResult:
        """
        Run a power sweep.

        on_point is called after each completed measurement.

        stop_event can be set by the caller to request cancellation.
        """

        if self._power_sweep is None:
            raise RuntimeError("Lab controller is not connected")

        return self._power_sweep.run(
            voltages=voltages,
            current_limit=current_limit,
            settle_time=settle_time,
            sample_rate=sample_rate,
            sample_count=sample_count,
            on_point=on_point,
            stop_event=stop_event,
        )

    def run_power_profile(
        self,
        *,
        voltage: float,
        current_limit: float = 0.1,
        settle_time: float = 0.5,
        sample_rate: float = 100_000,
        sample_count: int = 100_000):
        if self._power_profile is None:
            raise RuntimeError("Lab controller is not connected")

        return self._power_profile.run(
            voltage=voltage,
            current_limit=current_limit,
            settle_time=settle_time,
            sample_rate=sample_rate,
            sample_count=sample_count)

    def run_power_profile_continuous(
        self,
        *,
        voltage: float,
        current_limit: float = 0.1,
        settle_time: float = 0.5,
        sample_rate: float = 100_000,
        sample_count: int = 10_000,
        on_capture=None,
        stop_event: threading.Event | None = None) -> None:
        
        if self._power_profile is None:
            raise RuntimeError("Lab controller is not connected")

        self._power_profile.run_continuous(
            voltage=voltage,
            current_limit=current_limit,
            settle_time=settle_time,
            sample_rate=sample_rate,
            sample_count=sample_count,
            on_capture=on_capture,
            stop_event=stop_event)

    def status(self) -> dict[str, float | bool]:
        """
        Return the current state of the configured PSU channel.
        """
        if not self.connected:
            return {"connected": False}

        return {
            "connected": True,
            "voltage_setting": self.get_voltage(),
            "current_limit": self.get_current_limit(),
            "voltage": self.measure_voltage(),
            "current": self.measure_current(),
        }
