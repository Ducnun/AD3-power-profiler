from collections.abc import Callable
from dataclasses import dataclass
import threading
import time

from instruments.power import PowerCapture, PowerProfiler
from instruments.spd3303c import SPD3303C


@dataclass
class PowerProfileResult:
    capture: PowerCapture


class PowerProfileTest:
    """
    Capture power consumption for a fixed period or continuously.
    """

    def __init__(
        self,
        profiler: PowerProfiler,
        psu: SPD3303C,
        psu_channel: int = 1,
    ):
        self.profiler = profiler
        self.psu = psu
        self.psu_channel = psu_channel

    def _start_supply(
        self,
        voltage: float,
        current_limit: float,
    ) -> None:
        self.psu.set_current(self.psu_channel, current_limit)
        self.psu.set_voltage(self.psu_channel, voltage)
        self.psu.output_on(self.psu_channel)

    def _measure_supply_voltage(self) -> float:
        return self.psu.measure_voltage(self.psu_channel)

    def run(
        self,
        *,
        voltage: float,
        current_limit: float = 0.1,
        settle_time: float = 0.5,
        sample_rate: float = 100_000,
        sample_count: int = 100_000,
    ) -> PowerProfileResult:
        self._start_supply(voltage, current_limit)

        try:
            time.sleep(settle_time)

            supply_voltage = self._measure_supply_voltage()

            capture = self.profiler.capture(
                sample_rate,
                sample_count,
                supply_voltage,
            )

            return PowerProfileResult(capture)

        finally:
            self.psu.output_off(self.psu_channel)

    def run_continuous(
        self,
        *,
        voltage: float,
        current_limit: float = 0.1,
        settle_time: float = 0.5,
        sample_rate: float = 100_000,
        sample_count: int = 10_000,
        on_capture: Callable[[PowerCapture], None] | None = None,
        stop_event: threading.Event | None = None,
    ) -> None:
        self._start_supply(voltage, current_limit)

        try:
            time.sleep(settle_time)

            # Initial PSU sanity check.
            supply_voltage = self._measure_supply_voltage()

            print(f"PSU voltage: {supply_voltage:.3f} V")

            while stop_event is None or not stop_event.is_set():

                # Both voltage and shunt voltage are captured
                # synchronously by the AD3.
                capture = self.profiler.capture(
                    sample_rate,
                    sample_count,
                    supply_voltage,
                )

                if on_capture is not None:
                    on_capture(capture)

        finally:
            self.psu.output_off(self.psu_channel)