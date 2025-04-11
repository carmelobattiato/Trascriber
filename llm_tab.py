# --- START OF COMPLETE llm_tab.py ---

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import sys # For stderr output on errors
import typing # For type hinting
from llm_processor import LLMProcessor # Import the processor

# Forward declaration for type hinting gui_app parameter
if typing.TYPE_CHECKING:
    from gui import ModernTranscriptionApp

class LLMTab:
    """GUI Tab for LLM Processing."""

    # Define provider names consistent with LLMProcessor
    LLM_PROVIDERS = list(LLMProcessor.MODEL_OPTIONS.keys())

    def __init__(self, parent_notebook: ttk.Notebook, gui_app: 'ModernTranscriptionApp', llm_processor_instance: LLMProcessor):
        self.parent_notebook = parent_notebook
        self.gui_app = gui_app # To access translate, transcription text, etc.
        self.llm_processor = llm_processor_instance
        self.llm_processor.status_callback = self._update_status_from_processor # Link status updates

        self.frame = ttk.Frame(parent_notebook, padding="10")
        # Grid configuration for the main frame of this tab
        self.frame.columnconfigure(0, weight=1) # Make the main column expandable
        self.frame.rowconfigure(1, weight=1) # Make input text area expandable
        self.frame.rowconfigure(4, weight=1) # Make instruction text area expandable (adjusted row)
        self.frame.rowconfigure(6, weight=3) # Make output text area most expandable (adjusted row)

        # --- Variables ---
        self.llm_provider_var = tk.StringVar()
        self.llm_model_var = tk.StringVar()
        self.llm_api_key_var = tk.StringVar()
        self.llm_status_var = tk.StringVar(value=self.gui_app.translate("llm_status_ready")) # Use GUI's translate

        # --- Create Widgets ---
        self._create_widgets()

        # --- Set initial state ---
        self.llm_provider_var.trace_add("write", self._on_provider_change)
        # Default provider/model/key are set by _apply_loaded_llm_config_to_tab in gui.py
        # We only set a fallback here if no providers exist at all.
        if not self.LLM_PROVIDERS:
             self.llm_provider_var.set("")


    def _create_widgets(self):
        # --- Input Text Section ---
        input_frame = ttk.Frame(self.frame)
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        input_frame.columnconfigure(3, weight=1) # Allow buttons to space out
        self.input_label = ttk.Label(input_frame, text="")
        self.input_label.grid(row=0, column=0, sticky="w")
        self.load_from_trans_button = ttk.Button(input_frame, text="", command=self._load_from_transcription, style="Action.TButton")
        self.load_from_trans_button.grid(row=0, column=1, sticky="w", padx=5)
        self.load_file_button = ttk.Button(input_frame, text="", command=self._load_from_file, style="Action.TButton")
        self.load_file_button.grid(row=0, column=2, sticky="w", padx=5)
        self.paste_button = ttk.Button(input_frame, text="", command=self._paste_text, style="Action.TButton")
        self.paste_button.grid(row=0, column=3, sticky="w", padx=5)

        input_text_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        input_text_frame.grid(row=1, column=0, sticky="nsew", pady=(0,10))
        input_text_frame.rowconfigure(0, weight=1); input_text_frame.columnconfigure(0, weight=1)
        self.input_text = scrolledtext.ScrolledText(input_text_frame, wrap=tk.WORD, height=8, font=("Segoe UI", 10), borderwidth=0)
        self.input_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # --- LLM Configuration Section ---
        self.config_frame = ttk.LabelFrame(self.frame, text="", padding=10)
        self.config_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.config_frame.columnconfigure(1, weight=1); self.config_frame.columnconfigure(3, weight=1)
        # Provider
        self.provider_label = ttk.Label(self.config_frame, text="")
        self.provider_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.provider_combo = ttk.Combobox(self.config_frame, textvariable=self.llm_provider_var, values=self.LLM_PROVIDERS, state="readonly", width=25)
        self.provider_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # API Key
        self.api_key_label = ttk.Label(self.config_frame, text="")
        self.api_key_label.grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.api_key_entry = ttk.Entry(self.config_frame, textvariable=self.llm_api_key_var, width=40, show="*")
        self.api_key_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        # Model
        self.model_label = ttk.Label(self.config_frame, text="")
        self.model_label.grid(row=0, column=2, padx=(10, 5), pady=5, sticky="w")
        self.model_combo = ttk.Combobox(self.config_frame, textvariable=self.llm_model_var, state="disabled", width=30) # Start disabled until provider selected
        self.model_combo.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # --- Instructions Section ---
        self.instructions_label = ttk.Label(self.frame, text="")
        self.instructions_label.grid(row=3, column=0, sticky="w", pady=(10, 5)) # Adjusted row

        instructions_text_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        instructions_text_frame.grid(row=4, column=0, sticky="nsew", pady=(0,10)) # Adjusted row
        instructions_text_frame.rowconfigure(0, weight=1); instructions_text_frame.columnconfigure(0, weight=1)
        self.instructions_text = scrolledtext.ScrolledText(instructions_text_frame, wrap=tk.WORD, height=5, font=("Segoe UI", 10), borderwidth=0)
        self.instructions_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        # Placeholder set in update_ui_text

        # --- Process Control & Output Section ---
        output_control_frame = ttk.Frame(self.frame)
        output_control_frame.grid(row=5, column=0, sticky="ew", pady=(0, 5)) # Adjusted row
        output_control_frame.columnconfigure(1, weight=1) # Allow label to push buttons right
        self.process_button = ttk.Button(output_control_frame, text="", command=self._process_text_async, style="Primary.TButton")
        self.process_button.grid(row=0, column=0, sticky="w")
        self.output_label = ttk.Label(output_control_frame, text="")
        self.output_label.grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.copy_output_button = ttk.Button(output_control_frame, text="", command=self._copy_output, style="Action.TButton", state=tk.DISABLED) # Start disabled
        self.copy_output_button.grid(row=0, column=2, sticky="e", padx=5)
        self.save_output_button = ttk.Button(output_control_frame, text="", command=self._save_output, style="Action.TButton", state=tk.DISABLED) # Start disabled
        self.save_output_button.grid(row=0, column=3, sticky="e", padx=5)

        output_text_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        output_text_frame.grid(row=6, column=0, sticky="nsew", pady=(0,5)) # Adjusted row
        output_text_frame.rowconfigure(0, weight=1); output_text_frame.columnconfigure(0, weight=1)
        self.output_text = scrolledtext.ScrolledText(output_text_frame, wrap=tk.WORD, height=10, font=("Segoe UI", 10), state=tk.DISABLED, borderwidth=0)
        self.output_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # --- Status Label ---
        self.status_label_llm = ttk.Label(self.frame, textvariable=self.llm_status_var, anchor=tk.W, style="Status.TLabel", relief="sunken")
        self.status_label_llm.grid(row=7, column=0, sticky="ew", pady=(5,0)) # Adjusted row


    # --- UI Update & Control Methods ---

    def update_ui_text(self):
        """Updates widget text based on GUI language."""
        if not hasattr(self, 'input_label') or not self.input_label.winfo_exists(): return
        self.input_label.config(text=self.gui_app.translate("llm_input_label"))
        self.load_from_trans_button.config(text=self.gui_app.translate("llm_load_transcription"))
        self.load_file_button.config(text=self.gui_app.translate("llm_load_file"))
        self.paste_button.config(text=self.gui_app.translate("llm_paste"))
        self.config_frame.config(text=self.gui_app.translate("llm_config_frame"))
        self.provider_label.config(text=self.gui_app.translate("llm_provider_label"))
        self.api_key_label.config(text=self.gui_app.translate("llm_api_key_label"))
        self.model_label.config(text=self.gui_app.translate("llm_model_label"))
        self.instructions_label.config(text=self.gui_app.translate("llm_instructions_label"))

        if hasattr(self, 'instructions_text') and self.instructions_text.winfo_exists():
            current_instructions = ""
            try: current_instructions = self.instructions_text.get("1.0", tk.END).strip()
            except tk.TclError: pass
            is_placeholder = False
            if not current_instructions: is_placeholder = True
            else:
                for lang_code in self.gui_app.translations:
                    lang_placeholder = self.gui_app.translations[lang_code].get("llm_instructions_placeholder", "###")
                    if current_instructions == lang_placeholder: is_placeholder = True; break
            if is_placeholder:
                 try:
                     if self.instructions_text.cget('state') == tk.NORMAL:
                         self.instructions_text.delete("1.0", tk.END)
                         self.instructions_text.insert("1.0", self.gui_app.translate("llm_instructions_placeholder"))
                 except tk.TclError: pass

        self.process_button.config(text=self.gui_app.translate("llm_process_button"))
        self.output_label.config(text=self.gui_app.translate("llm_output_label"))
        self.copy_output_button.config(text=self.gui_app.translate("llm_copy_output"))
        self.save_output_button.config(text=self.gui_app.translate("llm_save_output"))

        current_status = self.llm_status_var.get()
        is_ready = any(current_status == self.gui_app.translations[code].get('llm_status_ready') for code in self.gui_app.translations if self.gui_app.translations[code].get('llm_status_ready'))
        if is_ready: self.llm_status_var.set(self.gui_app.translate("llm_status_ready"))


    def _on_provider_change(self, *args):
        """Updates the model combobox when the provider changes."""
        selected_provider = self.llm_provider_var.get()
        print(f"LLM Tab: Provider changed to {selected_provider}")
        models = self.llm_processor.get_models_for_provider(selected_provider)
        if hasattr(self, 'model_combo') and self.model_combo.winfo_exists():
            self.model_combo.config(values=models)
            if models:
                self.llm_model_var.set(models[0]) # Set default model
                self.model_combo.config(state="readonly")
                print(f"LLM Tab: Set default model to {models[0]}")
            else:
                self.llm_model_var.set("")
                self.model_combo.config(values=[])
                self.model_combo.config(state="disabled")
                print("LLM Tab: No models found, disabling model combobox.")
        else: print("LLM Tab Warning: Model combobox not available during provider change.")


    # --- Action Methods ---
    def _load_from_transcription(self):
        try:
            transcription_text = self.gui_app.get_transcription_text()
            if transcription_text:
                if self.input_text.winfo_exists(): self.input_text.delete("1.0", tk.END); self.input_text.insert("1.0", transcription_text)
                self.llm_status_var.set(self.gui_app.translate("llm_status_loaded_transcription"))
            else: messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_transcription"), parent=self.frame)
        except Exception as e: messagebox.showerror(self.gui_app.translate("error_title"), f"{self.gui_app.translate('llm_error_loading_transcription')}: {e}", parent=self.frame)

    def _load_from_file(self):
        filepath = filedialog.askopenfilename(title=self.gui_app.translate("llm_select_file_title"), filetypes=[("Text files", "*.txt"), ("All files", "*.*")], parent=self.frame)
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
                if self.input_text.winfo_exists(): self.input_text.delete("1.0", tk.END); self.input_text.insert("1.0", content)
                self.llm_status_var.set(self.gui_app.translate("llm_status_loaded_file").format(filename=os.path.basename(filepath)))
            except Exception as e: messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_reading_file").format(error=e), parent=self.frame)

    def _paste_text(self):
        try:
            clipboard_text = self.frame.clipboard_get()
            if clipboard_text:
                if self.input_text.winfo_exists(): self.input_text.delete("1.0", tk.END); self.input_text.insert("1.0", clipboard_text)
                self.llm_status_var.set(self.gui_app.translate("llm_status_pasted"))
            else: messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_clipboard_empty"), parent=self.frame)
        except tk.TclError: messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_clipboard_empty"), parent=self.frame)
        except Exception as e: messagebox.showerror(self.gui_app.translate("error_title"), f"{self.gui_app.translate('llm_error_pasting')}: {e}", parent=self.frame)


    def _process_text_async(self):
        provider = self.llm_provider_var.get(); api_key = self.llm_api_key_var.get(); model = self.llm_model_var.get()
        user_text = ""; instructions = ""; placeholder = self.gui_app.translate("llm_instructions_placeholder")
        if hasattr(self, 'input_text') and self.input_text.winfo_exists(): user_text = self.input_text.get("1.0", tk.END).strip()
        if hasattr(self, 'instructions_text') and self.instructions_text.winfo_exists(): instructions = self.instructions_text.get("1.0", tk.END).strip()
        system_prompt = instructions if instructions != placeholder else ""
        # Validations
        if not provider: messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_no_provider"), parent=self.frame); return
        if not api_key:
             if not messagebox.askyesno(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_api_key"), parent=self.frame): return
        if not model: messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_no_model"), parent=self.frame); return
        if not user_text: messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_no_input"), parent=self.frame); return
        # UI Update & Thread Start
        self._set_ui_state(processing=True)
        if hasattr(self, 'output_text') and self.output_text.winfo_exists(): self.output_text.config(state=tk.NORMAL); self.output_text.delete("1.0", tk.END); self.output_text.config(state=tk.DISABLED)
        thread = threading.Thread(target=self._run_llm_processing, args=(provider, api_key, model, system_prompt, user_text), daemon=True); thread.start()

    def _run_llm_processing(self, provider, api_key, model, system_prompt, user_text):
        result_text, error_message = self.llm_processor.process_text(provider, api_key, model, system_prompt, user_text)
        if hasattr(self,'frame') and self.frame.winfo_exists(): self.frame.after_idle(self._handle_llm_result, result_text, error_message)

    def _handle_llm_result(self, result_text, error_message):
        if not hasattr(self,'frame') or not self.frame.winfo_exists(): return
        output_exists = hasattr(self, 'output_text') and self.output_text.winfo_exists()
        if output_exists: self.output_text.config(state=tk.NORMAL); self.output_text.delete("1.0", tk.END)
        if error_message:
            if output_exists: self.output_text.insert(tk.END, f"{self.gui_app.translate('error_title')}: {error_message}")
            self.llm_status_var.set(self.gui_app.translate("llm_status_error"))
            messagebox.showerror(self.gui_app.translate("error_title"), error_message, parent=self.frame)
        elif result_text is not None:
            if output_exists: self.output_text.insert(tk.END, result_text)
            self.llm_status_var.set(self.gui_app.translate("llm_status_completed"))
        else:
            if output_exists: self.output_text.insert(tk.END, f"{self.gui_app.translate('error_title')}: {self.gui_app.translate('llm_error_unknown')}")
            self.llm_status_var.set(self.gui_app.translate("llm_status_error"))
            messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate('llm_error_unknown'), parent=self.frame)
        if output_exists: self.output_text.config(state=tk.DISABLED)
        self._set_ui_state(processing=False)

    def _set_ui_state(self, processing: bool):
        state = tk.DISABLED if processing else tk.NORMAL; action_state = tk.DISABLED if processing else "readonly"; text_state = tk.DISABLED if processing else tk.NORMAL
        widgets = {'load_from_trans_button': state, 'load_file_button': state, 'paste_button': state, 'input_text': text_state, 'provider_combo': action_state, 'api_key_entry': state, 'instructions_text': text_state, 'process_button': state, 'copy_output_button': state, 'save_output_button': state}
        try:
            for name, widget_state in widgets.items():
                widget = getattr(self, name, None)
                if widget and widget.winfo_exists():
                    if isinstance(widget, (scrolledtext.ScrolledText, ttk.Entry)): widget.config(state=widget_state)
                    elif isinstance(widget, ttk.Combobox): widget.config(state=widget_state)
                    elif isinstance(widget, ttk.Button): widget.config(state=widget_state)
            if hasattr(self,'model_combo') and self.model_combo.winfo_exists(): self.model_combo.config(state='readonly' if not processing and self.llm_provider_var.get() and self.model_combo.cget('values') else tk.DISABLED)
            if not processing:
                 output_empty = True
                 if hasattr(self, 'output_text') and self.output_text.winfo_exists():
                     try: original = self.output_text.cget('state'); self.output_text.config(state=tk.NORMAL); output_empty = not self.output_text.get("1.0", tk.END).strip(); self.output_text.config(state=original)
                     except tk.TclError: pass
                 if hasattr(self,'copy_output_button') and self.copy_output_button.winfo_exists(): self.copy_output_button.config(state=tk.NORMAL if not output_empty else tk.DISABLED)
                 if hasattr(self,'save_output_button') and self.save_output_button.winfo_exists(): self.save_output_button.config(state=tk.NORMAL if not output_empty else tk.DISABLED)
            if processing:
                 if hasattr(self,'llm_status_var'): self.llm_status_var.set(self.gui_app.translate("llm_status_processing"))
        except tk.TclError as e: print(f"LLM Tab: Error setting UI state (TclError: {e})", file=sys.__stderr__)
        except Exception as e: print(f"LLM Tab: Error setting UI state (Exception: {e})", file=sys.__stderr__)

    def _update_status_from_processor(self, message):
         if hasattr(self, 'llm_status_var') and hasattr(self, 'frame') and self.frame.winfo_exists(): self.frame.after_idle(lambda m=message: self.llm_status_var.set(m))

    def _copy_output(self):
        text_to_copy = ""; copied = False
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
            try: original = self.output_text.cget('state'); self.output_text.config(state=tk.NORMAL); text_to_copy = self.output_text.get("1.0", tk.END).strip(); self.output_text.config(state=original)
            except tk.TclError: pass
        if not text_to_copy: messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_output_to_copy"), parent=self.frame); return
        try: self.frame.clipboard_clear(); self.frame.clipboard_append(text_to_copy); self.frame.update(); copied = True
        except tk.TclError as e: messagebox.showerror(self.gui_app.translate("error_title"), f"{self.gui_app.translate('llm_error_copying')}\n{e}", parent=self.frame)
        if copied: messagebox.showinfo(self.gui_app.translate("copied_title"), self.gui_app.translate("llm_info_copied_output"), parent=self.frame)

    def _save_output(self):
        text_to_save = ""
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
             try: original = self.output_text.cget('state'); self.output_text.config(state=tk.NORMAL); text_to_save = self.output_text.get("1.0", tk.END).strip(); self.output_text.config(state=original)
             except tk.TclError: pass
        if not text_to_save: messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_output_to_save"), parent=self.frame); return
        filepath = filedialog.asksaveasfilename( title=self.gui_app.translate("llm_save_output_title"), defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], initialfile="llm_output.txt", parent=self.frame )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f: f.write(text_to_save)
                messagebox.showinfo(self.gui_app.translate("saved_title"), self.gui_app.translate("llm_info_saved_output").format(file=filepath), parent=self.frame)
            except Exception as e: messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_saving_output").format(error=e), parent=self.frame)

    # --- NEW Method for applying loaded model config ---
    def set_model_safely(self, model_name_to_set: str):
        """Sets the model combobox value if the model exists in its current list."""
        try:
            if hasattr(self, 'model_combo') and self.model_combo.winfo_exists():
                available_models = self.model_combo.cget('values')
                # Convert Tcl list string to Python list if necessary
                if isinstance(available_models, str):
                    import ast
                    try: available_models = ast.literal_eval(available_models)
                    except (ValueError, SyntaxError): available_models = []
                if not isinstance(available_models, (list, tuple)): available_models = []

                if model_name_to_set in available_models:
                    self.llm_model_var.set(model_name_to_set)
                    print(f"LLM Tab: Set model from config: {model_name_to_set}")
                else:
                    print(f"LLM Tab Warning: Saved model '{model_name_to_set}' not valid for provider '{self.llm_provider_var.get()}'. Using default.")
            else: print("LLM Tab: Model combobox not ready to set model.")
        except tk.TclError: print(f"LLM Tab: TclError setting model '{model_name_to_set}'.", file=sys.__stderr__)
        except Exception as e: print(f"LLM Tab: Error in set_model_safely: {e}", file=sys.__stderr__)

    def on_close(self):
        """Cleanup actions when the application is closing."""
        print("LLM Tab closing.")
        pass

# --- END OF COMPLETE llm_tab.py ---