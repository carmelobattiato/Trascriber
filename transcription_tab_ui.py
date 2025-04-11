# --- START OF REVISED transcription_tab_ui.py ---

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import sys
import typing
from utils import format_duration

if typing.TYPE_CHECKING:
    from gui import ModernTranscriptionApp
    from transcriber import AudioTranscriber

class TranscriptionTabUI:
    """Manages the UI and logic for the Transcription Tab."""

    def __init__(self, parent_notebook: ttk.Notebook, gui_app: 'ModernTranscriptionApp'):
        self.parent_notebook = parent_notebook
        self.gui_app = gui_app
        self.transcriber: 'AudioTranscriber' = gui_app.transcriber

        self.frame = ttk.Frame(parent_notebook, padding="10")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(4, weight=1) # Ensure results area expands

        # Shared Variables from gui_app
        self.file_path_var = self.gui_app.file_path
        self.model_var = self.gui_app.model_var
        self.transcription_language_var = self.gui_app.transcription_language_var
        self.use_gpu_var = self.gui_app.use_gpu_var
        self.progress_var = self.gui_app.progress_var
        self.current_task_var = self.gui_app.current_task # Label above progress bar
        self.model_desc_var = self.gui_app.model_desc_var # Label next to model dropdown

        self.gpu_tooltip = None
        self._tooltip_after_id = None

        self._create_widgets()

    def _widget_exists(self, widget_name):
        """Helper to check if a widget attribute exists and the widget itself exists."""
        widget = getattr(self, widget_name, None)
        return widget and isinstance(widget, tk.Widget) and widget.winfo_exists()

    def _create_widgets(self):
        # --- File Selection ---
        self.file_frame = ttk.LabelFrame(self.frame, text="", padding=10) # TEXT REMOVED
        self.file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.file_frame.columnconfigure(1, weight=1)
        self.wav_file_label = ttk.Label(self.file_frame, text="") # TEXT REMOVED
        self.wav_file_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path_var, width=60)
        self.file_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.browse_button = ttk.Button(self.file_frame, text="", command=self.select_file, style="Action.TButton") # TEXT REMOVED
        self.browse_button.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # --- Options ---
        self.options_frame = ttk.LabelFrame(self.frame, text="", padding=10) # TEXT REMOVED
        self.options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.options_frame.columnconfigure(2, weight=1) # Allow model description to expand

        self.model_label = ttk.Label(self.options_frame, text="") # TEXT REMOVED
        self.model_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        models = ["tiny", "base", "small", "medium", "large"]
        self.model_combobox = ttk.Combobox(self.options_frame, textvariable=self.model_var, values=models, state="readonly", width=15)
        self.model_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        # self.model_combobox.set(self.model_var.get()) # Set happens via textvariable sync

        self.model_desc_label = ttk.Label(self.options_frame, textvariable=self.model_desc_var, anchor="w", wraplength=300) # Wraplength added
        self.model_desc_label.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
        self.model_combobox.bind("<<ComboboxSelected>>", self.update_model_description)

        self.transcription_language_label = ttk.Label(self.options_frame, text="") # TEXT REMOVED
        self.transcription_language_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        # Define available languages directly
        self.transcription_languages = list(self.gui_app.translations.keys()) # Assuming keys match Whisper language names/codes needed later? No, these are display names.
        # Let's stick to the original list for Whisper for now:
        self.transcription_languages_display = ["italiano", "inglese", "francese", "tedesco", "spagnolo", "giapponese", "cinese"]
        self.language_combobox = ttk.Combobox(self.options_frame, textvariable=self.transcription_language_var, values=self.transcription_languages_display, state="readonly", width=15)
        self.language_combobox.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        # self.language_combobox.set(self.transcription_language_var.get()) # Set happens via textvariable sync

        self.acceleration_label = ttk.Label(self.options_frame, text="") # TEXT REMOVED
        self.acceleration_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.gpu_check = ttk.Checkbutton(self.options_frame, text="", variable=self.use_gpu_var) # TEXT REMOVED
        self.gpu_check.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        self.gpu_check.bind("<Enter>", self.show_gpu_tooltip)
        self.gpu_check.bind("<Leave>", self._on_leave_tooltip)

        # --- Buttons ---
        buttons_frame = ttk.Frame(self.frame)
        buttons_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self.start_button = ttk.Button(buttons_frame, text="", command=self.start_transcription, style="Primary.TButton") # TEXT REMOVED
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.stop_button = ttk.Button(buttons_frame, text="", command=self.stop_transcription, style="Action.TButton", state=tk.DISABLED) # TEXT REMOVED
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)
        # Frame for right-aligned buttons
        action_buttons_right = ttk.Frame(buttons_frame)
        action_buttons_right.pack(side=tk.RIGHT)
        self.save_button = ttk.Button(action_buttons_right, text="", command=self.save_transcription, style="Action.TButton") # TEXT REMOVED
        self.save_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.copy_button = ttk.Button(action_buttons_right, text="", command=self.copy_to_clipboard, style="Action.TButton") # TEXT REMOVED
        self.copy_button.pack(side=tk.RIGHT, padx=5, pady=5)


        # --- Progress ---
        progress_frame = ttk.Frame(self.frame)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        progress_frame.columnconfigure(0, weight=1)
        # Label showing current task (e.g., "Loading model...", "Transcribing...")
        self.current_task_label = ttk.Label(progress_frame, textvariable=self.current_task_var, anchor="w")
        self.current_task_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, mode="indeterminate", length=100, style="TProgressbar")
        self.progress_bar.grid(row=1, column=0, sticky="ew")

        # --- Results Notebook ---
        self.results_notebook = ttk.Notebook(self.frame)
        self.results_notebook.grid(row=4, column=0, sticky="nsew", pady=(0, 5))

        # --- Transcription Result Tab ---
        trans_result_frame = ttk.Frame(self.results_notebook, padding=10)
        trans_result_frame.pack(fill=tk.BOTH, expand=True)
        trans_result_frame.columnconfigure(0, weight=1)
        trans_result_frame.rowconfigure(1, weight=1) # Make text area expand
        self.results_notebook.add(trans_result_frame, text="") # TEXT REMOVED (set in update_ui_text)

        self.transcription_result_label = ttk.Label(trans_result_frame, text="") # TEXT REMOVED
        self.transcription_result_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Frame for border around ScrolledText
        result_text_frame = ttk.Frame(trans_result_frame, borderwidth=1, relief="sunken")
        result_text_frame.grid(row=1, column=0, sticky="nsew")
        result_text_frame.rowconfigure(0, weight=1)
        result_text_frame.columnconfigure(0, weight=1)
        self.result_text = scrolledtext.ScrolledText(result_text_frame, wrap=tk.WORD, width=80, height=10, font=("Segoe UI", 11), background="white", foreground=self.gui_app.text_color, borderwidth=0, relief="flat")
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # --- Console Output Tab ---
        console_frame = ttk.Frame(self.results_notebook, padding=10)
        console_frame.pack(fill=tk.BOTH, expand=True)
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(1, weight=1) # Make text area expand
        self.results_notebook.add(console_frame, text="") # TEXT REMOVED (set in update_ui_text)

        self.console_output_label = ttk.Label(console_frame, text="") # TEXT REMOVED
        self.console_output_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Frame for border around ScrolledText
        console_text_frame = ttk.Frame(console_frame, borderwidth=1, relief="sunken")
        console_text_frame.grid(row=1, column=0, sticky="nsew")
        console_text_frame.rowconfigure(0, weight=1)
        console_text_frame.columnconfigure(0, weight=1)
        self.console_output = scrolledtext.ScrolledText(console_text_frame, wrap=tk.WORD, width=80, height=10, background="#f0f0f0", foreground="#333", font=("Consolas", 10), borderwidth=0, relief="flat", state=tk.DISABLED)
        self.console_output.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

    def update_ui_text(self):
        """Updates text elements within the transcription tab safely."""
        # print("DEBUG: transcription_tab_ui.update_ui_text called")
        try:
            if not self.frame.winfo_exists(): return

            # Use helper to configure widget text safely
            self._safe_config(self.file_frame, text=self.gui_app.translate("select_audio_frame"))
            self._safe_config(self.options_frame, text=self.gui_app.translate("options_frame"))
            self._safe_config(self.wav_file_label, text=self.gui_app.translate("wav_file_label"))
            self._safe_config(self.model_label, text=self.gui_app.translate("model_label"))
            self._safe_config(self.transcription_language_label, text=self.gui_app.translate("language_label"))
            self._safe_config(self.acceleration_label, text=self.gui_app.translate("acceleration_label"))
            self._safe_config(self.transcription_result_label, text=self.gui_app.translate("transcription_result_label"))
            self._safe_config(self.console_output_label, text=self.gui_app.translate("console_output_label"))
            self._safe_config(self.gpu_check, text=self.gui_app.translate("use_gpu_checkbox"))
            self._safe_config(self.browse_button, text=self.gui_app.translate("browse_button"))
            self._safe_config(self.start_button, text=self.gui_app.translate("start_button"))
            self._safe_config(self.stop_button, text=self.gui_app.translate("stop_button"))
            self._safe_config(self.copy_button, text=self.gui_app.translate("copy_button"))
            self._safe_config(self.save_button, text=self.gui_app.translate("save_button"))

            # Update notebook tabs safely
            if self._widget_exists('results_notebook'):
                try:
                     tabs = self.results_notebook.tabs()
                     if len(tabs) >= 2:
                        self.results_notebook.tab(tabs[0], text=self.gui_app.translate("tab_transcription"))
                        self.results_notebook.tab(tabs[1], text=self.gui_app.translate("tab_console"))
                except tk.TclError as e: print(f"Error updating results notebook tabs: {e}", file=sys.__stderr__)

            # Update model description (this method already has internal checks)
            self.update_model_description()

            # Update current task label if it's showing a placeholder/key
            current_task_text = self.current_task_var.get()
            if current_task_text.startswith("<") and current_task_text.endswith(">"):
                self.current_task_var.set(self.gui_app.translate(current_task_text[1:-1])) # Translate the key

        except Exception as e:
            import traceback
            print(f"ERROR during transcription_tab_ui.update_ui_text: {e}\n{traceback.format_exc()}", file=sys.__stderr__)

    def _safe_config(self, widget, **kwargs):
        """Safely configure a widget object if it exists."""
        # (Corrected version from previous step)
        if widget and isinstance(widget, tk.Widget) and widget.winfo_exists():
            try:
                widget.config(**kwargs)
            except tk.TclError as e:
                widget_name = getattr(widget, '_name', str(widget))
                print(f"TclError configuring widget {widget_name}: {e}", file=sys.__stderr__)

    # --- Other methods (update_model_description, select_file, etc.) ---
    # (These remain largely the same, ensure they use _widget_exists or try/except for UI ops)

    def update_model_description(self, event=None):
        # (Unchanged - already seems robust)
        try:
            selected_model = self.model_var.get()
            # Fallback key if model not found in descriptions
            desc_key = self.gui_app.model_descriptions.get(selected_model, "model_desc_large")
            translated_desc = self.gui_app.translate(desc_key)
            self.model_desc_var.set(translated_desc)
        except tk.TclError as e: print(f"TclError updating model description: {e}", file=sys.__stderr__)
        except Exception as e: import traceback; print(f"Error in update_model_description: {e}\n{traceback.format_exc()}", file=sys.__stderr__)

    def select_file(self):
        # (Unchanged - seems robust)
        initial_dir = os.path.dirname(self.file_path_var.get()) if self.file_path_var.get() else os.path.expanduser("~")
        file_types = [
            (self.gui_app.translate("audio_files_label"), "*.wav *.mp3 *.flac *.ogg *.m4a"),
            (self.gui_app.translate("all_files_label"), "*.*")
        ]
        file = filedialog.askopenfilename(
            title=self.gui_app.translate("select_audio_frame"),
            initialdir=initial_dir,
            filetypes=file_types,
            parent=self.frame
        )
        if file:
            self.file_path_var.set(file)
            filename = os.path.basename(file)
            # Use main app's print method to ensure it goes to console widget
            self.gui_app._print(f"{self.gui_app.translate('selected_file_label')}: {filename}\n")
            # Try reading WAV info specifically
            if file.lower().endswith(".wav"):
                try:
                    file_info = self.transcriber.get_audio_info(file)
                    if file_info:
                        duration, channels, rate = file_info
                        duration_str = format_duration(duration)
                        info_msg = self.gui_app.translate("selected_file_info").format(
                            filename=filename, duration=duration_str, channels=channels, rate=rate
                        )
                        self.gui_app._print(info_msg + "\n")
                    else:
                        self.gui_app._print(f"{self.gui_app.translate('error_reading_wav_info').format(filename=filename)}\n")
                except Exception as e:
                    self.gui_app._print(f"Error reading WAV info for {filename}: {e}\n")


    def start_transcription(self):
        # (Unchanged - seems robust)
        input_file = self.file_path_var.get(); model_type = self.model_var.get()
        language_display_name = self.transcription_language_var.get()
        language_code = self.gui_app.get_language_code(language_display_name) # Convert display name to code
        use_gpu = self.use_gpu_var.get()

        if not input_file or not os.path.isfile(input_file):
            messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("error_no_file"), parent=self.frame)
            return

        try:
             if self._widget_exists('start_button'): self.start_button.config(state=tk.DISABLED)
             if self._widget_exists('stop_button'): self.stop_button.config(state=tk.NORMAL)
             if self._widget_exists('browse_button'): self.browse_button.config(state=tk.DISABLED) # Disable browse during run
        except tk.TclError:
            print("Error updating button states (widget destroyed?)", file=sys.__stderr__)
            return # Don't proceed if UI is broken

        self.console_output_delete_all() # Clear console
        self.result_text_clear() # Clear previous results

        self.transcriber.start_transcription_async(input_file, model_type, language_code, use_gpu, self.gui_app.system_type)

    def stop_transcription(self):
        # (Unchanged - seems robust)
        if hasattr(self.transcriber, 'request_stop'):
            self.transcriber.request_stop()
            # Use main app's print method
            self.gui_app._print(self.gui_app.translate("stop_requested_info") + "\n")
            # Update status via main app
            self.gui_app.status_var.set(self.gui_app.translate("status_stopping"))
            self.current_task_var.set(self.gui_app.translate("progress_label_interrupted"))
            try:
                 if self._widget_exists('stop_button'): self.stop_button.config(state=tk.DISABLED)
                 # Optionally re-enable start/browse if stop is immediate? No, wait for finalize_ui
            except tk.TclError:
                print("Error disabling stop button (widget destroyed?)", file=sys.__stderr__)


    def copy_to_clipboard(self):
        # (Unchanged - seems robust)
        text_to_copy = self.get_transcription_text()
        if not text_to_copy:
            messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("warning_no_text_to_copy"), parent=self.frame)
            return
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(text_to_copy)
            self.frame.update() # Necessary for clipboard to work reliably on some systems
            messagebox.showinfo(self.gui_app.translate("copied_title"), self.gui_app.translate("copied_message"), parent=self.frame)
        except tk.TclError as e:
            messagebox.showerror(self.gui_app.translate("error_title"), f"{self.gui_app.translate('error_copying')} Clipboard error: {e}", parent=self.frame)
        except Exception as e:
            messagebox.showerror(self.gui_app.translate("error_title"), f"{self.gui_app.translate('error_copying')} {e}", parent=self.frame)

    def save_transcription(self):
        # (Unchanged - seems robust)
        text = self.get_transcription_text()
        if not text:
            messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("warning_no_text_to_save"), parent=self.frame)
            return

        original_filename = os.path.basename(self.file_path_var.get())
        if original_filename:
            suggested_filename = os.path.splitext(original_filename)[0] + "_transcription.txt"
        else:
            # Fallback filename if no input file was selected/remembered
            suggested_filename = self.gui_app.translate('tab_transcription').lower().replace(" ", "_") + ".txt"

        initial_dir = os.path.dirname(self.file_path_var.get()) if self.file_path_var.get() else os.path.expanduser("~")

        file_path = filedialog.asksaveasfilename(
            title=self.gui_app.translate("save_transcription_title"), # Need new translation key
            defaultextension=".txt",
            filetypes=[(self.gui_app.translate("text_files_label"), "*.txt"), (self.gui_app.translate("all_files_label"), "*.*")], # Need keys
            initialfile=suggested_filename,
            initialdir=initial_dir,
            parent=self.frame
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo(self.gui_app.translate("saved_title"), self.gui_app.translate("saved_message").format(file=os.path.basename(file_path)), parent=self.frame)
                self.gui_app._print(f"{self.gui_app.translate('transcription_saved_to')}: {file_path}\n") # Need key
            except Exception as e:
                error_msg = self.gui_app.translate("error_saving").format(error=str(e))
                messagebox.showerror(self.gui_app.translate("error_title"), error_msg, parent=self.frame)
                self.gui_app._print(f"ERROR saving transcription: {error_msg}\n")


    def show_gpu_tooltip(self, event):
        # (Unchanged - seems okay)
        self._destroy_tooltip() # Ensure any previous one is gone
        try:
            # Create a Toplevel window
            self.gpu_tooltip = tk.Toplevel(self.frame)
            self.gpu_tooltip.wm_overrideredirect(True) # Remove window decorations

            # Position tooltip near the widget
            x = event.widget.winfo_rootx() + event.widget.winfo_width() + 5
            y = event.widget.winfo_rooty()
            self.gpu_tooltip.wm_geometry(f"+{x}+{y}")

            # Get the correct tooltip text based on OS
            msg_key = "gpu_tooltip_mac" if self.gui_app.system_type == "mac" else "gpu_tooltip_windows"
            msg = self.gui_app.translate(msg_key)

            label = ttk.Label(self.gpu_tooltip, text=msg, justify=tk.LEFT,
                              background="#ffffe0", relief="solid", borderwidth=1, padding=5,
                              font=("Segoe UI", 9))
            label.pack(ipadx=1, ipady=1)

            # Schedule tooltip destruction after a delay
            self._tooltip_after_id = self.frame.after(5000, self._destroy_tooltip)
        except Exception as e:
            print(f"Error showing GPU tooltip: {e}", file=sys.__stderr__)
            self._destroy_tooltip()

    def _destroy_tooltip(self):
        # (Unchanged - seems okay)
        # Cancel scheduled destruction if it exists
        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id:
            try:
                self.frame.after_cancel(self._tooltip_after_id)
            except ValueError: pass # Ignore if already cancelled
            self._tooltip_after_id = None
        # Destroy the tooltip window if it exists
        if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip and isinstance(self.gpu_tooltip, tk.Toplevel) and self.gpu_tooltip.winfo_exists():
            try:
                self.gpu_tooltip.destroy()
            except tk.TclError: pass # Ignore if already destroyed
        self.gpu_tooltip = None


    def _on_leave_tooltip(self, event=None):
        # (Unchanged - seems okay)
        self._destroy_tooltip()

    def update_progress_state(self, task_text, status_text, progress_mode):
        # (Unchanged - controlled by gui_app)
        try:
            if not self.frame.winfo_exists(): return
            # task_text is already translated by gui_app._update_progress
            self.current_task_var.set(task_text) # Update local task label

            if self._widget_exists('progress_bar'):
                pb = self.progress_bar
                if progress_mode == "start" or progress_mode == "indeterminate":
                    pb.config(mode="indeterminate")
                    pb.start(15) # Animation speed
                elif progress_mode == "stop":
                    pb.stop()
                    pb.config(mode="determinate")
                    self.progress_var.set(0)
                elif progress_mode == "determinate":
                    # For future use if specific progress % is available
                    pb.config(mode="determinate")
                    # self.progress_var.set(percentage_value) # Example
        except tk.TclError:
            print(f"TranscriptionTab TclError updating progress: Task={task_text}", file=sys.__stderr__)
        except Exception as e:
            print(f"TranscriptionTab Error updating progress: {e}", file=sys.__stderr__)


    def finalize_ui_state(self, success, interrupted):
        # (Unchanged - controlled by gui_app)
        try:
            if not self.frame.winfo_exists(): return
            # Re-enable buttons
            if self._widget_exists('start_button'): self.start_button.config(state=tk.NORMAL)
            if self._widget_exists('stop_button'): self.stop_button.config(state=tk.DISABLED)
            if self._widget_exists('browse_button'): self.browse_button.config(state=tk.NORMAL)
            # Stop progress bar
            if self._widget_exists('progress_bar'):
                self.progress_bar.stop()
                self.progress_var.set(0) # Reset progress value
        except tk.TclError:
            print("TranscriptionTab TclError finalizing UI state.", file=sys.__stderr__)
        except Exception as e:
            print(f"TranscriptionTab Error finalizing UI state: {e}", file=sys.__stderr__)


    def get_transcription_text(self):
        # (Unchanged - seems robust)
        if self._widget_exists('result_text'):
            try:
                return self.result_text.get("1.0", tk.END).strip()
            except tk.TclError:
                print("TclError getting result text.", file=sys.__stderr__)
        return ""

    def result_text_set(self, text):
        # (Unchanged - seems robust)
        if self._widget_exists('result_text'):
            try:
                self.result_text.config(state=tk.NORMAL)
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, text)
                self.result_text.see(tk.END) # Scroll to the end
                # Keep NORMAL state for potential copying
            except tk.TclError:
                print("TclError setting result text.", file=sys.__stderr__)
            except Exception as e:
                print(f"Error in result_text_set: {e}", file=sys.__stderr__)


    def result_text_clear(self):
        # (Unchanged - seems robust)
         if self._widget_exists('result_text'):
            try:
                 self.result_text.config(state=tk.NORMAL)
                 self.result_text.delete(1.0, tk.END)
            except tk.TclError:
                print("TclError clearing result text.", file=sys.__stderr__)
            except Exception as e:
                print(f"Error in result_text_clear: {e}", file=sys.__stderr__)

    def console_output_insert(self, text):
        # This method becomes redundant if gui_app._print is used consistently
        # But keep it for now in case direct calls exist or for future use
        if self._widget_exists('console_output'):
            try:
                console = self.console_output
                # Use after_idle for thread safety from potential background threads
                self.frame.after_idle(lambda w=console, t=text: (
                    w.config(state=tk.NORMAL),
                    w.insert(tk.END, t),
                    w.see(tk.END),
                    w.config(state=tk.DISABLED)
                ))
            except tk.TclError: print("TclError inserting console text.", file=sys.__stderr__)
            except Exception as e: print(f"Error in console_output_insert: {e}", file=sys.__stderr__)


    def console_output_delete_all(self):
        # (Unchanged - seems robust)
        if self._widget_exists('console_output'):
            try:
                console = self.console_output
                # Schedule the update to ensure it runs in the main thread safely
                self.frame.after_idle(lambda w=console: (
                    w.config(state=tk.NORMAL),
                    w.delete(1.0, tk.END),
                    w.config(state=tk.DISABLED)
                ))
            except tk.TclError: print("TclError deleting console text.", file=sys.__stderr__)
            except Exception as e: print(f"Error in console_output_delete_all: {e}", file=sys.__stderr__)

# --- END OF REVISED transcription_tab_ui.py ---