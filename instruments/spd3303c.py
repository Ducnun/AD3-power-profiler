import os
import time


class SPD3303C:
    DEVICE = "/dev/usbtmc0"

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def __init__(self, device=DEVICE):
        self.device = device
        self.fd = None

    def connect(self):
        if self.fd is not None:
            return

        self.fd = os.open(
            self.device,
            os.O_RDWR,
        )

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def write(self, command):
        if self.fd is None:
            raise RuntimeError("PSU is not connected")

        command = command.rstrip("\n") + "\n"

        os.write(self.fd, command.encode())

    def read(self, size=4096):
        if self.fd is None:
            raise RuntimeError("PSU is not connected")

        data = os.read(self.fd, size)

        return data.decode(errors="replace").strip()

    def query(self, command):
        self.write(command)
        return self.read()

    def identify(self):
        return self.query("*IDN?")

    # ---------------------------------------------------------------
    # Channel configuration
    # ---------------------------------------------------------------

    def set_voltage(self, channel, voltage):
        self.write(
            f"CH{channel}:VOLTage {voltage}"
        )

    def get_voltage(self, channel):
        return float(
            self.query(f"CH{channel}:VOLTage?")
        )

    def set_current(self, channel, current):
        self.write(
            f"CH{channel}:CURRent {current}"
        )

    def get_current(self, channel):
        return float(
            self.query(f"CH{channel}:CURRent?")
        )

    # ---------------------------------------------------------------
    # Output
    # ---------------------------------------------------------------

    def output_on(self, channel):
        self.write(
            f"OUTPut CH{channel},ON"
        )

    def output_off(self, channel):
        self.write(
            f"OUTPut CH{channel},OFF"
        )

    # ---------------------------------------------------------------
    # Measurements
    # ---------------------------------------------------------------

    def measure_voltage(self, channel):
        return float(
            self.query(f"MEASure:VOLTage? CH{channel}")
        )

    def measure_current(self, channel):
        return float(
            self.query(f"MEASure:CURRent? CH{channel}")
        )

    # ---------------------------------------------------------------
    # Convenience
    # ---------------------------------------------------------------

    def configure_channel(self, channel, voltage, current):
        self.set_voltage(channel, voltage)
        self.set_current(channel, current)

    def status(self, channel):
        return {
            "voltage_setting": self.get_voltage(channel),
            "current_setting": self.get_current(channel),
            "voltage": self.measure_voltage(channel),
            "current": self.measure_current(channel),
        }