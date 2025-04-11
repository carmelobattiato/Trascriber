# --- START OF FILE status_bar.py ---

import tkinter as tk
from tkinter import ttk

class StatusBar:
    """Manages the status bar at the bottom of the GUI."""

    def __init__(self, parent, gui_app):
        self.parent = parent
        self.gui_app = gui_app # For status_var access

        self.frame = ttk.Frame(parent, style="Status.TFrame", borderwidth=1, relief='groove')
        self.frame.pack(side=tk.BOTTOM, fill=tk.X) # Pack directly

        # Use the main app's status variable
        self.status_label = ttk.Label(self.frame, textvariable=self.gui_app.status_var, style="Status.TLabel", anchor="w")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)

    # No specific update_ui_text needed here as the label uses textvariable

# --- END OF FILE status_bar.py ---