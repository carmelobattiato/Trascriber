# --- START OF MODIFIED gui.py ---

# ...(importazioni e classe ConsoleOutput come prima)...
import tkinter as tk
from tkinter import ttk, messagebox
import io
import os
import sys
import typing

from transcriber import AudioTranscriber
from llm_processor import LLMProcessor
from header_frame import HeaderFrame
from transcription_tab_ui import TranscriptionTabUI
from recorder_tab import RecorderTab
from llm_tab import LLMTab
from status_bar import StatusBar
from config_manager import ConfigManager
from translations import translations_dict, model_descriptions_dict

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


class ModernTranscriptionApp:
    """Main application class, orchestrates UI components and backend logic."""

    def __init__(self, root):
        self.root = root
        self.config_manager = ConfigManager()
        self.system_type = "mac" if sys.platform == "darwin" else "windows"
        self.translations = translations_dict
        self.model_descriptions = model_descriptions_dict
        self.current_language = tk.StringVar(value="English")
        self.status_var = tk.StringVar()
        self.current_task = tk.StringVar(value="")
        self.file_path = tk.StringVar()
        self.model_var = tk.StringVar(value="large")
        self.transcription_language_var = tk.StringVar(value="italiano")
        self.use_gpu_var = tk.BooleanVar(value=False)
        self.progress_var = tk.DoubleVar(value=0)
        self.model_desc_var = tk.StringVar() # Shared variable

        loaded_config = self.config_manager.load_config()
        self._apply_loaded_config(loaded_config)

        self.status_var.set(self.translate("status_ready"))
        # *** NO initial model description set here anymore ***

        self.transcriber = AudioTranscriber(self)
        self.llm_processor = LLMProcessor()
        self.setup_ui_styles()
        self.create_widgets() # Creates components

        # --- Post-Widget Creation Setup ---
        self.current_language.trace_add("write", self.change_language)
        # This first update_ui_text call will now also set the initial model description
        self.root.after_idle(self.update_ui_text)
        self.root.after_idle(self._setup_stdout_redirect)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ... (_apply_loaded_config, _gather_current_config, translate, setup_ui_styles) ...
    def _apply_loaded_config(self, config: dict):
        print("Applying loaded configuration to variables...")
        self.current_language.set(config.get("ui_language", "English"))
        self.model_var.set(config.get("transcription_model", "large"))
        self.transcription_language_var.set(config.get("transcription_language", "italiano"))
        self.use_gpu_var.set(config.get("transcription_use_gpu", False))
        self.loaded_llm_provider = config.get("llm_provider", None)
        self.loaded_llm_model = config.get("llm_model", None)
        self.loaded_llm_api_key = config.get("llm_api_key", "")
        print("Finished applying loaded config.")

    def _gather_current_config(self) -> dict:
        settings = {"ui_language": self.current_language.get(), "transcription_model": self.model_var.get(), "transcription_language": self.transcription_language_var.get(), "transcription_use_gpu": self.use_gpu_var.get(), "llm_provider": None, "llm_model": None, "llm_api_key": ""}
        if hasattr(self, 'llm_tab') and self.llm_tab: settings["llm_provider"] = self.llm_tab.llm_provider_var.get(); settings["llm_model"] = self.llm_tab.llm_model_var.get(); settings["llm_api_key"] = self.llm_tab.llm_api_key_var.get()
        return settings

    def translate(self, key):
        lang_code = self.current_language.get(); selected_lang_dict = self.translations.get(lang_code, self.translations['English']); return selected_lang_dict.get(key, self.translations['English'].get(key, f"<{key}>"))

    def setup_ui_styles(self):
        self.style = ttk.Style(); theme = 'clam'
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
        self.header = HeaderFrame(self.root, self)
        self.main_notebook = ttk.Notebook(self.root, padding=(20, 10, 20, 10))
        self.main_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.transcription_tab = TranscriptionTabUI(self.main_notebook, self)
        self.recorder_tab = RecorderTab(self.main_notebook, self.update_transcription_path_callback)
        self.llm_tab = LLMTab(self.main_notebook, self, self.llm_processor)
        self.main_notebook.add(self.transcription_tab.frame, text="")
        self.main_notebook.add(self.recorder_tab.frame, text="")
        self.main_notebook.add(self.llm_tab.frame, text="")
        self.status_bar = StatusBar(self.root, self)
        self.root.after(10, self._apply_loaded_llm_config_to_tab)

    def _setup_stdout_redirect(self):
        try:
            if (hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'console_output') and
                    isinstance(self.transcription_tab.console_output, tk.Widget) and self.transcription_tab.console_output.winfo_exists()):
                sys.stdout = ConsoleOutput(self.transcription_tab.console_output)
                print("Standard output redirected to console widget.")
                self._print(self.translate("welcome_message") + "\n")
            else: print("Console widget not available for stdout redirection.", file=sys.__stderr__)
        except Exception as e: print(f"Error setting up stdout redirection: {e}", file=sys.__stderr__)

    def _apply_loaded_llm_config_to_tab(self):
         if hasattr(self, 'llm_tab') and self.llm_tab:
             print("Applying loaded LLM config to LLM Tab widgets...")
             if hasattr(self, 'loaded_llm_provider') and self.loaded_llm_provider:
                 self.llm_tab.llm_provider_var.set(self.loaded_llm_provider)
                 if hasattr(self, 'loaded_llm_model') and self.loaded_llm_model: self.root.after(50, lambda: self.llm_tab.set_model_safely(self.loaded_llm_model))
             if hasattr(self, 'loaded_llm_api_key'): self.llm_tab.llm_api_key_var.set(self.loaded_llm_api_key)
             print("Finished applying config to LLM Tab widgets.")
         else: print("LLM Tab not ready for applying config.")

    def update_ui_text(self):
        print("Updating UI text for all components...")
        if not self.root.winfo_exists(): return
        self.root.title(self.translate("window_title"))
        if hasattr(self, 'header'): self.header.update_ui_text()
        if hasattr(self, 'transcription_tab'): self.transcription_tab.update_ui_text() # This will trigger model desc update
        if hasattr(self, 'recorder_tab') and hasattr(self.recorder_tab, 'update_ui_text'): self.recorder_tab.update_ui_text()
        if hasattr(self, 'llm_tab'): self.llm_tab.update_ui_text()
        try:
            tabs = self.main_notebook.tabs()
            if len(tabs) > 0: self.main_notebook.tab(tabs[0], text=self.translate("tab_transcription"))
            if len(tabs) > 1: self.main_notebook.tab(tabs[1], text=self.translate("tab_recorder"))
            if len(tabs) > 2: self.main_notebook.tab(tabs[2], text=self.translate("tab_llm"))
        except tk.TclError as e: print(f"Error updating main notebook tabs: {e}", file=sys.__stderr__)
        current_status = self.status_var.get()
        is_ready = any(current_status == self.translations[code].get('status_ready') for code in self.translations if self.translations[code].get('status_ready'))
        if is_ready: self.status_var.set(self.translate("status_ready"))

    def on_language_select(self, event=None): pass # Trace handles the call

    def change_language(self, *args):
        """Handles language change for the entire application. Called by trace."""
        print(f"Language change detected via trace: {self.current_language.get()}")
        self.update_ui_text() # Update all components' text first
        # Note: update_ui_text already calls transcription_tab.update_ui_text,
        # which in turn calls transcription_tab.update_model_description.
        # So, no extra call needed here.
        print(f"UI updated for language: {self.current_language.get()}")

    # **** REMOVED _update_initial_model_description ****

    def get_language_code(self, language_name: str) -> str:
        """Converts UI language name to Whisper language code."""
        language_map = {"italiano": "italian", "inglese": "english", "francese": "french", "tedesco": "german", "spagnolo": "spanish", "giapponese": "japanese", "cinese": "chinese"}
        return language_map.get(language_name.lower(), "italian")

    def update_transcription_path_callback(self, file_path):
         if file_path and os.path.exists(file_path):
             self.file_path.set(file_path); self._print(f"Audio file path set: {os.path.basename(file_path)}\n")
             if hasattr(self, 'main_notebook') and hasattr(self, 'transcription_tab'):
                  try: self.main_notebook.select(self.transcription_tab.frame)
                  except tk.TclError: print("Could not switch tab (TclError).", file=sys.__stderr__)
                  except Exception as e: print(f"Could not switch tab (Error: {e}).", file=sys.__stderr__)
         else: self._print(f"Invalid file path: {file_path}\n")

    def _print(self, message):
        if hasattr(self, 'transcription_tab'): self.transcription_tab.console_output_insert(message)
        else: print(f"Fallback print: {message.strip()}", file=sys.__stderr__)

    def _update_progress(self, task_key, status_key, progress_mode="start"):
         task_text = self.translate(task_key) if task_key else self.current_task.get()
         status_text = self.translate(status_key) if status_key else self.status_var.get()
         self.current_task.set(task_text); self.status_var.set(status_text)
         if hasattr(self, 'transcription_tab'): self.root.after_idle(self.transcription_tab.update_progress_state, task_text, status_text, progress_mode)

    def _finalize_ui(self, success=True, interrupted=False):
         if interrupted: sk, tk_ = "status_interrupted", "progress_label_interrupted"
         elif success: sk, tk_ = "status_completed", "progress_label_completed"
         else: sk, tk_ = "status_error", "progress_label_error"
         self.status_var.set(self.translate(sk)); self.current_task.set(self.translate(tk_))
         if hasattr(self, 'transcription_tab'): self.root.after_idle(self.transcription_tab.finalize_ui_state, success, interrupted)

    def _show_error(self, error_key, **kwargs):
         t = self.translate("error_title"); m = self.translate(error_key).format(**kwargs)
         self.root.after_idle(lambda: messagebox.showerror(t, m, parent=self.root))

    def _show_info(self, info_key, **kwargs):
         t = self.translate("info_title"); m = self.translate(info_key).format(**kwargs)
         self.root.after_idle(lambda: messagebox.showinfo(t, m, parent=self.root))

    def result_text_set(self, text):
         if hasattr(self, 'transcription_tab'): self.root.after_idle(self.transcription_tab.result_text_set, text)

    def on_closing(self):
        if messagebox.askokcancel(self.translate("ask_close_title"), self.translate("ask_close_message"), parent=self.root):
            print("Exiting application..."); current_settings = self._gather_current_config(); self.config_manager.save_config(current_settings)
            if hasattr(self.transcriber, 'request_stop'): print("Requesting transcription stop..."); self.transcriber.request_stop()
            if hasattr(self, 'recorder_tab') and self.recorder_tab:
                try: print("Cleaning up recorder tab..."); self.recorder_tab.on_close()
                except Exception as e: print(f"Error during recorder tab cleanup: {e}", file=sys.__stderr__)
            if hasattr(self, 'llm_tab') and self.llm_tab:
                try: print("Cleaning up LLM tab..."); self.llm_tab.on_close()
                except Exception as e: print(f"Error during LLM tab cleanup: {e}", file=sys.__stderr__)
            print("Destroying root window."); self.root.destroy()

# --- END OF CORRECTED gui.py ---