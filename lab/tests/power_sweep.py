from dataclasses import dataclass
import time

from instruments.power import PowerCapture
import numpy as np
from collections.abc import Callable, Iterable
import threading

from instruments.power import PowerCapture, PowerProfiler
from instruments.spd3303c import SPD3303C


@dataclass
class SweepPoint:
    voltage_setting: float
    capture: PowerCapture


@dataclass
class PowerSweepResult:
    points: list[SweepPoint]

    @property
    def voltages(self):
        return np.array([p.voltage_setting for p in self.points])

    @property
    def currents(self):
        return np.array([p.capture.average_current for p in self.points])

    @property
    def powers(self):
        return np.array([p.capture.average_power for p in self.points])


class PowerSweepTest:
    """
    Sweep PSU voltage and measure load power at each point.
    """
    def __init__(self, profiler: PowerProfiler, psu: SPD3303C, psu_channel: int = 1):
        self.profiler = profiler
        self.psu = psu
        self.psu_channel = psu_channel

    def run(
        self,
        voltages: Iterable[float],
        *,
        current_limit: float = 0.1,
        settle_time: float = 0.5,
        sample_rate: float = 100_000,
        sample_count: int = 10_000,
        on_point: Callable[[SweepPoint], None] | None = None,
        stop_event: threading.Event | None = None,
    ) -> PowerSweepResult:
        results = []

        self.psu.set_current(self.psu_channel, current_limit)
        self.psu.output_on(self.psu_channel)

        try:
            for voltage in voltages:
                if (stop_event is not None and stop_event.is_set()):
                    break

                self.psu.set_voltage(self.psu_channel, voltage)

                if stop_event is not None:
                    if stop_event.wait(settle_time):
                        break
                else:
                    time.sleep(settle_time)

                if (stop_event is not None and stop_event.is_set()):
                    break

                supply_voltage = (self.psu.measure_voltage(self.psu_channel))
                capture = self.profiler.capture(sample_rate, sample_count, supply_voltage)
                point = SweepPoint(voltage, capture)
                results.append(point)

                if on_point is not None:
                    on_point(point)

        finally:
            self.psu.output_off(self.psu_channel)

        return PowerSweepResult(results)