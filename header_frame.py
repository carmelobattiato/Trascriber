# --- START OF FILE header_frame.py ---

import tkinter as tk
from tkinter import ttk

class HeaderFrame:
    """Manages the header section of the main GUI."""

    def __init__(self, parent, gui_app):
        self.parent = parent
        self.gui_app = gui_app # For translations and language var access

        self.frame = ttk.Frame(parent, style="Card.TFrame", padding=(20, 10, 20, 10))
        self.frame.pack(side=tk.TOP, fill=tk.X) # Pack directly here
        self.frame.columnconfigure(1, weight=1) # Allow subtitle to take space

        # --- Widgets ---
        self.app_title_label = ttk.Label(self.frame, text="", style="Heading.TLabel")
        self.app_title_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.app_subtitle_label = ttk.Label(self.frame, text="", style="TLabel")
        self.app_subtitle_label.grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Language Selection Frame (aligned right in header)
        lang_select_frame = ttk.Frame(self.frame, style="Card.TFrame") # Use Card style for consistency
        lang_select_frame.grid(row=0, column=2, sticky="e")

        self.lang_select_label = ttk.Label(lang_select_frame, text="")
        self.lang_select_label.pack(side=tk.LEFT, padx=(0, 5))

        # Use the language variable from the main app
        self.lang_options = {"English": "English", "Italiano": "Italiano", "Français": "Français", "中文": "中文"}
        self.language_selector = ttk.Combobox(lang_select_frame,
                                              textvariable=self.gui_app.current_language, # Use main app's var
                                              values=list(self.lang_options.keys()),
                                              state="readonly", width=10)
        self.language_selector.set(self.gui_app.current_language.get()) # Set initial value
        self.language_selector.bind("<<ComboboxSelected>>", self.gui_app.on_language_select) # Bind to main app's method
        self.language_selector.pack(side=tk.LEFT)

    def update_ui_text(self):
        """Updates text elements within the header based on the current language."""
        if not self.frame.winfo_exists(): return
        self.app_title_label.config(text=self.gui_app.translate("app_title"))
        self.app_subtitle_label.config(text=self.gui_app.translate("app_subtitle"))
        self.lang_select_label.config(text=self.gui_app.translate("language_select_label"))
        # Combobox value updates automatically via textvariable

# --- END OF FILE header_frame.py ---