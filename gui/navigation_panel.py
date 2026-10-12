import tkinter as tk
from tkinter import ttk
from collections.abc import Callable


class NavigationPanel(ttk.Frame):
    """
    Navigation tree for instruments and laboratory tests.

    Calls on_select with the selected page identifier.
    """
    def __init__(self, parent, *, on_select: Callable[[str], None]):
        super().__init__(parent)
        self.on_select = on_select
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(self, show="tree", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.configure(yscrollcommand=scrollbar.set)
        self._populate()
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)

    def _populate(self):
        instruments = self.tree.insert("", "end", iid="category.instruments", text="Instruments", open=True)
        self.tree.insert(instruments, "end", iid="instrument.psu", text="Power Supply")
        self.tree.insert(instruments, "end", iid="instrument.ad3", text="Analog Discovery 3")

        tests = self.tree.insert("", "end", iid="category.tests", text="Tests", open=True)
        self.tree.insert(tests, "end", iid="test.power_sweep", text="Power Sweep")
        self.tree.insert(tests, "end", iid="test.power_profile", text="Power Profiler")

    def _selection_changed(self, _event):
        selection = self.tree.selection()

        if not selection:
            return

        page_id = selection[0]

        # Ignore category nodes.
        if page_id.startswith("category."):
            return

        self.on_select(page_id)