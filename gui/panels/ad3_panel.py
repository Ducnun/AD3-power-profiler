import tkinter as tk
from tkinter import ttk


class AD3Panel(ttk.Frame):
    """
    Analog Discovery 3 instrument panel.

    This starts as a device/status page. Acquisition controls can
    be added here independently of the power profiling experiment.
    """

    def __init__(self, parent, *, controller):
        super().__init__(parent, padding=15)
        self.controller = controller
        self.status = tk.StringVar(value="Ready")
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        frame = ttk.LabelFrame(self, text="Analog Discovery 3", padding=15)
        frame.grid(row=0, column=0, sticky="ew")

        ttk.Label(frame, text="Device:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=5)

        ttk.Label(frame, text=self.controller.ad3.name).grid(
            row=0, column=1, sticky="w", pady=5)

        ttk.Label(frame, text="Serial:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=5)

        ttk.Label(frame, text=self.controller.ad3.serial).grid(
            row=1, column=1, sticky="w", pady=5)

        ttk.Label(frame, textvariable=self.status).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(15, 0))