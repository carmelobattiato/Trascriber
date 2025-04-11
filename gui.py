# --- START OF REVISED gui.py ---

import tkinter as tk
from tkinter import ttk, messagebox
import io
import os
import sys
import typing

# Backend/Logic Imports
from transcriber import AudioTranscriber
from llm_processor import LLMProcessor

# UI Component Imports
from header_frame import HeaderFrame
from transcription_tab_ui import TranscriptionTabUI
from recorder_tab import RecorderTab
from llm_tab import LLMTab
from status_bar import StatusBar

# Utility/Data Imports
from config_manager import ConfigManager
from translations import translations_dict, model_descriptions_dict

# --- Console Output Redirector ---
# (ConsoleOutput class remains the same)
class ConsoleOutput(io.StringIO):
    def __init__(self, text_widget): super().__init__(); self.text_widget = text_widget
    def write(self, message):
        try:
            if self.text_widget and isinstance(self.text_widget, tk.Widget) and self.text_widget.winfo_exists(): self.text_widget.after_idle(self._insert_text, message)
            else: print(f"Console Write Error (widget gone?): {message.strip()}", file=sys.__stderr__)
        except tk.TclError: print(f"Console Write Error (TclError): {message.strip()}", file=sys.__stderr__)
        except Exception as e: print(f"Console Write Error (General Exception): {e} - Message: {message.strip()}", file=sys.__stderr__)
        super().write(message)
    def _insert_text(self, message):
        try:
            if self.text_widget and isinstance(self.text_widget, tk.Widget) and self.text_widget.winfo_exists():
                original_state = self.text_widget.cget('state')
                if original_state == tk.DISABLED: self.text_widget.config(state=tk.NORMAL)
                self.text_widget.insert(tk.END, message); self.text_widget.see(tk.END)
                if original_state == tk.DISABLED: self.text_widget.config(state=tk.DISABLED)
        except tk.TclError: print(f"Console Insert Error (TclError - widget destroyed?): {message.strip()}", file=sys.__stderr__)
        except Exception as e: print(f"Console Insert Error (General Exception): {e} - Message: {message.strip()}", file=sys.__stderr__)
# --- End Console Output ---

