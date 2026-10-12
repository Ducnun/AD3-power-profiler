from dataclasses import dataclass

import numpy as np


@dataclass
class PowerCapture:
    """
    Power measurement captured over time.
    """
    time: np.ndarray
    supply_voltage: float
    voltage: np.ndarray
    shunt_voltage: np.ndarray
    current: np.ndarray
    power: np.ndarray

    @property
    def sample_count(self) -> int:
        return len(self.time)

    @property
    def duration(self) -> float:
        if self.sample_count < 2:
            return 0.0

        return float(self.time[-1] - self.time[0])

    @property
    def average_voltage(self) -> float:
        return float(np.mean(self.voltage))

    @property
    def average_shunt_voltage(self) -> float:
        return float(np.mean(self.shunt_voltage))

    @property
    def average_current(self) -> float:
        return float(np.mean(self.current))

    @property
    def average_power(self) -> float:
        return float(np.mean(self.power))

    @property
    def peak_current(self) -> float:
        return float(np.max(self.current))

    @property
    def peak_power(self) -> float:
        return float(np.max(self.power))

    @property
    def energy(self) -> float:
        """
        Energy consumed by the load during the capture.

        Returns
        -------
        float
            Energy in joules.
        """

        return float(np.trapezoid(self.power, self.time))
