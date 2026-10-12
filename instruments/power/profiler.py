from .capture import PowerCapture
from .shunt import Shunt


class PowerProfiler:
    """
    Converts AD3 analog measurements into electrical
    measurements using a shunt resistor.
    """

    # Fixed wiring of the power-profiling fixture.
    VOLTAGE_CHANNEL = 0
    SHUNT_CHANNEL = 1

    def __init__(
        self,
        analog,
        shunt: Shunt,
    ):
        self.analog = analog
        self.shunt = shunt

    def capture(
        self,
        sample_rate: float,
        sample_count: int,
        supply_voltage: float,
        *,
        voltage_range: float = 5.0,
        shunt_range: float = 1.0,
    ) -> PowerCapture:
        """
        Capture the DUT voltage and shunt voltage, then calculate
        current and power for every sample.

        supply_voltage is the PSU's measured voltage and is retained
        as a reference value. The actual power calculation uses the
        AD3 voltage measurement.
        """

        capture = self.analog.capture(
            [
                self.VOLTAGE_CHANNEL,
                self.SHUNT_CHANNEL,
            ],
            sample_rate,
            sample_count
        )

        # Actual voltage across the DUT/load.
        voltage = capture.channel(self.VOLTAGE_CHANNEL)

        # Voltage dropped across the shunt.
        shunt_voltage = capture.channel(self.SHUNT_CHANNEL)

        # I = Vshunt / Rshunt
        current = self.shunt.current(shunt_voltage)

        # P = Vdut * I
        power = voltage * current

        return PowerCapture(
            capture.time,
            supply_voltage,
            voltage,
            shunt_voltage,
            current,
            power,
        )