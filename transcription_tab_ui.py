# --- START OF FILE transcription_tab_ui.py ---

import tkinter as tk
from tkinter import ttk, scrolledtext
import os # For path operations if needed directly (e.g., tooltips)
import sys # For platform check

class TranscriptionTabUI:
    """Manages the UI elements for the Transcription Tab."""

    def __init__(self, parent_notebook, gui_app):
        self.parent_notebook = parent_notebook
        self.gui_app = gui_app # Access main app for translations, vars, methods

        # --- Main Frame for the Tab ---
        self.frame = ttk.Frame(parent_notebook, padding="10")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(4, weight=1) # Make results notebook expand

        # --- Variables (References to main app's variables) ---
        # We will access main app's variables via self.gui_app.var_name
        # Or, we can store references if preferred, but accessing via gui_app is often cleaner
        self.file_path_var = self.gui_app.file_path # Store ref if used often locally
        self.model_var = self.gui_app.model_var
        self.transcription_language_var = self.gui_app.transcription_language_var
        self.use_gpu_var = self.gui_app.use_gpu_var
        self.progress_var = self.gui_app.progress_var
        self.current_task_var = self.gui_app.current_task # Reference to main app's task var
        self.model_desc_var = self.gui_app.model_desc_var

        # --- Create Widgets ---
        self._create_widgets()

    def _create_widgets(self):
        # File Selection
        self.file_frame = ttk.LabelFrame(self.frame, text="", padding=10)
        self.file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.file_frame.columnconfigure(1, weight=1) # Make entry expand

        self.wav_file_label = ttk.Label(self.file_frame, text="")
        self.wav_file_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path_var, width=60)
        self.file_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.browse_button = ttk.Button(self.file_frame, text="", command=self.gui_app.select_file, style="Action.TButton")
        self.browse_button.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # Options
        self.options_frame = ttk.LabelFrame(self.frame, text="", padding=10)
        self.options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.options_frame.columnconfigure(2, weight=1) # Description takes remaining space

        self.model_label = ttk.Label(self.options_frame, text="")
        self.model_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        models = ["tiny", "base", "small", "medium", "large"]
        self.model_combobox = ttk.Combobox(self.options_frame, textvariable=self.model_var, values=models, state="readonly", width=15)
        self.model_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.model_combobox.set(self.model_var.get()) # Set initial value
        self.model_desc_label = ttk.Label(self.options_frame, textvariable=self.model_desc_var, anchor="w")
        self.model_desc_label.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
        self.model_combobox.bind("<<ComboboxSelected>>", self.gui_app.update_model_description) # Bind to main app method

        self.transcription_language_label = ttk.Label(self.options_frame, text="")
        self.transcription_language_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.transcription_languages = ["italiano", "inglese", "francese", "tedesco", "spagnolo", "giapponese", "cinese"]
        self.language_combobox = ttk.Combobox(self.options_frame, textvariable=self.transcription_language_var,
                                            values=self.transcription_languages, state="readonly", width=15)
        self.language_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.language_combobox.set(self.transcription_language_var.get()) # Set initial value

        self.acceleration_label = ttk.Label(self.options_frame, text="")
        self.acceleration_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.gpu_check = ttk.Checkbutton(self.options_frame, text="", variable=self.use_gpu_var)
        self.gpu_check.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        # Tooltip binding needs the main app's methods
        self.gpu_check.bind("<Enter>", self.gui_app.show_gpu_tooltip)
        # Leave binding is handled within the main app's tooltip logic


        # Buttons
        buttons_frame = ttk.Frame(self.frame)
        buttons_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))

        self.start_button = ttk.Button(buttons_frame, text="", command=self.gui_app.start_transcription, style="Primary.TButton")
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.stop_button = ttk.Button(buttons_frame, text="", command=self.gui_app.stop_transcription, style="Action.TButton", state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)

        action_buttons_right = ttk.Frame(buttons_frame)
        action_buttons_right.pack(side=tk.RIGHT)
        self.save_button = ttk.Button(action_buttons_right, text="", command=self.gui_app.save_transcription, style="Action.TButton")
        self.save_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.copy_button = ttk.Button(action_buttons_right, text="", command=self.gui_app.copy_to_clipboard, style="Action.TButton")
        self.copy_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Progress
        progress_frame = ttk.Frame(self.frame)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        progress_frame.columnconfigure(0, weight=1)

        # Use the main app's current_task variable
        self.current_task_label = ttk.Label(progress_frame, textvariable=self.current_task_var, anchor="w")
        self.current_task_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                         mode="indeterminate", length=100, style="TProgressbar")
        self.progress_bar.grid(row=1, column=0, sticky="ew")


        # Results Notebook (Transcription Text / Console)
        self.results_notebook = ttk.Notebook(self.frame)
        self.results_notebook.grid(row=4, column=0, sticky="nsew", pady=(0, 5)) # Reduced bottom padding

        # -- Transcription Result Tab --
        transcription_result_frame = ttk.Frame(self.results_notebook, padding=10)
        transcription_result_frame.pack(fill=tk.BOTH, expand=True)
        transcription_result_frame.columnconfigure(0, weight=1)
        transcription_result_frame.rowconfigure(1, weight=1)
        self.results_notebook.add(transcription_result_frame, text="") # Text set in update_ui_text

        self.transcription_result_label = ttk.Label(transcription_result_frame, text="")
        self.transcription_result_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        result_text_frame = ttk.Frame(transcription_result_frame, borderwidth=1, relief="sunken")
        result_text_frame.grid(row=1, column=0, sticky="nsew")
        result_text_frame.rowconfigure(0, weight=1)
        result_text_frame.columnconfigure(0, weight=1)
        # IMPORTANT: Store reference to the text widget itself for the main app
        self.result_text = scrolledtext.ScrolledText(result_text_frame, wrap=tk.WORD, width=80, height=10,
                                     font=("Segoe UI", 11), background="white", foreground=self.gui_app.text_color, # Use style color
                                     borderwidth=0, relief="flat")
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # -- Console Tab --
        console_frame = ttk.Frame(self.results_notebook, padding=10)
        console_frame.pack(fill=tk.BOTH, expand=True)
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(1, weight=1)
        self.results_notebook.add(console_frame, text="") # Text set in update_ui_text

        self.console_output_label = ttk.Label(console_frame, text="")
        self.console_output_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        console_text_frame = ttk.Frame(console_frame, borderwidth=1, relief="sunken")
        console_text_frame.grid(row=1, column=0, sticky="nsew")
        console_text_frame.rowconfigure(0, weight=1)
        console_text_frame.columnconfigure(0, weight=1)
        # IMPORTANT: Store reference to the console widget itself for the main app
        self.console_output = scrolledtext.ScrolledText(console_text_frame, wrap=tk.WORD, width=80, height=10,
                                     background="#f0f0f0", foreground="#333",
                                     font=("Consolas", 10),
                                     borderwidth=0, relief="flat")
        self.console_output.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

    def update_ui_text(self):
        """Updates text elements within the transcription tab."""
        if not self.frame.winfo_exists(): return

        # Frame Titles
        self.file_frame.config(text=self.gui_app.translate("select_audio_frame"))
        self.options_frame.config(text=self.gui_app.translate("options_frame"))

        # Labels
        self.wav_file_label.config(text=self.gui_app.translate("wav_file_label"))
        self.model_label.config(text=self.gui_app.translate("model_label"))
        self.transcription_language_label.config(text=self.gui_app.translate("language_label"))
        self.acceleration_label.config(text=self.gui_app.translate("acceleration_label"))
        self.transcription_result_label.config(text=self.gui_app.translate("transcription_result_label"))
        self.console_output_label.config(text=self.gui_app.translate("console_output_label"))
        self.gpu_check.config(text=self.gui_app.translate("use_gpu_checkbox")) # Checkbutton text

        # Buttons
        self.browse_button.config(text=self.gui_app.translate("browse_button"))
        self.start_button.config(text=self.gui_app.translate("start_button"))
        self.stop_button.config(text=self.gui_app.translate("stop_button"))
        self.copy_button.config(text=self.gui_app.translate("copy_button"))
        self.save_button.config(text=self.gui_app.translate("save_button"))

        # Results Notebook Tabs
        try:
             if len(self.results_notebook.tabs()) >= 2:
                self.results_notebook.tab(0, text=self.gui_app.translate("tab_transcription")) # Text Result
                self.results_notebook.tab(1, text=self.gui_app.translate("tab_console"))      # Console
        except tk.TclError as e:
             print(f"Error updating results notebook tabs: {e}")

        # Update model description (called separately by main app during language change too)
        # self.gui_app.update_model_description() # Or let main app handle this call


# --- END OF FILE transcription_tab_ui.py ---