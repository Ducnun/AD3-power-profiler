import threading
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from lab.tests.power_sweep import PowerSweepResult, SweepPoint


class PowerSweepPanel(ttk.Frame):
    """
    GUI for configuring, running, and viewing a power sweep.
    """

    def __init__(self, parent, *, controller, on_result=None):
        super().__init__(parent, padding=15)

        self.controller = controller
        self.on_result = on_result

        self.start_voltage = tk.DoubleVar(value=3.0)
        self.stop_voltage = tk.DoubleVar(value=5.0)
        self.step_voltage = tk.DoubleVar(value=0.1)

        self.current_limit = tk.DoubleVar(value=0.1)
        self.settle_time = tk.DoubleVar(value=0.5)

        self.sample_rate = tk.IntVar(value=100_000)
        self.sample_count = tk.IntVar(value=10_000)

        self.status = tk.StringVar(value="Ready")

        self.result: PowerSweepResult | None = None
        self._worker = None
        self._stop_event = None

        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_result()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _build_left_panel(self):
        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="ns", padx=(0, 15))

        self._build_configuration(frame)
        self._build_controls(frame)
        self._build_status(frame)

    def _build_configuration(self, parent):
        frame = ttk.LabelFrame(parent, text="Sweep Configuration", padding=10)
        frame.pack(fill="x", pady=(0, 10))

        fields = [
            ("Start voltage", self.start_voltage, "V"),
            ("Stop voltage", self.stop_voltage, "V"),
            ("Step", self.step_voltage, "V"),
            ("Current limit", self.current_limit, "A"),
            ("Settle time", self.settle_time, "s"),
            ("Sample rate", self.sample_rate, "Hz"),
            ("Sample count", self.sample_count, ""),
        ]

        for row, (label, variable, unit) in enumerate(fields):
            ttk.Label(frame, text=f"{label}:").grid(
                row=row, column=0, sticky="w", padx=(0, 10), pady=3)

            ttk.Entry(frame, textvariable=variable, width=15).grid(
                row=row, column=1, sticky="w", pady=3)

            if unit:
                ttk.Label(frame, text=unit).grid(
                    row=row, column=2, sticky="w", padx=(5, 0))

    def _build_controls(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(0, 10))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        self.run_button = ttk.Button(frame, text="Run Sweep", command=self.start_sweep)
        self.run_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.stop_button = ttk.Button(frame, text="Stop", command=self.stop_sweep)
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def _build_status(self, parent):
        frame = ttk.LabelFrame(parent, text="Status", padding=10)
        frame.pack(fill="x")

        ttk.Label(frame, textvariable=self.status).pack(anchor="w")

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def _build_result(self):
        frame = ttk.LabelFrame(self, text="Result", padding=10)
        frame.grid(row=0, column=1, sticky="nsew")

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(7, 5), dpi=100)

        self.power_ax = self.figure.add_subplot(211)
        self.current_ax = self.figure.add_subplot(212, sharex=self.power_ax)

        self.power_ax.set_title("Power Sweep")
        self.power_ax.set_ylabel("Power (mW)")
        self.power_ax.grid(True, alpha=0.3)

        self.current_ax.set_xlabel("PSU voltage (V)")
        self.current_ax.set_ylabel("Current (mA)")
        self.current_ax.grid(True, alpha=0.3)

        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        self._build_statistics(frame)
        self.figure.tight_layout()

    def _build_statistics(self, parent):
        frame = ttk.Frame(parent)
        frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        self.average_current = tk.StringVar(value="-")
        self.peak_current = tk.StringVar(value="-")
        self.average_power = tk.StringVar(value="-")
        self.peak_power = tk.StringVar(value="-")

        statistics = [
            ("Average current", self.average_current),
            ("Peak current", self.peak_current),
            ("Average power", self.average_power),
            ("Peak power", self.peak_power),
        ]

        for index, (label, variable) in enumerate(statistics):
            row = index // 2
            column = (index % 2) * 2

            ttk.Label(frame, text=f"{label}:").grid(
                row=row, column=column, sticky="w", padx=(0, 5), pady=2)

            ttk.Label(frame, textvariable=variable).grid(
                row=row, column=column + 1, sticky="w", padx=(0, 20), pady=2)

    # ------------------------------------------------------------------
    # Sweep
    # ------------------------------------------------------------------

    def _generate_voltages(self):
        start = self.start_voltage.get()
        stop = self.stop_voltage.get()
        step = self.step_voltage.get()

        if step <= 0:
            raise ValueError("Step must be greater than zero")

        if stop < start:
            raise ValueError("Stop voltage must be greater than start voltage")

        values = []

        voltage = start

        while voltage <= stop + 1e-12:
            values.append(voltage)
            voltage += step

        return values

    def start_sweep(self):
        if self._worker is not None:
            return

        try:
            voltages = self._generate_voltages()

            capture_time = self.sample_count.get() / self.sample_rate.get()
            point_time = self.settle_time.get() + capture_time
            estimated_time = len(voltages) * point_time

            current_limit = self.current_limit.get()
            settle_time = self.settle_time.get()
            sample_rate = self.sample_rate.get()
            sample_count = self.sample_count.get()

            if current_limit <= 0:
                raise ValueError("Current limit must be greater than zero")

            if settle_time < 0:
                raise ValueError("Settle time must be non-negative")

            if sample_rate <= 0:
                raise ValueError("Sample rate must be greater than zero")

            if sample_count <= 0:
                raise ValueError("Sample count must be greater than zero")

        except (tk.TclError, ValueError) as exc:
            self.status.set(str(exc))
            return

        voltages = self._generate_voltages()

        self.result = PowerSweepResult([])
        self._prepare_plot(voltages)

        self._stop_event = threading.Event()

        self._clear_result()

        self.status.set(f"Running sweep ({len(voltages)} points)...")

        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        self._worker = threading.Thread(
            target=self._run_sweep,
            args=(voltages, current_limit, settle_time, sample_rate, sample_count),
            daemon=True,
        )

        self._worker.start()

    def _run_sweep(self, voltages, current_limit, settle_time, sample_rate, sample_count):
        try:
            result = self.controller.run_power_sweep(
                voltages,
                current_limit=current_limit,
                settle_time=settle_time,
                sample_rate=sample_rate,
                sample_count=sample_count,
                on_point=self._point_complete,
                stop_event=self._stop_event,
            )

            self.after(0, lambda result=result: self._sweep_complete(result))

        except Exception as exc:
            self.after(0, lambda exc=exc: self.status.set(f"Error: {exc}"))

        finally:
            self.after(0, self._worker_finished)

    def _point_complete(self, point: SweepPoint):
        """
        Called from the sweep worker thread.

        Tkinter widgets are updated through the main thread.
        """

        self.after(0, lambda point=point: self._update_point(point))

    def _update_point(self, point: SweepPoint):
        if self.result is None:
            self.result = PowerSweepResult([])

        self.result.points.append(point)

        voltage = point.voltage_setting
        current = point.capture.average_current
        power = point.capture.average_power

        self.status.set(f"{voltage:.2f} V  " f"{current * 1000:.3f} mA  " f"{power * 1000:.3f} mW")

        self._update_plot()
        self._update_statistics()

    def _sweep_complete(self, result: PowerSweepResult):
        self.result = result

        if self._stop_event is not None and self._stop_event.is_set():
            self.status.set(f"Sweep stopped ({len(result.points)} points)")
        else:
            self.status.set(f"Sweep complete ({len(result.points)} points)")

        self._update_plot()
        self._update_statistics()

        if self.on_result is not None:
            self.on_result(result)

    def stop_sweep(self):
        if self._stop_event is not None:
            self.stop_button.configure(state="disabled")
            self.status.set("Stopping...")
            self._stop_event.set()

    def _worker_finished(self):
        self._worker = None
        self._stop_event = None

        self.run_button.configure(state="normal")
        self.stop_button.configure(state="normal")

    # ------------------------------------------------------------------
    # Result display
    # ------------------------------------------------------------------

    def _clear_result(self):
        self.power_ax.clear()
        self.current_ax.clear()

        self.power_ax.set_title("Power Sweep")
        self.power_ax.set_ylabel("Power (mW)")
        self.power_ax.grid(True, alpha=0.3)

        self.current_ax.set_xlabel("PSU voltage (V)")
        self.current_ax.set_ylabel("Current (mA)")
        self.current_ax.grid(True, alpha=0.3)

        self.average_current.set("-")
        self.peak_current.set("-")
        self.average_power.set("-")
        self.peak_power.set("-")

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _prepare_plot(self, voltages):
        self.power_ax.clear()
        self.current_ax.clear()

        self.power_ax.set_title("Power Sweep")
        self.power_ax.set_ylabel("Power (mW)")
        self.power_ax.set_xlim(min(voltages), max(voltages))
        self.power_ax.grid(True, alpha=0.3)

        self.current_ax.set_xlabel("PSU voltage (V)")
        self.current_ax.set_ylabel("Current (mA)")
        self.current_ax.set_xlim(min(voltages), max(voltages))
        self.current_ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _update_plot(self):
        if self.result is None or not self.result.points:
            return

        self.power_ax.clear()
        self.current_ax.clear()
        self.power_ax.plot(self.result.voltages, self.result.powers * 1000, marker="o", linewidth=1)
        self.power_ax.set_title("Power Sweep")
        self.power_ax.set_ylabel("Power (mW)")
        self.power_ax.grid(True, alpha=0.3)

        self.current_ax.plot(self.result.voltages, self.result.currents * 1000, marker="o", linewidth=1)

        self.current_ax.set_xlabel("PSU voltage (V)")
        self.current_ax.set_ylabel("Current (mA)")
        self.current_ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _update_statistics(self):
        if self.result is None or not self.result.points:
            return

        currents = self.result.currents
        powers = self.result.powers
        self.average_current.set(f"{currents.mean() * 1000:.3f} mA")
        self.peak_current.set(f"{currents.max() * 1000:.3f} mA")
        self.average_power.set(f"{powers.mean() * 1000:.3f} mW")
        self.peak_power.set(f"{powers.max() * 1000:.3f} mW")