# --- START OF CORRECTED transcription_tab_ui.py ---

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import sys
import typing # For hints

# Import main app only for type hinting if needed, avoid circular imports
if typing.TYPE_CHECKING:
    from gui import ModernTranscriptionApp
    from transcriber import AudioTranscriber

class TranscriptionTabUI:
    """Manages the UI and logic for the Transcription Tab."""

    def __init__(self, parent_notebook: ttk.Notebook, gui_app: 'ModernTranscriptionApp'):
        self.parent_notebook = parent_notebook
        self.gui_app = gui_app # Use this to access shared vars/methods
        self.transcriber: 'AudioTranscriber' = gui_app.transcriber # Get transcriber instance

        self.frame = ttk.Frame(parent_notebook, padding="10")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(4, weight=1) # Make results notebook expand

        # --- Use Shared Variables from gui_app ---
        self.file_path_var = self.gui_app.file_path
        self.model_var = self.gui_app.model_var
        self.transcription_language_var = self.gui_app.transcription_language_var
        self.use_gpu_var = self.gui_app.use_gpu_var
        self.progress_var = self.gui_app.progress_var
        self.current_task_var = self.gui_app.current_task
        self.model_desc_var = self.gui_app.model_desc_var # This var holds the description text

        self.gpu_tooltip = None # Local storage for tooltip window
        self._tooltip_after_id = None # Initialize attribute for tooltip timer

        # --- Create Widgets ---
        self._create_widgets()

    # --- Widget Creation ---
    def _create_widgets(self):
        # File Selection
        self.file_frame = ttk.LabelFrame(self.frame, text="", padding=10)
        self.file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15)); self.file_frame.columnconfigure(1, weight=1)
        self.wav_file_label = ttk.Label(self.file_frame, text=""); self.wav_file_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path_var, width=60); self.file_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.browse_button = ttk.Button(self.file_frame, text="", command=self.select_file, style="Action.TButton"); self.browse_button.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # Options
        self.options_frame = ttk.LabelFrame(self.frame, text="", padding=10)
        self.options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15)); self.options_frame.columnconfigure(2, weight=1)
        self.model_label = ttk.Label(self.options_frame, text=""); self.model_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        models = ["tiny", "base", "small", "medium", "large"]
        self.model_combobox = ttk.Combobox(self.options_frame, textvariable=self.model_var, values=models, state="readonly", width=15)
        self.model_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5); self.model_combobox.set(self.model_var.get())
        self.model_desc_label = ttk.Label(self.options_frame, textvariable=self.model_desc_var, anchor="w")
        self.model_desc_label.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
        self.model_combobox.bind("<<ComboboxSelected>>", self.update_model_description)

        self.transcription_language_label = ttk.Label(self.options_frame, text=""); self.transcription_language_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.transcription_languages = ["italiano", "inglese", "francese", "tedesco", "spagnolo", "giapponese", "cinese"]
        self.language_combobox = ttk.Combobox(self.options_frame, textvariable=self.transcription_language_var, values=self.transcription_languages, state="readonly", width=15)
        self.language_combobox.grid(row=1, column=1, sticky="w", padx=5, pady=5); self.language_combobox.set(self.transcription_language_var.get())

        self.acceleration_label = ttk.Label(self.options_frame, text=""); self.acceleration_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.gpu_check = ttk.Checkbutton(self.options_frame, text="", variable=self.use_gpu_var); self.gpu_check.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        self.gpu_check.bind("<Enter>", self.show_gpu_tooltip); self.gpu_check.bind("<Leave>", self._on_leave_tooltip)

        # Buttons
        buttons_frame = ttk.Frame(self.frame); buttons_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self.start_button = ttk.Button(buttons_frame, text="", command=self.start_transcription, style="Primary.TButton"); self.start_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.stop_button = ttk.Button(buttons_frame, text="", command=self.stop_transcription, style="Action.TButton", state=tk.DISABLED); self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)
        action_buttons_right = ttk.Frame(buttons_frame); action_buttons_right.pack(side=tk.RIGHT)
        self.save_button = ttk.Button(action_buttons_right, text="", command=self.save_transcription, style="Action.TButton"); self.save_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.copy_button = ttk.Button(action_buttons_right, text="", command=self.copy_to_clipboard, style="Action.TButton"); self.copy_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Progress
        progress_frame = ttk.Frame(self.frame); progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15)); progress_frame.columnconfigure(0, weight=1)
        self.current_task_label = ttk.Label(progress_frame, textvariable=self.current_task_var, anchor="w"); self.current_task_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, mode="indeterminate", length=100, style="TProgressbar"); self.progress_bar.grid(row=1, column=0, sticky="ew")

        # Results Notebook
        self.results_notebook = ttk.Notebook(self.frame); self.results_notebook.grid(row=4, column=0, sticky="nsew", pady=(0, 5))
        # Transcription Result Tab
        trans_result_frame = ttk.Frame(self.results_notebook, padding=10); trans_result_frame.pack(fill=tk.BOTH, expand=True); trans_result_frame.columnconfigure(0, weight=1); trans_result_frame.rowconfigure(1, weight=1)
        self.results_notebook.add(trans_result_frame, text="")
        self.transcription_result_label = ttk.Label(trans_result_frame, text=""); self.transcription_result_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        result_text_frame = ttk.Frame(trans_result_frame, borderwidth=1, relief="sunken"); result_text_frame.grid(row=1, column=0, sticky="nsew"); result_text_frame.rowconfigure(0, weight=1); result_text_frame.columnconfigure(0, weight=1)
        self.result_text = scrolledtext.ScrolledText(result_text_frame, wrap=tk.WORD, width=80, height=10, font=("Segoe UI", 11), background="white", foreground=self.gui_app.text_color, borderwidth=0, relief="flat"); self.result_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        # Console Tab
        console_frame = ttk.Frame(self.results_notebook, padding=10); console_frame.pack(fill=tk.BOTH, expand=True); console_frame.columnconfigure(0, weight=1); console_frame.rowconfigure(1, weight=1)
        self.results_notebook.add(console_frame, text="")
        self.console_output_label = ttk.Label(console_frame, text=""); self.console_output_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        console_text_frame = ttk.Frame(console_frame, borderwidth=1, relief="sunken"); console_text_frame.grid(row=1, column=0, sticky="nsew"); console_text_frame.rowconfigure(0, weight=1); console_text_frame.columnconfigure(0, weight=1)
        self.console_output = scrolledtext.ScrolledText(console_text_frame, wrap=tk.WORD, width=80, height=10, background="#f0f0f0", foreground="#333", font=("Consolas", 10), borderwidth=0, relief="flat", state=tk.DISABLED); self.console_output.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)


    # --- Methods specific to this tab ---

    def update_ui_text(self):
        """Updates text elements within the transcription tab."""
        if not self.frame.winfo_exists(): return
        self.file_frame.config(text=self.gui_app.translate("select_audio_frame"))
        self.options_frame.config(text=self.gui_app.translate("options_frame"))
        self.wav_file_label.config(text=self.gui_app.translate("wav_file_label"))
        self.model_label.config(text=self.gui_app.translate("model_label"))
        self.transcription_language_label.config(text=self.gui_app.translate("language_label"))
        self.acceleration_label.config(text=self.gui_app.translate("acceleration_label"))
        self.transcription_result_label.config(text=self.gui_app.translate("transcription_result_label"))
        self.console_output_label.config(text=self.gui_app.translate("console_output_label"))
        self.gpu_check.config(text=self.gui_app.translate("use_gpu_checkbox"))
        self.browse_button.config(text=self.gui_app.translate("browse_button"))
        self.start_button.config(text=self.gui_app.translate("start_button"))
        self.stop_button.config(text=self.gui_app.translate("stop_button"))
        self.copy_button.config(text=self.gui_app.translate("copy_button"))
        self.save_button.config(text=self.gui_app.translate("save_button"))
        try:
             if hasattr(self.results_notebook, 'tabs') and len(self.results_notebook.tabs()) >= 2:
                self.results_notebook.tab(0, text=self.gui_app.translate("tab_transcription"))
                self.results_notebook.tab(1, text=self.gui_app.translate("tab_console"))
        except tk.TclError as e: print(f"Error updating results notebook tabs: {e}")
        self.update_model_description()


    def update_model_description(self, event=None):
        """Updates the shared model_desc_var based on the selected model and current language."""
        try:
            selected_model = self.model_var.get()
            desc_key = self.gui_app.model_descriptions.get(selected_model, "model_desc_large")
            translated_desc = self.gui_app.translate(desc_key)
            self.model_desc_var.set(translated_desc)
        except tk.TclError as e: print(f"TclError updating model description: {e}", file=sys.__stderr__)
        except Exception as e: import traceback; print(f"Error in update_model_description: {e}\n{traceback.format_exc()}", file=sys.__stderr__)

    def select_file(self):
        initial_dir = os.path.dirname(self.file_path_var.get()) if self.file_path_var.get() else os.path.expanduser("~")
        file = filedialog.askopenfilename( title=self.gui_app.translate("select_audio_frame"), initialdir=initial_dir, filetypes=[("Audio files", "*.wav *.mp3 *.flac *.ogg *.m4a"), ("All files", "*.*")], parent=self.frame )
        if file:
            self.file_path_var.set(file); filename = os.path.basename(file)
            if file.lower().endswith(".wav"):
                try:
                    file_info = self.transcriber.get_audio_info(file)
                    if file_info:
                        duration, channels, rate = file_info; from utils import format_duration; duration_str = format_duration(duration)
                        info_msg = self.gui_app.translate("selected_file_info").format(filename=filename, duration=duration_str, channels=channels, rate=rate)
                        self.console_output_insert(info_msg)
                    else: self.console_output_insert(f"Could not read WAV info for: {filename}\n")
                except Exception as e: self.console_output_insert(f"Error reading WAV info for {filename}: {e}\n")
            else: self.console_output_insert(f"Selected audio file: {filename}\n")

    def start_transcription(self):
        input_file = self.file_path_var.get(); model_type = self.model_var.get()
        language_code = self.gui_app.get_language_code(self.transcription_language_var.get())
        use_gpu = self.use_gpu_var.get()
        if not input_file or not os.path.isfile(input_file): messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("error_no_file"), parent=self.frame); return
        try:
             if self.start_button.winfo_exists(): self.start_button.config(state=tk.DISABLED)
             if self.stop_button.winfo_exists(): self.stop_button.config(state=tk.NORMAL)
        except tk.TclError: print("Error updating button states (widget destroyed?)"); return
        self.console_output_delete_all(); self.result_text_clear()
        self.transcriber.start_transcription_async(input_file, model_type, language_code, use_gpu, self.gui_app.system_type)

    def stop_transcription(self):
         if hasattr(self.transcriber, 'request_stop'):
             self.transcriber.request_stop()
             self.console_output_insert(self.gui_app.translate("stop_requested_info"))
             self.gui_app.status_var.set(self.gui_app.translate("status_stopping"))
             self.current_task_var.set(self.gui_app.translate("progress_label_interrupted"))
             try:
                 if self.stop_button.winfo_exists(): self.stop_button.config(state=tk.DISABLED)
             except tk.TclError: print("Error disabling stop button (widget destroyed?)")

    def copy_to_clipboard(self):
        text_to_copy = self.get_transcription_text()
        if not text_to_copy: messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("warning_no_text_to_save"), parent=self.frame); return
        try:
            self.frame.clipboard_clear(); self.frame.clipboard_append(text_to_copy); self.frame.update()
            messagebox.showinfo(self.gui_app.translate("copied_title"), self.gui_app.translate("copied_message"), parent=self.frame)
        except tk.TclError as e: messagebox.showerror(self.gui_app.translate("error_title"), f"Clipboard error: {e}", parent=self.frame)
        except Exception as e: messagebox.showerror(self.gui_app.translate("error_title"), f"Error copying text: {e}", parent=self.frame)

    def save_transcription(self):
        text = self.get_transcription_text()
        if not text: messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("warning_no_text_to_save"), parent=self.frame); return
        original_filename = os.path.basename(self.file_path_var.get())
        suggested_filename = os.path.splitext(original_filename)[0] + "_transcription.txt" if original_filename else self.gui_app.translate('tab_transcription').lower().replace(" ", "_") + ".txt"
        initial_dir = os.path.dirname(self.file_path_var.get()) if self.file_path_var.get() else os.path.expanduser("~")
        file_path = filedialog.asksaveasfilename( title=self.gui_app.translate("save_button"), defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], initialfile=suggested_filename, initialdir=initial_dir, parent=self.frame )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f: f.write(text)
                messagebox.showinfo(self.gui_app.translate("saved_title"), self.gui_app.translate("saved_message").format(file=file_path), parent=self.frame)
                self.console_output_insert(f"Transcription saved to: {file_path}\n")
            except Exception as e:
                error_msg = self.gui_app.translate("error_saving").format(error=str(e))
                messagebox.showerror(self.gui_app.translate("error_title"), error_msg, parent=self.frame)
                self.console_output_insert(f"ERROR saving transcription: {error_msg}\n")

    def show_gpu_tooltip(self, event):
        self._destroy_tooltip()
        try:
            self.gpu_tooltip = tk.Toplevel(self.frame); self.gpu_tooltip.wm_overrideredirect(True)
            x = event.widget.winfo_rootx() + event.widget.winfo_width() + 5; y = event.widget.winfo_rooty()
            self.gpu_tooltip.wm_geometry(f"+{x}+{y}")
            msg = self.gui_app.translate("gpu_tooltip_mac") if self.gui_app.system_type == "mac" else self.gui_app.translate("gpu_tooltip_windows")
            label = ttk.Label(self.gpu_tooltip, text=msg, justify=tk.LEFT, background="#ffffe0", relief="solid", borderwidth=1, padding=5, font=("Segoe UI", 9)); label.pack(ipadx=1, ipady=1)
            self._tooltip_after_id = self.frame.after(5000, self._destroy_tooltip)
        except Exception as e: print(f"Error showing GPU tooltip: {e}"); self._destroy_tooltip()

    def _destroy_tooltip(self):
        # **** FIX: Correct indentation for try...except ****
        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id:
            try:
                self.frame.after_cancel(self._tooltip_after_id)
            except ValueError:
                pass # Ignore if ID is already invalid
            self._tooltip_after_id = None # Reset ID

        if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip and isinstance(self.gpu_tooltip, tk.Toplevel) and self.gpu_tooltip.winfo_exists():
            try:
                self.gpu_tooltip.destroy()
            except tk.TclError:
                pass # Ignore if window already destroyed
        self.gpu_tooltip = None # Reset reference


    def _on_leave_tooltip(self, event=None):
        self._destroy_tooltip()

    def update_progress_state(self, task_text, status_text, progress_mode):
        try:
            if not self.frame.winfo_exists(): return
            self.current_task_var.set(task_text)
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                pb = self.progress_bar
                if progress_mode == "start" or progress_mode == "indeterminate": pb.config(mode="indeterminate"); pb.start(15)
                elif progress_mode == "stop": pb.stop(); pb.config(mode="determinate"); self.progress_var.set(0)
                elif progress_mode == "determinate": pb.config(mode="determinate")
            else: print("Progress bar widget missing in transcription tab.", file=sys.__stderr__)
        except tk.TclError: print(f"TranscriptionTab TclError updating progress: Task={task_text}", file=sys.__stderr__)
        except Exception as e: print(f"TranscriptionTab Error updating progress: {e}", file=sys.__stderr__)

    def finalize_ui_state(self, success, interrupted):
        try:
            if not self.frame.winfo_exists(): return
            if hasattr(self,'start_button') and self.start_button.winfo_exists(): self.start_button.config(state=tk.NORMAL)
            if hasattr(self,'stop_button') and self.stop_button.winfo_exists(): self.stop_button.config(state=tk.DISABLED)
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists(): self.progress_bar.stop(); self.progress_var.set(0)
        except tk.TclError: print("TranscriptionTab TclError finalizing UI state.", file=sys.__stderr__)
        except Exception as e: print(f"TranscriptionTab Error finalizing UI state: {e}", file=sys.__stderr__)

    def get_transcription_text(self):
        try:
            if hasattr(self, 'result_text') and self.result_text.winfo_exists(): return self.result_text.get("1.0", tk.END).strip()
        except tk.TclError: print("TclError getting result text.")
        return ""

    def result_text_set(self, text):
        try:
            if hasattr(self, 'result_text') and self.result_text.winfo_exists(): self.result_text.config(state=tk.NORMAL); self.result_text.delete(1.0, tk.END); self.result_text.insert(tk.END, text); self.result_text.see(tk.END)
        except tk.TclError: print("TclError setting result text.")
        except Exception as e: print(f"Error in result_text_set: {e}")

    def result_text_clear(self):
         try:
            if hasattr(self, 'result_text') and self.result_text.winfo_exists(): self.result_text.config(state=tk.NORMAL); self.result_text.delete(1.0, tk.END)
         except tk.TclError: print("TclError clearing result text.")
         except Exception as e: print(f"Error in result_text_clear: {e}")

    def console_output_insert(self, text):
        try:
            if isinstance(sys.stdout, ConsoleOutput) and sys.stdout.text_widget == self.console_output: sys.stdout.write(text)
            elif hasattr(self, 'console_output') and self.console_output.winfo_exists():
                 console = self.console_output; original_state = console.cget('state')
                 if original_state == tk.DISABLED: console.config(state=tk.NORMAL)
                 console.insert(tk.END, text); console.see(tk.END)
                 if original_state == tk.DISABLED: console.config(state=tk.DISABLED)
            else: print(f"Fallback console: {text}", file=sys.__stderr__)
        except tk.TclError: print("TclError inserting console text.")
        except Exception as e: print(f"Error in console_output_insert: {e}")

    def console_output_delete_all(self):
        try:
            if hasattr(self, 'console_output') and self.console_output.winfo_exists():
                console = self.console_output
                self.frame.after_idle(lambda w=console: (w.config(state=tk.NORMAL), w.delete(1.0, tk.END), w.config(state=tk.DISABLED)))
        except tk.TclError: print("TclError deleting console text.")
        except Exception as e: print(f"Error in console_output_delete_all: {e}")

# --- END OF CORRECTED transcription_tab_ui.py ---