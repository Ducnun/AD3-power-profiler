from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Shunt:
    """
    Current-sense resistor.

    Parameters
    ----------
    resistance:
        Resistance in ohms.
    """
    resistance: float

    def __post_init__(self):
        if self.resistance <= 0:
            raise ValueError("Shunt resistance must be greater than zero")

    def current(self, shunt_voltage):
        """
        Calculate current from voltage across the shunt.

        Parameters
        ----------
        shunt_voltage:
            Voltage across the shunt in volts.

        Returns
        -------
        numpy.ndarray
            Current in amperes.
        """

        return np.asarray(shunt_voltage) / self.resistance
