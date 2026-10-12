import tkinter as tk
from tkinter import ttk


class PSUPanel(ttk.Frame):
    """
    Power supply control and measurement panel.
    """

    def __init__(self, parent, *, controller):
        super().__init__(parent, padding=15)

        self.controller = controller

        self.voltage = tk.DoubleVar(value=3.3)
        self.current_limit = tk.DoubleVar(value=0.1)

        self.measured_voltage = tk.StringVar(value="--")
        self.measured_current = tk.StringVar(value="--")
        self.status = tk.StringVar(value="Disconnected")

        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        self._build_status()
        self._build_settings()
        self._build_output()
        self._build_measurements()

    def _build_status(self):
        frame = ttk.LabelFrame(self, text="Status", padding=10)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(frame, textvariable=self.status).grid(row=0, column=0, sticky="w")

    def _build_settings(self):
        frame = ttk.LabelFrame(self, text="Output Configuration", padding=10)

        frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(frame, text="Voltage:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=5)

        ttk.Entry(frame, textvariable=self.voltage, width=12).grid(
            row=0, column=1, pady=5)

        ttk.Label(frame, text="V").grid(
            row=0, column=2, sticky="w", padx=(5, 0))

        ttk.Label(frame, text="Current limit:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=5)

        ttk.Entry(frame, textvariable=self.current_limit, width=12).grid(
            row=1, column=1, pady=5)

        ttk.Label(frame, text="A").grid(
            row=1, column=2, sticky="w", padx=(5, 0))

        ttk.Button(frame, text="Apply", command=self._apply_settings).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))

    def _build_output(self):
        frame = ttk.LabelFrame(self, text="Output", padding=10)
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        ttk.Button(frame, text="Output ON", command=self._output_on).grid(
            row=0, column=0, sticky="ew", padx=(0, 5))

        ttk.Button(frame, text="Output OFF", command=self._output_off).grid(
            row=0, column=1, sticky="ew", padx=(5, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_measurements(self):
        frame = ttk.LabelFrame(self, text="Measurements", padding=10)
        frame.grid(row=3, column=0, sticky="ew")

        ttk.Label(frame, text="Voltage:").grid(
            row=0, column=0, sticky="w")

        ttk.Label(frame, textvariable=self.measured_voltage).grid(
            row=0, column=1, sticky="e")

        ttk.Label(frame, text="Current:").grid(
            row=1, column=0, sticky="w")

        ttk.Label(frame, textvariable=self.measured_current).grid(
            row=1, column=1, sticky="e")

        ttk.Button(frame, text="Refresh", command=self.refresh_measurements,).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    # ------------------------------------------------------------------
    # Controller operations
    # ------------------------------------------------------------------

    def _apply_settings(self):
        self.controller.set_voltage(self.voltage.get())
        self.controller.set_current_limit(self.current_limit.get())
        self.status.set("Settings applied")

    def _output_on(self):
        self.controller.output_on()
        self.status.set("Output ON")

    def _output_off(self):
        self.controller.output_off()
        self.status.set("Output OFF")

    def refresh_measurements(self):
        voltage = self.controller.measure_voltage()
        current = self.controller.measure_current()
        self.measured_voltage.set(f"{voltage:.4f} V")
        self.measured_current.set(f"{current * 1000:.3f} mA")