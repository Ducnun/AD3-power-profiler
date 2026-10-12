import tkinter as tk
from tkinter import ttk

from lab.controller import LabController

from gui.navigation_panel import NavigationPanel
from gui.panels.psu_panel import PSUPanel
from gui.panels.ad3_panel import AD3Panel

# Measurement panels
from gui.panels.power_sweep_panel import PowerSweepPanel
from gui.panels.power_profile_panel import PowerProfilePanel


class MainWindow:
    """
    Main laboratory control application window.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Lab Control")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)

        self.controller = LabController()

        self.current_panel = None

        self.pages = {
            "instrument.psu": PSUPanel,
            "instrument.ad3": AD3Panel,
            "test.power_sweep": PowerSweepPanel,
            "test.power_profile": PowerProfilePanel
        }

        self._build_ui()

        # Connect before displaying instrument-specific pages.
        self._connect()

    def _build_ui(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.navigation = NavigationPanel(self.root, on_select=self.show_page)
        self.navigation.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)

        self.content = ttk.Frame(self.root, padding=10)
        self.content.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.placeholder = ttk.Label(self.content, text="Select an instrument or test", anchor="center")
        self.placeholder.grid(row=0, column=0, sticky="nsew")

    def _connect(self):
        try:
            self.controller.connect()
        except Exception as exc:
            self.placeholder.configure(text=f"Connection error:\n{exc}")

    def show_page(self, page_id):
        page_class = self.pages.get(page_id)

        if page_class is None:
            return

        if self.current_panel is not None:
            self.current_panel.destroy()

        self.placeholder.grid_remove()

        self.current_panel = page_class(self.content, controller=self.controller)
        self.current_panel.grid(row=0, column=0, sticky="nsew")

    def close(self):
        self.controller.disconnect()
        self.root.destroy()