class ModernTranscriptionApp:
    """Main application class, orchestrates UI components and backend logic."""

    def __init__(self, root):
        self.root = root
        self.config_manager = ConfigManager()
        self.system_type = "mac" if sys.platform == "darwin" else "windows"
        self.translations = translations_dict
        self.model_descriptions = model_descriptions_dict

        # --- Initialize Shared State Variables (with hardcoded defaults or loaded later) ---
        self.current_language = tk.StringVar(value="English") # Default, will be overwritten by config
        self.status_var = tk.StringVar()
        self.current_task = tk.StringVar(value="")
        self.file_path = tk.StringVar()
        self.model_var = tk.StringVar(value="large") # Default, overwritten by config
        self.transcription_language_var = tk.StringVar(value="italiano") # Default, overwritten by config
        self.use_gpu_var = tk.BooleanVar(value=False) # Default, overwritten by config
        self.progress_var = tk.DoubleVar(value=0)
        self.model_desc_var = tk.StringVar() # Set dynamically

        # --- Load Config & Apply Language FIRST ---
        print("Loading config...")
        self.loaded_config = self.config_manager.load_config()
        loaded_lang = self.loaded_config.get("ui_language", "English")
        self.current_language.set(loaded_lang)
        print(f"Language set to: {self.current_language.get()}")

        # Set initial status only AFTER language is definitely set
        # Will be updated again in update_ui_text
        self.status_var.set(self.translate("status_ready"))

        # --- Instantiate Backend Logic ---
        self.transcriber = AudioTranscriber(self)
        self.llm_processor = LLMProcessor()

        # --- UI Setup ---
        self.setup_ui_styles()
        print("Creating widgets...")
        self.create_widgets() # Creates components with empty text where needed
        print("Widgets created.")

        # --- Post-Widget Creation Setup ---
        # Schedule a single function to run after the current event loop iteration
        # This function will apply remaining config and perform initial UI update
        self.root.after_idle(self._post_init_setup)

        # Add trace AFTER initial setup is scheduled
        self.current_language.trace_add("write", self.change_language)
        print("Language trace added.")

        # Handle closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        print("Initialization complete.")


    def _post_init_setup(self):
        """Applies remaining config and performs initial UI updates after idle."""
        print("Running post-init setup...")
        try:
            # Apply the non-language parts of the config now that widgets exist
            self._apply_rest_of_config(self.loaded_config)

            # Set initial model description based on loaded/default model
            self._update_initial_model_description() # Uses translate

            # --- Perform the first full UI text update ---
            print("Calling initial full UI text update...")
            self.update_ui_text() # THIS IS THE KEY CALL
            print("Initial full UI text update called.")
            # -------------------------------------------

            # Setup stdout redirection (needs console widget to exist and be updated)
            self._setup_stdout_redirect()
            print("Post-init setup finished successfully.")
        except Exception as e:
            import traceback
            print(f"ERROR during post-init setup: {e}\n{traceback.format_exc()}", file=sys.__stderr__)
            messagebox.showerror("Initialization Error", f"Failed during initial setup:\n{e}")


    def _apply_rest_of_config(self, config: dict):
        """Applies non-language settings from loaded config."""
        print("Applying rest of config...")
        self.model_var.set(config.get("transcription_model", "large"))
        self.transcription_language_var.set(config.get("transcription_language", "italiano"))
        self.use_gpu_var.set(config.get("transcription_use_gpu", False))

        # Apply LLM config - now uses _apply_loaded_llm_config_to_tab which handles existence
        self._apply_loaded_llm_config_to_tab()
        print("Finished applying rest of config.")

    def _gather_current_config(self) -> dict:
        settings = {
            "ui_language": self.current_language.get(),
            "transcription_model": self.model_var.get(),
            "transcription_language": self.transcription_language_var.get(),
            "transcription_use_gpu": self.use_gpu_var.get(),
            "llm_provider": None,
            "llm_model": None,
            "llm_api_key": "", # Raw key, will be obfuscated on save
            "custom_llm_templates": {}
        }
        if hasattr(self, 'llm_tab') and self.llm_tab:
            # Safely get values from LLM tab widgets if they exist
            if hasattr(self.llm_tab, 'llm_provider_var'): settings["llm_provider"] = self.llm_tab.llm_provider_var.get()
            if hasattr(self.llm_tab, 'llm_model_var'): settings["llm_model"] = self.llm_tab.llm_model_var.get()
            if hasattr(self.llm_tab, 'llm_api_key_var'): settings["llm_api_key"] = self.llm_tab.llm_api_key_var.get()
            if hasattr(self.llm_tab, 'custom_templates'): settings["custom_llm_templates"] = self.llm_tab.custom_templates

        return settings

    def translate(self, key):
        lang_code = self.current_language.get()
        selected_lang_dict = self.translations.get(lang_code, self.translations.get('English', {})) # Fallback to English dict
        english_dict = self.translations.get('English', {})
        # Return specific language value, or English value, or the key itself as fallback
        return selected_lang_dict.get(key, english_dict.get(key, f"<{key}>"))


    def setup_ui_styles(self):
        # (Setup styles - unchanged)
        self.style = ttk.Style(); theme = 'clam';
        try: self.style.theme_use(theme)
        except tk.TclError: available = self.style.theme_names(); print(f"Theme '{theme}' not found. Available: {available}", file=sys.__stderr__); theme = available[0] if available else 'default'; self.style.theme_use(theme)
        self.primary_color="#3498db"; self.secondary_color="#2980b9"; self.bg_color="#f5f5f5"; self.text_color="#2c3e50"
        self.root.configure(bg=self.bg_color)
        default_font=("Segoe UI", 10); bold_font=("Segoe UI", 10, "bold"); heading_font=("Segoe UI", 14, "bold"); console_font=("Consolas", 10)
        self.style.configure("Card.TFrame", background=self.bg_color, relief="raised", borderwidth=1)
        self.style.configure("Primary.TButton", background=self.primary_color, foreground="white", padding=10, font=bold_font); self.style.map("Primary.TButton", background=[("active", self.secondary_color), ("disabled", "#bdc3c7")])
        self.style.configure("Action.TButton", background=self.secondary_color, foreground="white", padding=8, font=("Segoe UI", 9)); self.style.map("Action.TButton", background=[("active", self.primary_color), ("disabled", "#bdc3c7")])
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=default_font)
        self.style.configure("Heading.TLabel", background=self.bg_color, foreground=self.text_color, font=heading_font)
        self.style.configure("Status.TLabel", background="#ecf0f1", foreground=self.text_color, padding=5, relief="sunken", font=default_font)
        self.style.configure("TProgressbar", background=self.primary_color, troughcolor="#d1d1d1", thickness=10)
        self.style.configure("TCombobox", padding=5, font=default_font)
        self.style.configure("TLabelframe.Label", font=bold_font, foreground=self.text_color, background=self.bg_color)
        self.style.configure("TRadiobutton", background=self.bg_color, font=default_font)
        self.style.configure("TNotebook.Tab", font=default_font, padding=[5, 2])


    def create_widgets(self):
        """Creates the main UI structure by instantiating component classes."""
        self.header = HeaderFrame(self.root, self)
        self.main_notebook = ttk.Notebook(self.root, padding=(20, 10, 20, 10))
        self.main_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Instantiate Tabs (they will create their widgets with empty text)
        self.transcription_tab = TranscriptionTabUI(self.main_notebook, self)
        self.recorder_tab = RecorderTab(self.main_notebook, self, self.update_transcription_path_callback) # Pass self (gui_app)
        self.llm_tab = LLMTab(self.main_notebook, self, self.llm_processor)

        # Add tabs to notebook (text will be set in update_ui_text)
        self.main_notebook.add(self.transcription_tab.frame, text="")
        self.main_notebook.add(self.recorder_tab.frame, text="")
        self.main_notebook.add(self.llm_tab.frame, text="")

        self.status_bar = StatusBar(self.root, self)
        # LLM config applied in _apply_rest_of_config scheduled from _post_init_setup

    def _setup_stdout_redirect(self):
        # (Unchanged)
        try:
            if (hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'console_output') and
                    isinstance(self.transcription_tab.console_output, tk.Widget) and self.transcription_tab.console_output.winfo_exists()):
                sys.stdout = ConsoleOutput(self.transcription_tab.console_output)
                print("Standard output redirected to console widget.")
                self._print(self.translate("welcome_message") + "\n")
            else: print("Console widget not available for stdout redirection.", file=sys.__stderr__)
        except Exception as e: print(f"Error setting up stdout redirection: {e}", file=sys.__stderr__)

    def _apply_loaded_llm_config_to_tab(self):
         # Applies config to LLM Tab *after* widgets are created
         if hasattr(self, 'llm_tab') and self.llm_tab:
             print("Applying LLM config to LLM Tab widgets...")
             # Get values from the main loaded_config dictionary
             provider_to_set = self.loaded_config.get("llm_provider")
             model_to_set = self.loaded_config.get("llm_model")
             api_key_to_set = self.loaded_config.get("llm_api_key", "") # Get the deobfuscated key

             if provider_to_set:
                 self.llm_tab.llm_provider_var.set(provider_to_set)
                 # The _on_provider_change trace will update models
                 if model_to_set:
                     # Schedule the model setting to run after the combobox values are updated by the trace
                     self.root.after(50, lambda m=model_to_set: self.llm_tab.set_model_safely(m))
             self.llm_tab.llm_api_key_var.set(api_key_to_set)

             # Apply custom templates
             custom_templates_loaded = self.loaded_config.get("custom_llm_templates", {})
             self.llm_tab.custom_templates = custom_templates_loaded
             self.llm_tab._populate_template_listbox() # Refresh listbox with loaded templates

             print(f"Finished applying config to LLM Tab widgets (Provider: {provider_to_set}, Model: {model_to_set}, Key Set: {'Yes' if api_key_to_set else 'No'}, Templates: {len(custom_templates_loaded)})")
         else:
             print("LLM Tab not ready for applying config.")


    def update_ui_text(self):
        """Coordinates the UI text update across all components."""
        try:
            print(f"DEBUG: gui.update_ui_text called for language: {self.current_language.get()}") # Debug Print
            if not self.root.winfo_exists():
                print("DEBUG: Root window destroyed before update_ui_text.")
                return

            self.root.title(self.translate("window_title"))

            # Delegate updates to components, checking existence first
            if hasattr(self, 'header') and self.header.frame.winfo_exists():
                 self.header.update_ui_text()
            if hasattr(self, 'transcription_tab') and self.transcription_tab.frame.winfo_exists():
                 self.transcription_tab.update_ui_text()

            # --- CHECK AND CALL RECORDER TAB UPDATE ---
            if hasattr(self, 'recorder_tab') and self.recorder_tab.frame.winfo_exists():
                 if hasattr(self.recorder_tab, 'update_ui_text'):
                     self.recorder_tab.update_ui_text()
                 else:
                     print("WARNING: RecorderTab instance exists but has no update_ui_text method.", file=sys.__stderr__)
            # ------------------------------------------

            if hasattr(self, 'llm_tab') and self.llm_tab.frame.winfo_exists():
                 self.llm_tab.update_ui_text()

            # Update Main Notebook Tab Titles
            if hasattr(self, 'main_notebook') and self.main_notebook.winfo_exists():
                try:
                    tabs = self.main_notebook.tabs()
                    if len(tabs) > 0: self.main_notebook.tab(tabs[0], text=self.translate("tab_transcription"))
                    if len(tabs) > 1: self.main_notebook.tab(tabs[1], text=self.translate("tab_recorder"))
                    if len(tabs) > 2: self.main_notebook.tab(tabs[2], text=self.translate("tab_llm"))
                except tk.TclError as e: print(f"Error updating main notebook tabs: {e}", file=sys.__stderr__)

            # Update main status bar text only if it's currently "Ready"
            current_status = self.status_var.get()
            # Check if the current status matches the "Ready" status in *any* known language
            is_ready = False
            for lang_code in self.translations:
                ready_text = self.translations[lang_code].get('status_ready')
                if ready_text and current_status == ready_text:
                    is_ready = True
                    break
            if is_ready:
                self.status_var.set(self.translate("status_ready")) # Set to current language's "Ready"

            print("Finished updating UI text.")

        except Exception as e:
             import traceback
             print(f"ERROR during update_ui_text: {e}\n{traceback.format_exc()}", file=sys.__stderr__)

    def on_language_select(self, event=None):
        # The trace on current_language variable handles the logic
        pass

    def change_language(self, *args):
        print(f"Language change triggered for: {self.current_language.get()}")
        self.update_ui_text()
        print(f"UI updated for language: {self.current_language.get()}")

    def _update_initial_model_description(self):
        # Needs transcription_tab to exist
        if hasattr(self, 'transcription_tab'):
            self.transcription_tab.update_model_description()

    def get_language_code(self, language_name: str) -> str:
        # (Unchanged)
        language_map = {"italiano": "italian", "inglese": "english", "francese": "french", "tedesco": "german", "spagnolo": "spanish", "giapponese": "japanese", "cinese": "chinese"}
        return language_map.get(language_name.lower(), "italian") # Default to Italian if map fails

    def update_transcription_path_callback(self, file_path):
         # (Unchanged)
         if file_path and os.path.exists(file_path):
             self.file_path.set(file_path); self._print(f"Audio file path set: {os.path.basename(file_path)}\n")
             if hasattr(self, 'main_notebook') and hasattr(self, 'transcription_tab'):
                  try: self.main_notebook.select(self.transcription_tab.frame)
                  except tk.TclError: print("Could not switch tab (TclError).", file=sys.__stderr__)
                  except Exception as e: print(f"Could not switch tab (Error: {e}).", file=sys.__stderr__)
         else: self._print(f"Invalid file path: {file_path}\n")

    # --- Methods for Transcriber Backend Communication ---
    # (Unchanged methods: _print, _update_progress, _finalize_ui, _show_error, _show_info, result_text_set)
    def _print(self, message):
        if hasattr(self, 'transcription_tab') and self.transcription_tab and hasattr(self.transcription_tab, 'console_output'):
            # Delegate to ConsoleOutput instance via stdout redirection
            print(message, end='') # Use print to go through the redirection
        else:
            print(f"Fallback print (no console): {message.strip()}", file=sys.__stderr__)

    def _update_progress(self, task_key, status_key, progress_mode="start"):
         task_text = self.translate(task_key) if task_key else self.current_task.get()
         status_text = self.translate(status_key) if status_key else self.status_var.get()
         self.current_task.set(task_text)
         self.status_var.set(status_text) # Update main status bar variable
         if hasattr(self, 'transcription_tab'):
             # Schedule UI update in the main thread
             self.root.after_idle(self.transcription_tab.update_progress_state, task_text, status_text, progress_mode)

    def _finalize_ui(self, success=True, interrupted=False):
         if interrupted: sk, tk_ = "status_interrupted", "progress_label_interrupted"
         elif success: sk, tk_ = "status_completed", "progress_label_completed"
         else: sk, tk_ = "status_error", "progress_label_error"
         # Set main status bar and transcription task label
         self.status_var.set(self.translate(sk))
         self.current_task.set(self.translate(tk_))
         if hasattr(self, 'transcription_tab'):
             self.root.after_idle(self.transcription_tab.finalize_ui_state, success, interrupted)

    def _show_error(self, error_key, **kwargs):
         t = self.translate("error_title"); m = self.translate(error_key).format(**kwargs)
         if hasattr(self, 'root') and self.root.winfo_exists():
             self.root.after_idle(lambda: messagebox.showerror(t, m, parent=self.root))
         else: print(f"ERROR (no GUI): {t} - {m}", file=sys.__stderr__)

    def _show_info(self, info_key, **kwargs):
         t = self.translate("info_title"); m = self.translate(info_key).format(**kwargs)
         if hasattr(self, 'root') and self.root.winfo_exists():
             self.root.after_idle(lambda: messagebox.showinfo(t, m, parent=self.root))
         else: print(f"INFO (no GUI): {t} - {m}", file=sys.__stderr__)

    def result_text_set(self, text):
         if hasattr(self, 'transcription_tab'):
             self.root.after_idle(self.transcription_tab.result_text_set, text)

    # --- Method to get transcription text for LLM tab ---
    def get_transcription_text(self):
        if hasattr(self, 'transcription_tab'):
            return self.transcription_tab.get_transcription_text()
        return ""

    # --- Application Closing ---
    def on_closing(self):
        # (Corrected version from previous step)
        if messagebox.askokcancel(self.translate("ask_close_title"), self.translate("ask_close_message"), parent=self.root):
            print("Exiting application...")
            current_settings = self._gather_current_config()
            self.config_manager.save_config(current_settings)

            if hasattr(self.transcriber, 'request_stop'):
                print("Requesting transcription stop...")
                self.transcriber.request_stop()

            if hasattr(self, 'recorder_tab') and self.recorder_tab:
                try:
                    print("Cleaning up recorder tab...")
                    self.recorder_tab.on_close()
                except Exception as e:
                    print(f"Error during recorder tab cleanup: {e}", file=sys.__stderr__)

            if hasattr(self, 'llm_tab') and self.llm_tab:
                try:
                    print("Cleaning up LLM tab...")
                    self.llm_tab.on_close()
                except Exception as e:
                    print(f"Error during LLM tab cleanup: {e}", file=sys.__stderr__)

            print("Destroying root window.")
            self.root.destroy()

# --- END OF REVISED gui.py ---