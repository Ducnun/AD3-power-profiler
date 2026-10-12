import threading
import tkinter as tk
from tkinter import ttk
from collections import deque

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from lab.tests.power_profile import PowerProfileResult
from instruments.power import PowerCapture


class PowerProfilePanel(ttk.Frame):
    """
    GUI for configuring, running, and viewing a power profile.

    The LabController performs all hardware operations. Hardware work
    runs on a background thread so the Tkinter UI remains responsive.

    Continuous captures are reduced to display-resolution data before
    being retained by the GUI.
    """

    LIVE_WINDOW = 10.0
    LIVE_UPDATE_INTERVAL = 100

    def __init__(self, parent, *, controller, on_result=None):
        super().__init__(parent, padding=15)

        self.controller = controller
        self.on_result = on_result

        # --------------------------------------------------------------
        # Configuration
        # --------------------------------------------------------------

        self.voltage = tk.DoubleVar(value=3.3)
        self.current_limit = tk.DoubleVar(value=0.1)
        self.settle_time = tk.DoubleVar(value=0.5)

        self.sample_rate = tk.IntVar(value=100_000)
        self.sample_count = tk.IntVar(value=10_000)

        self.display_granularity = tk.DoubleVar(value=0.1)

        self.status = tk.StringVar(value="Ready")

        # --------------------------------------------------------------
        # Run state
        # --------------------------------------------------------------

        self.result: PowerProfileResult | None = None

        self._worker: threading.Thread | None = None
        self._stop_event: threading.Event | None = None

        self._continuous = False

        # Tkinter must only be accessed from the Tk thread.
        # Continuous worker data is therefore protected separately.
        self._data_lock = threading.Lock()

        # --------------------------------------------------------------
        # Live display data
        # --------------------------------------------------------------

        # These contain already-averaged display points rather than
        # the original ADC samples.
        self._live_time = deque()
        self._live_current = deque()
        self._live_power = deque()

        self._live_time_offset = 0.0

        # --------------------------------------------------------------
        # Complete continuous-run statistics
        # --------------------------------------------------------------

        self._total_current_sum = 0.0
        self._total_power_sum = 0.0
        self._total_sample_count = 0

        self._peak_current = 0.0
        self._peak_power = 0.0
        self._energy = 0.0
        self._duration = 0.0

        # Tk after() job used for live updates.
        self._live_refresh_job = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

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
        frame.grid(
            row=0,
            column=0,
            sticky="ns",
            padx=(0, 15),
        )

        self._build_configuration(frame)
        self._build_controls(frame)
        self._build_status(frame)

    def _build_configuration(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text="Profile Configuration",
            padding=10,
        )
        frame.pack(
            fill="x",
            pady=(0, 10),
        )

        fields = [
            ("Voltage", self.voltage, "V"),
            ("Current limit", self.current_limit, "A"),
            ("Settle time", self.settle_time, "s"),
            ("Sample rate", self.sample_rate, "Hz"),
            ("Sample count", self.sample_count, ""),
            (
                "Display granularity",
                self.display_granularity,
                "s",
            ),
        ]

        for row, (label, variable, unit) in enumerate(fields):
            ttk.Label(
                frame,
                text=f"{label}:",
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 10),
                pady=3,
            )

            ttk.Entry(
                frame,
                textvariable=variable,
                width=15,
            ).grid(
                row=row,
                column=1,
                sticky="w",
                pady=3,
            )

            if unit:
                ttk.Label(
                    frame,
                    text=unit,
                ).grid(
                    row=row,
                    column=2,
                    sticky="w",
                    padx=(5, 0),
                )

    def _build_controls(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(
            fill="x",
            pady=(0, 10),
        )

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        self.run_button = ttk.Button(
            frame,
            text="Run Profile",
            command=self.start_profile,
        )
        self.run_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 3),
        )

        self.continuous_button = ttk.Button(
            frame,
            text="Continuous",
            command=self.start_continuous_profile,
        )
        self.continuous_button.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=3,
        )

        self.stop_button = ttk.Button(
            frame,
            text="Stop",
            command=self.stop_profile,
            state="disabled",
        )
        self.stop_button.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(3, 0),
        )

    def _build_status(self, parent):
        frame = ttk.LabelFrame(
            parent,
            text="Status",
            padding=10,
        )
        frame.pack(fill="x")

        ttk.Label(
            frame,
            textvariable=self.status,
        ).pack(anchor="w")

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def _build_result(self):
        frame = ttk.LabelFrame(
            self,
            text="Result",
            padding=10,
        )
        frame.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.figure = Figure(
            figsize=(7, 5),
            dpi=100,
        )

        self.current_ax = self.figure.add_subplot(211)
        self.power_ax = self.figure.add_subplot(
            212,
            sharex=self.current_ax,
        )

        self.current_ax.set_title("Power Profile")
        self.current_ax.set_ylabel("Current (mA)")
        self.current_ax.grid(
            True,
            alpha=0.3,
        )

        self.power_ax.set_xlabel("Time (s)")
        self.power_ax.set_ylabel("Power (mW)")
        self.power_ax.grid(
            True,
            alpha=0.3,
        )

        self.current_line, = self.current_ax.plot(
            [],
            [],
            linewidth=1.5,
        )

        self.power_line, = self.power_ax.plot(
            [],
            [],
            linewidth=1.5,
        )

        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=frame,
        )

        self.canvas.get_tk_widget().grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self._build_statistics(frame)

        self.figure.tight_layout()

    def _build_statistics(self, parent):
        frame = ttk.Frame(parent)
        frame.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

        self.average_current = tk.StringVar(value="-")
        self.peak_current = tk.StringVar(value="-")
        self.average_power = tk.StringVar(value="-")
        self.peak_power = tk.StringVar(value="-")
        self.energy = tk.StringVar(value="-")
        self.duration = tk.StringVar(value="-")

        statistics = [
            ("Average current", self.average_current),
            ("Peak current", self.peak_current),
            ("Average power", self.average_power),
            ("Peak power", self.peak_power),
            ("Energy", self.energy),
            ("Duration", self.duration),
        ]

        for index, (label, variable) in enumerate(statistics):
            row = index // 2
            column = (index % 2) * 2

            ttk.Label(
                frame,
                text=f"{label}:",
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0, 5),
                pady=2,
            )

            ttk.Label(
                frame,
                textvariable=variable,
            ).grid(
                row=row,
                column=column + 1,
                sticky="w",
                padx=(0, 20),
                pady=2,
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _get_configuration(self):
        try:
            voltage = self.voltage.get()
            current_limit = self.current_limit.get()
            settle_time = self.settle_time.get()
            sample_rate = self.sample_rate.get()
            sample_count = self.sample_count.get()
            display_granularity = self.display_granularity.get()

            if voltage < 0:
                raise ValueError(
                    "Voltage must be non-negative"
                )

            if current_limit <= 0:
                raise ValueError(
                    "Current limit must be greater than zero"
                )

            if settle_time < 0:
                raise ValueError(
                    "Settle time must be non-negative"
                )

            if sample_rate <= 0:
                raise ValueError(
                    "Sample rate must be greater than zero"
                )

            if sample_count <= 0:
                raise ValueError(
                    "Sample count must be greater than zero"
                )

            if display_granularity <= 0:
                raise ValueError(
                    "Display granularity must be greater than zero"
                )

            return (
                voltage,
                current_limit,
                settle_time,
                sample_rate,
                sample_count,
                display_granularity,
            )

        except (tk.TclError, ValueError) as exc:
            self.status.set(str(exc))
            return None

    # ------------------------------------------------------------------
    # Fixed profile
    # ------------------------------------------------------------------

    def start_profile(self):
        if self._worker is not None:
            return

        configuration = self._get_configuration()

        if configuration is None:
            return

        self._continuous = False
        self._clear_result()

        self._stop_event = threading.Event()

        self._set_running(True)

        self.status.set("Running profile...")

        self._worker = threading.Thread(
            target=self._run_profile,
            args=configuration,
            daemon=True,
        )

        self._worker.start()

    def _run_profile(
        self,
        voltage,
        current_limit,
        settle_time,
        sample_rate,
        sample_count,
        display_granularity,
    ):
        try:
            result = self.controller.run_power_profile(
                voltage=voltage,
                current_limit=current_limit,
                settle_time=settle_time,
                sample_rate=sample_rate,
                sample_count=sample_count,
            )

        except Exception as exc:
            self.after(
                0,
                lambda exc=exc: self._profile_error(exc),
            )

        else:
            self.after(
                0,
                lambda result=result: self._profile_complete(
                    result
                ),
            )

        finally:
            self.after(
                0,
                self._worker_finished,
            )

    # ------------------------------------------------------------------
    # Continuous profile
    # ------------------------------------------------------------------

    def start_continuous_profile(self):
        if self._worker is not None:
            return

        configuration = self._get_configuration()

        if configuration is None:
            return

        self._continuous = True
        self._clear_result()

        self._stop_event = threading.Event()

        self._set_running(True)

        self.status.set(
            "Running continuous profile..."
        )

        self._worker = threading.Thread(
            target=self._run_continuous_profile,
            args=configuration,
            daemon=True,
        )

        self._worker.start()

        self._schedule_live_refresh()

    def _run_continuous_profile(
        self,
        voltage,
        current_limit,
        settle_time,
        sample_rate,
        sample_count,
        display_granularity,
    ):
        try:
            self.controller.run_power_profile_continuous(
                voltage=voltage,
                current_limit=current_limit,
                settle_time=settle_time,
                sample_rate=sample_rate,
                sample_count=sample_count,
                on_capture=lambda capture: self._capture_complete(
                    capture,
                    display_granularity,
                ),
                stop_event=self._stop_event,
            )

        except Exception as exc:
            self.after(
                0,
                lambda exc=exc: self._profile_error(exc),
            )

        else:
            self.after(
                0,
                self._continuous_complete,
            )

        finally:
            self.after(
                0,
                self._worker_finished,
            )

    def _capture_complete(
        self,
        capture: PowerCapture,
        granularity: float,
    ):
        """
        Called from the continuous profile worker thread.

        This method must not access Tkinter objects.
        """

        time_values, current_values, power_values = (
            self._average_bins(
                capture.time,
                capture.current,
                capture.power,
                granularity=granularity,
            )
        )

        if len(time_values) == 0:
            return

        current = np.asarray(
            capture.current,
            dtype=float,
        )

        power = np.asarray(
            capture.power,
            dtype=float,
        )

        with self._data_lock:
            # Offset this capture so that continuous captures form
            # one continuous time axis.
            time_values = (
                time_values + self._live_time_offset
            )

            self._live_time_offset = float(
                time_values[-1] + granularity
            )

            for time_value, current_value, power_value in zip(
                time_values,
                current_values,
                power_values,
            ):
                self._live_time.append(
                    float(time_value)
                )
                self._live_current.append(
                    float(current_value)
                )
                self._live_power.append(
                    float(power_value)
                )

            # Keep only approximately LIVE_WINDOW seconds.
            cutoff = (
                self._live_time_offset
                - self.LIVE_WINDOW
            )

            while (
                self._live_time
                and self._live_time[0] < cutoff
            ):
                self._live_time.popleft()
                self._live_current.popleft()
                self._live_power.popleft()

            # Complete-run statistics.
            if len(current):
                self._total_current_sum += float(
                    np.sum(current)
                )

                self._peak_current = max(
                    self._peak_current,
                    float(np.max(current)),
                )

            if len(power):
                self._total_power_sum += float(
                    np.sum(power)
                )

                self._peak_power = max(
                    self._peak_power,
                    float(np.max(power)),
                )

            self._total_sample_count += len(current)

            self._energy += float(
                capture.energy
            )

            self._duration += float(
                capture.duration
            )

    # ------------------------------------------------------------------
    # Live display
    # ------------------------------------------------------------------

    def _schedule_live_refresh(self):
        if self._live_refresh_job is not None:
            return

        self._live_refresh_job = self.after(
            self.LIVE_UPDATE_INTERVAL,
            self._refresh_live_display,
        )

    def _refresh_live_display(self):
        self._live_refresh_job = None

        if not self._continuous:
            return

        self._update_live_plot()
        self._update_live_statistics()

        with self._data_lock:
            duration = self._duration

        self.status.set(
            "Capturing · "
            f"{duration:.2f} s · "
            f"{self.average_current.get()} · "
            f"{self.average_power.get()}"
        )

        self._schedule_live_refresh()

    def _update_live_plot(self):
        with self._data_lock:
            if not self._live_time:
                return

            # Make copies while holding the lock.
            time_values = np.asarray(
                list(self._live_time),
                dtype=float,
            )

            current_values = np.asarray(
                list(self._live_current),
                dtype=float,
            )

            power_values = np.asarray(
                list(self._live_power),
                dtype=float,
            )

        end_time = float(
            time_values[-1]
        )

        start_time = max(
            0.0,
            end_time - self.LIVE_WINDOW,
        )

        self.current_line.set_data(
            time_values,
            current_values * 1000,
        )

        self.power_line.set_data(
            time_values,
            power_values * 1000,
        )

        x_max = max(
            self.LIVE_WINDOW,
            end_time,
        )

        self.current_ax.set_xlim(
            start_time,
            x_max,
        )

        self.power_ax.set_xlim(
            start_time,
            x_max,
        )

        self.current_ax.relim()
        self.current_ax.autoscale(
            axis="y",
            tight=False,
        )

        self.power_ax.relim()
        self.power_ax.autoscale(
            axis="y",
            tight=False,
        )

        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Completion / cancellation
    # ------------------------------------------------------------------

    def _profile_complete(
        self,
        result: PowerProfileResult,
    ):
        self.result = result

        self.status.set(
            "Profile complete"
        )

        self._update_plot()
        self._update_statistics()

        if self.on_result is not None:
            self.on_result(result)

    def _continuous_complete(self):
        if (
            self._stop_event is not None
            and self._stop_event.is_set()
        ):
            with self._data_lock:
                duration = self._duration

            self.status.set(
                f"Profile stopped · "
                f"{duration:.2f} s"
            )

        else:
            self.status.set(
                "Continuous profile complete"
            )

        # Final update before disabling continuous mode.
        self._update_live_plot()
        self._update_live_statistics()

        self._continuous = False

    def _profile_error(self, exc):
        self.status.set(
            f"Error: {exc}"
        )

        self._continuous = False

    def stop_profile(self):
        if self._worker is None:
            return

        if self._stop_event is not None:
            self.status.set(
                "Stopping..."
            )

            self._stop_event.set()

    def _worker_finished(self):
        """
        Called on the Tk thread after the worker exits.

        This method deliberately does not change _continuous.
        The completion handler owns the continuous-mode lifecycle.
        """

        self._worker = None
        self._stop_event = None

        self._set_running(False)

    def _set_running(self, running):
        state = (
            "disabled"
            if running
            else "normal"
        )

        stop_state = (
            "normal"
            if running
            else "disabled"
        )

        self.run_button.configure(
            state=state
        )

        self.continuous_button.configure(
            state=state
        )

        self.stop_button.configure(
            state=stop_state
        )

    # ------------------------------------------------------------------
    # Result display
    # ------------------------------------------------------------------

    def _clear_result(self):
        self.result = None

        with self._data_lock:
            self._live_time.clear()
            self._live_current.clear()
            self._live_power.clear()

            self._live_time_offset = 0.0

            self._total_current_sum = 0.0
            self._total_power_sum = 0.0
            self._total_sample_count = 0

            self._peak_current = 0.0
            self._peak_power = 0.0
            self._energy = 0.0
            self._duration = 0.0

        self.current_line.set_data(
            [],
            [],
        )

        self.power_line.set_data(
            [],
            [],
        )

        self.current_ax.set_xlim(
            0.0,
            self.LIVE_WINDOW,
        )

        self.power_ax.set_xlim(
            0.0,
            self.LIVE_WINDOW,
        )

        self.current_ax.relim()
        self.current_ax.autoscale(
            axis="y"
        )

        self.power_ax.relim()
        self.power_ax.autoscale(
            axis="y"
        )

        self._clear_statistics()

        self.canvas.draw_idle()

    def _update_plot(self):
        if self.result is None:
            return

        capture = self.result.capture

        time_values = np.asarray(
            capture.time,
            dtype=float,
        )

        current_values = np.asarray(
            capture.current,
            dtype=float,
        )

        power_values = np.asarray(
            capture.power,
            dtype=float,
        )

        if len(time_values) == 0:
            return

        self.current_line.set_data(
            time_values,
            current_values * 1000,
        )

        self.power_line.set_data(
            time_values,
            power_values * 1000,
        )

        duration = float(
            capture.duration
        )

        self.current_ax.set_xlim(
            0.0,
            max(
                self.LIVE_WINDOW,
                duration,
            ),
        )

        self.power_ax.set_xlim(
            0.0,
            max(
                self.LIVE_WINDOW,
                duration,
            ),
        )

        self.current_ax.relim()
        self.current_ax.autoscale(
            axis="y"
        )

        self.power_ax.relim()
        self.power_ax.autoscale(
            axis="y"
        )

        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def _update_statistics(self):
        if self.result is None:
            return

        capture = self.result.capture

        self.average_current.set(
            f"{capture.average_current * 1000:.3f} mA"
        )

        self.peak_current.set(
            f"{capture.peak_current * 1000:.3f} mA"
        )

        self.average_power.set(
            f"{capture.average_power * 1000:.3f} mW"
        )

        self.peak_power.set(
            f"{capture.peak_power * 1000:.3f} mW"
        )

        self.energy.set(
            f"{capture.energy * 1000:.3f} mJ"
        )

        self.duration.set(
            f"{capture.duration * 1000:.3f} ms"
        )

    def _update_live_statistics(self):
        with self._data_lock:
            if self._total_sample_count == 0:
                return

            average_current = (
                self._total_current_sum
                / self._total_sample_count
            )

            average_power = (
                self._total_power_sum
                / self._total_sample_count
            )

            peak_current = self._peak_current
            peak_power = self._peak_power
            energy = self._energy
            duration = self._duration

        self.average_current.set(
            f"{average_current * 1000:.3f} mA"
        )

        self.peak_current.set(
            f"{peak_current * 1000:.3f} mA"
        )

        self.average_power.set(
            f"{average_power * 1000:.3f} mW"
        )

        self.peak_power.set(
            f"{peak_power * 1000:.3f} mW"
        )

        self.energy.set(
            f"{energy * 1000:.3f} mJ"
        )

        self.duration.set(
            f"{duration:.3f} s"
        )

    def _clear_statistics(self):
        self.average_current.set("-")
        self.peak_current.set("-")
        self.average_power.set("-")
        self.peak_power.set("-")
        self.energy.set("-")
        self.duration.set("-")

    # ------------------------------------------------------------------
    # Data reduction
    # ------------------------------------------------------------------

    @staticmethod
    def _average_bins(
        time_values,
        *values,
        granularity,
    ):
        """
        Average samples into fixed-width time bins.

        Returns:
            averaged_time,
            averaged_value_1,
            averaged_value_2,
            ...
        """

        time_values = np.asarray(
            time_values,
            dtype=float,
        )

        if len(time_values) == 0:
            return (
                np.asarray([]),
                *(
                    np.asarray(value)
                    for value in values
                ),
            )

        values = [
            np.asarray(value, dtype=float)
            for value in values
        ]

        bins = np.floor(
            time_values / granularity
        )

        unique_bins = np.unique(bins)

        averaged_time = []
        averaged_values = [
            []
            for _ in values
        ]

        for bin_index in unique_bins:
            mask = bins == bin_index

            averaged_time.append(
                np.mean(
                    time_values[mask]
                )
            )

            for index, value in enumerate(values):
                averaged_values[index].append(
                    np.mean(
                        value[mask]
                    )
                )

        return (
            np.asarray(averaged_time),
            *(
                np.asarray(value)
                for value in averaged_values
            ),
        )
