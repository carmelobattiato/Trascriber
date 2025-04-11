# --- START OF REVISED header_frame.py ---

import tkinter as tk
from tkinter import ttk
import typing

if typing.TYPE_CHECKING:
    from gui import ModernTranscriptionApp

class HeaderFrame:
    """Manages the header section of the main GUI."""

    def __init__(self, parent, gui_app: 'ModernTranscriptionApp'):
        self.parent = parent
        self.gui_app = gui_app # For translations and language var access

        self.frame = ttk.Frame(parent, style="Card.TFrame", padding=(20, 10, 20, 10))
        self.frame.pack(side=tk.TOP, fill=tk.X) # Pack directly here
        self.frame.columnconfigure(1, weight=1) # Allow subtitle to take space

        # --- Widgets (Initialize without text where needed) ---
        self.app_title_label = ttk.Label(self.frame, text="", style="Heading.TLabel") # TEXT REMOVED
        self.app_title_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.app_subtitle_label = ttk.Label(self.frame, text="", style="TLabel") # TEXT REMOVED
        self.app_subtitle_label.grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Language Selection Frame (aligned right in header)
        lang_select_frame = ttk.Frame(self.frame, style="Card.TFrame") # Use Card style for consistency
        lang_select_frame.grid(row=0, column=2, sticky="e")

        self.lang_select_label = ttk.Label(lang_select_frame, text="") # TEXT REMOVED
        self.lang_select_label.pack(side=tk.LEFT, padx=(0, 5))

        # Use the language variable from the main app
        self.lang_options = list(self.gui_app.translations.keys()) # Get keys directly
        self.language_selector = ttk.Combobox(lang_select_frame,
                                              textvariable=self.gui_app.current_language, # Use main app's var
                                              values=self.lang_options,
                                              state="readonly", width=10)
        # Ensure the value set matches one of the available keys
        current_lang = self.gui_app.current_language.get()
        if current_lang not in self.lang_options:
            current_lang = "English" # Fallback to English if saved lang not found
            self.gui_app.current_language.set(current_lang)
        self.language_selector.set(current_lang) # Set initial value

        # Binding happens in main app, no need to bind here if using trace
        # self.language_selector.bind("<<ComboboxSelected>>", self.gui_app.on_language_select)
        self.language_selector.pack(side=tk.LEFT)

    def update_ui_text(self):
        """Updates text elements within the header based on the current language."""
        if not self.frame.winfo_exists(): return
        try:
            self.app_title_label.config(text=self.gui_app.translate("app_title"))
            self.app_subtitle_label.config(text=self.gui_app.translate("app_subtitle"))
            self.lang_select_label.config(text=self.gui_app.translate("language_select_label"))
            # Combobox value updates automatically via textvariable
        except tk.TclError as e:
            print(f"HeaderFrame: TclError during update_ui_text: {e}", file=sys.__stderr__)
        except Exception as e:
            import traceback
            print(f"HeaderFrame: Error during update_ui_text: {e}\n{traceback.format_exc()}", file=sys.__stderr__)


# --- END OF REVISED header_frame.py ---