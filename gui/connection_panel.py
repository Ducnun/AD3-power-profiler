from tkinter import messagebox
from tkinter import ttk


class ConnectionPanel(ttk.LabelFrame):
    """
    Connection controls for the laboratory hardware.

    Hardware lifecycle is owned entirely by LabController.
    """
    def __init__(self, parent, *, controller, on_connection_changed=None):
        super().__init__(parent, text="Lab Connection", padding=10)
        self.controller = controller
        self.on_connection_changed = on_connection_changed
        self._build_ui()
        self._update_status()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        ttk.Label(self, text="Status:").grid(
            row=0, column=0, sticky="w", padx=(0, 10))

        self.status_label = ttk.Label(self, text="Disconnected")
        self.status_label.grid(row=0, column=1, sticky="w")
        self.connect_button = ttk.Button(self, text="Connect", command=self._connect)
        self.connect_button.grid(row=0, column=2, padx=(20, 5))
        self.disconnect_button = ttk.Button(self, text="Disconnect", command=self._disconnect, state="disabled")
        self.disconnect_button.grid(row=0, column=3)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _connect(self):
        try:
            self.controller.connect()
        except Exception as exc:
            messagebox.showerror("Connection Error", str(exc), parent=self)
            return

        self._update_status()
        self._notify_connection_changed()

    def _disconnect(self):
        try:
            self.controller.disconnect()
        except Exception as exc:
            messagebox.showerror("Disconnect Error", str(exc), parent=self)
            return

        self._update_status()
        self._notify_connection_changed()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _update_status(self):
        if self.controller.connected:
            self.status_label.configure(text="Connected", foreground="green")
            self.connect_button.configure(state="disabled")
            self.disconnect_button.configure(state="normal")

        else:
            self.status_label.configure(text="Disconnected", foreground="red")
            self.connect_button.configure(state="normal")
            self.disconnect_button.configure(state="disabled")

    def _notify_connection_changed(self):
        if self.on_connection_changed is not None:
            self.on_connection_changed(self.controller.connected)
