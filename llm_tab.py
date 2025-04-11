# --- START OF MODIFIED llm_tab.py ---

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
from llm_processor import LLMProcessor # Import the processor

class LLMTab:
    """GUI Tab for LLM Processing."""

    # Define provider names consistent with LLMProcessor
    LLM_PROVIDERS = list(LLMProcessor.MODEL_OPTIONS.keys())

    def __init__(self, parent_notebook, gui_app_instance, llm_processor_instance):
        self.parent_notebook = parent_notebook
        self.gui_app = gui_app_instance # To access translate, transcription text, etc.
        self.llm_processor = llm_processor_instance
        self.llm_processor.status_callback = self._update_status_from_processor # Link status updates

        self.frame = ttk.Frame(parent_notebook, padding="10")
        # Grid configuration for the main frame of this tab
        self.frame.columnconfigure(0, weight=1) # Make the main column expandable
        self.frame.rowconfigure(1, weight=1) # Make input text area expandable
        self.frame.rowconfigure(3, weight=1) # Make instruction text area expandable
        self.frame.rowconfigure(5, weight=3) # Make output text area most expandable

        # --- Variables ---
        self.llm_provider_var = tk.StringVar()
        self.llm_model_var = tk.StringVar()
        self.llm_api_key_var = tk.StringVar()
        self.llm_status_var = tk.StringVar(value=self.gui_app.translate("status_ready")) # Use GUI's translate

        # --- Create Widgets ---
        self._create_widgets() # This will now correctly create self.config_frame

        # --- Add to Notebook ---
        # The actual adding happens in gui.py after instantiation

        # --- Set initial state ---
        self.llm_provider_var.trace_add("write", self._on_provider_change)
        # Set default provider AFTER trace is added to trigger model update
        if self.LLM_PROVIDERS: # Check if list is not empty
            self.llm_provider_var.set(self.LLM_PROVIDERS[0])
        else:
             self.llm_provider_var.set("") # Handle case with no providers


    def _create_widgets(self):
        # --- Input Text Section ---
        input_frame = ttk.Frame(self.frame)
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        input_frame.columnconfigure(3, weight=1) # Allow buttons to space out

        self.input_label = ttk.Label(input_frame, text=self.gui_app.translate("llm_input_label"))
        self.input_label.grid(row=0, column=0, sticky="w")

        self.load_from_trans_button = ttk.Button(input_frame, text=self.gui_app.translate("llm_load_transcription"), command=self._load_from_transcription, style="Action.TButton")
        self.load_from_trans_button.grid(row=0, column=1, sticky="w", padx=5)

        self.load_file_button = ttk.Button(input_frame, text=self.gui_app.translate("llm_load_file"), command=self._load_from_file, style="Action.TButton")
        self.load_file_button.grid(row=0, column=2, sticky="w", padx=5)

        self.paste_button = ttk.Button(input_frame, text=self.gui_app.translate("llm_paste"), command=self._paste_text, style="Action.TButton")
        self.paste_button.grid(row=0, column=3, sticky="w", padx=5)


        input_text_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        input_text_frame.grid(row=1, column=0, sticky="nsew", pady=(0,10))
        input_text_frame.rowconfigure(0, weight=1)
        input_text_frame.columnconfigure(0, weight=1)
        self.input_text = scrolledtext.ScrolledText(input_text_frame, wrap=tk.WORD, height=8, font=("Segoe UI", 10), borderwidth=0)
        self.input_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)


        # --- LLM Configuration Section ---
        # ***** FIX: Assign to self.config_frame *****
        self.config_frame = ttk.LabelFrame(self.frame, text=self.gui_app.translate("llm_config_frame"), padding=10)
        self.config_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.config_frame.columnconfigure(1, weight=1) # Allow API Key entry to expand
        self.config_frame.columnconfigure(3, weight=1) # Allow Model combobox to expand slightly

        # ***** FIX: Add widgets to self.config_frame *****
        # Provider
        self.provider_label = ttk.Label(self.config_frame, text=self.gui_app.translate("llm_provider_label"))
        self.provider_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.provider_combo = ttk.Combobox(self.config_frame, textvariable=self.llm_provider_var, values=self.LLM_PROVIDERS, state="readonly", width=25)
        self.provider_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # API Key
        self.api_key_label = ttk.Label(self.config_frame, text=self.gui_app.translate("llm_api_key_label"))
        self.api_key_label.grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.api_key_entry = ttk.Entry(self.config_frame, textvariable=self.llm_api_key_var, width=40, show="*")
        self.api_key_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # Model
        self.model_label = ttk.Label(self.config_frame, text=self.gui_app.translate("llm_model_label"))
        self.model_label.grid(row=0, column=2, padx=(10, 5), pady=5, sticky="w")
        self.model_combo = ttk.Combobox(self.config_frame, textvariable=self.llm_model_var, state="readonly", width=30)
        self.model_combo.grid(row=0, column=3, padx=5, pady=5, sticky="ew")


        # --- Instructions Section ---
        # ***** FIX: Position instructions label relative to the frame grid *****
        self.instructions_label = ttk.Label(self.frame, text=self.gui_app.translate("llm_instructions_label"))
        self.instructions_label.grid(row=3, column=0, sticky="w", pady=(10, 5)) # Changed row from 2 to 3

        instructions_text_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        # ***** FIX: Position instructions text frame relative to the frame grid *****
        instructions_text_frame.grid(row=4, column=0, sticky="nsew", pady=(0,10)) # Changed row from 3 to 4
        instructions_text_frame.rowconfigure(0, weight=1)
        instructions_text_frame.columnconfigure(0, weight=1)
        self.instructions_text = scrolledtext.ScrolledText(instructions_text_frame, wrap=tk.WORD, height=5, font=("Segoe UI", 10), borderwidth=0)
        self.instructions_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        # Use insert with "1.0" index
        self.instructions_text.insert("1.0", self.gui_app.translate("llm_instructions_placeholder")) # Add placeholder


        # --- Process Control & Output Section ---
        output_control_frame = ttk.Frame(self.frame)
         # ***** FIX: Position output control frame relative to the frame grid *****
        output_control_frame.grid(row=5, column=0, sticky="ew", pady=(0, 5)) # Changed row from 4 to 5
        output_control_frame.columnconfigure(1, weight=1) # Allow label to push buttons right

        self.process_button = ttk.Button(output_control_frame, text=self.gui_app.translate("llm_process_button"), command=self._process_text_async, style="Primary.TButton")
        self.process_button.grid(row=0, column=0, sticky="w")

        self.output_label = ttk.Label(output_control_frame, text=self.gui_app.translate("llm_output_label"))
        self.output_label.grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.copy_output_button = ttk.Button(output_control_frame, text=self.gui_app.translate("llm_copy_output"), command=self._copy_output, style="Action.TButton")
        self.copy_output_button.grid(row=0, column=2, sticky="e", padx=5)

        self.save_output_button = ttk.Button(output_control_frame, text=self.gui_app.translate("llm_save_output"), command=self._save_output, style="Action.TButton")
        self.save_output_button.grid(row=0, column=3, sticky="e", padx=5)

        output_text_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        # ***** FIX: Position output text frame relative to the frame grid *****
        output_text_frame.grid(row=6, column=0, sticky="nsew", pady=(0,5)) # Changed row from 5 to 6
        output_text_frame.rowconfigure(0, weight=1)
        output_text_frame.columnconfigure(0, weight=1)
        self.output_text = scrolledtext.ScrolledText(output_text_frame, wrap=tk.WORD, height=10, font=("Segoe UI", 10), state=tk.DISABLED, borderwidth=0)
        self.output_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # --- Status Label ---
        self.status_label_llm = ttk.Label(self.frame, textvariable=self.llm_status_var, anchor=tk.W, style="Status.TLabel", relief="sunken")
        # ***** FIX: Position status label relative to the frame grid *****
        self.status_label_llm.grid(row=7, column=0, sticky="ew", pady=(5,0)) # Changed row from 6 to 7


    # --- UI Update & Control Methods ---

    def update_ui_text(self):
        """Updates widget text based on GUI language."""
        # Check if widgets exist before configuring
        if not hasattr(self, 'input_label') or not self.input_label.winfo_exists(): return

        self.input_label.config(text=self.gui_app.translate("llm_input_label"))
        self.load_from_trans_button.config(text=self.gui_app.translate("llm_load_transcription"))
        self.load_file_button.config(text=self.gui_app.translate("llm_load_file"))
        self.paste_button.config(text=self.gui_app.translate("llm_paste"))

        # *** Access self.config_frame ***
        self.config_frame.config(text=self.gui_app.translate("llm_config_frame"))

        self.provider_label.config(text=self.gui_app.translate("llm_provider_label"))
        self.api_key_label.config(text=self.gui_app.translate("llm_api_key_label"))
        self.model_label.config(text=self.gui_app.translate("llm_model_label"))
        self.instructions_label.config(text=self.gui_app.translate("llm_instructions_label"))

        # Re-insert placeholder text if instructions text is currently the placeholder or empty
        # Check existence before getting text
        if hasattr(self, 'instructions_text') and self.instructions_text.winfo_exists():
            current_instructions = self.instructions_text.get("1.0", tk.END).strip()
            current_placeholder = self.gui_app.translate("llm_instructions_placeholder")
            # Update only if it's the placeholder or completely empty
            if current_instructions == current_placeholder or not current_instructions:
                 try:
                     # Check state before modifying
                     if self.instructions_text.cget('state') == tk.NORMAL:
                         self.instructions_text.delete("1.0", tk.END)
                         self.instructions_text.insert("1.0", current_placeholder)
                 except tk.TclError:
                     pass # Widget might be disabled

        self.process_button.config(text=self.gui_app.translate("llm_process_button"))
        self.output_label.config(text=self.gui_app.translate("llm_output_label"))
        self.copy_output_button.config(text=self.gui_app.translate("llm_copy_output"))
        self.save_output_button.config(text=self.gui_app.translate("llm_save_output"))

        # Update status if it's currently "Ready"
        current_status = self.llm_status_var.get()
        # Check against all possible "Ready" translations
        is_ready = False
        for lang_code in self.gui_app.translations:
             ready_text = self.gui_app.translations[lang_code].get("llm_status_ready", "###NOTFOUND###")
             if current_status == ready_text:
                 is_ready = True
                 break
        if is_ready:
             self.llm_status_var.set(self.gui_app.translate("llm_status_ready"))


    # --- Other methods remain the same ---
    # ... (_on_provider_change, _load_from_transcription, _load_from_file, _paste_text, ...)
    # ... (_process_text_async, _run_llm_processing, _handle_llm_result, _set_ui_state, ...)
    # ... (_update_status_from_processor, _copy_output, _save_output, on_close) ...

    def _on_provider_change(self, *args):
        """Updates the model combobox when the provider changes."""
        selected_provider = self.llm_provider_var.get()
        models = self.llm_processor.get_models_for_provider(selected_provider)
        if hasattr(self, 'model_combo') and self.model_combo.winfo_exists():
            self.model_combo.config(values=models)
            if models:
                self.llm_model_var.set(models[0]) # Set default model for the provider
                self.model_combo.config(state="readonly")
            else:
                self.llm_model_var.set("")
                self.model_combo.config(values=[]) # Clear values explicitly
                self.model_combo.config(state="disabled")


    def _load_from_transcription(self):
        """Loads text from the main transcription result area."""
        try:
            transcription_text = self.gui_app.get_transcription_text()
            if transcription_text:
                if self.input_text.winfo_exists():
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", transcription_text)
                self.llm_status_var.set(self.gui_app.translate("llm_status_loaded_transcription"))
            else:
                messagebox.showwarning(self.gui_app.translate("warning_title"),
                                       self.gui_app.translate("llm_warn_no_transcription"), parent=self.frame)
        except Exception as e:
            messagebox.showerror(self.gui_app.translate("error_title"),
                                 f"{self.gui_app.translate('llm_error_loading_transcription')}: {e}", parent=self.frame)

    def _load_from_file(self):
        """Loads text from a user-selected file."""
        filepath = filedialog.askopenfilename(
            title=self.gui_app.translate("llm_select_file_title"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            parent=self.frame
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if self.input_text.winfo_exists():
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", content)
                self.llm_status_var.set(self.gui_app.translate("llm_status_loaded_file").format(filename=os.path.basename(filepath)))
            except Exception as e:
                messagebox.showerror(self.gui_app.translate("error_title"),
                                     self.gui_app.translate("llm_error_reading_file").format(error=e), parent=self.frame)

    def _paste_text(self):
        """Pastes text from the clipboard."""
        try:
            clipboard_text = self.frame.clipboard_get()
            if clipboard_text:
                if self.input_text.winfo_exists():
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", clipboard_text)
                self.llm_status_var.set(self.gui_app.translate("llm_status_pasted"))
            else:
                 messagebox.showwarning(self.gui_app.translate("warning_title"),
                                        self.gui_app.translate("llm_warn_clipboard_empty"), parent=self.frame)
        except tk.TclError:
             messagebox.showwarning(self.gui_app.translate("warning_title"),
                                    self.gui_app.translate("llm_warn_clipboard_empty"), parent=self.frame)
        except Exception as e:
            messagebox.showerror(self.gui_app.translate("error_title"),
                                 f"{self.gui_app.translate('llm_error_pasting')}: {e}", parent=self.frame)


    def _process_text_async(self):
        """Starts the LLM processing in a separate thread."""
        provider = self.llm_provider_var.get()
        api_key = self.llm_api_key_var.get()
        model = self.llm_model_var.get()
        user_text = ""
        instructions = ""
        placeholder = self.gui_app.translate("llm_instructions_placeholder")

        if hasattr(self, 'input_text') and self.input_text.winfo_exists():
            user_text = self.input_text.get("1.0", tk.END).strip()
        if hasattr(self, 'instructions_text') and self.instructions_text.winfo_exists():
             instructions = self.instructions_text.get("1.0", tk.END).strip()

        system_prompt = instructions if instructions != placeholder else ""

        # --- Validations ---
        if not provider: messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_no_provider"), parent=self.frame); return
        if not api_key:
             proceed = messagebox.askyesno(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_api_key"), parent=self.frame)
             if not proceed: return
        if not model: messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_no_model"), parent=self.frame); return
        if not user_text: messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_no_input"), parent=self.frame); return

        # --- Disable UI elements ---
        self._set_ui_state(processing=True)
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete("1.0", tk.END)
            self.output_text.config(state=tk.DISABLED)

        # --- Start Thread ---
        thread = threading.Thread(target=self._run_llm_processing, args=(provider, api_key, model, system_prompt, user_text), daemon=True)
        thread.start()

    def _run_llm_processing(self, provider, api_key, model, system_prompt, user_text):
        """Worker function called by the thread."""
        result_text, error_message = self.llm_processor.process_text( provider, api_key, model, system_prompt, user_text )
        if hasattr(self, 'frame') and self.frame.winfo_exists():
             self.frame.after_idle(self._handle_llm_result, result_text, error_message)

    def _handle_llm_result(self, result_text, error_message):
        """Updates the GUI after LLM processing finishes."""
        if not hasattr(self, 'frame') or not self.frame.winfo_exists(): return

        output_exists = hasattr(self, 'output_text') and self.output_text.winfo_exists()

        if output_exists:
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete("1.0", tk.END)

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

        if output_exists:
            self.output_text.config(state=tk.DISABLED)

        self._set_ui_state(processing=False) # Re-enable UI

    def _set_ui_state(self, processing: bool):
        """Enable/disable controls during processing."""
        state = tk.DISABLED if processing else tk.NORMAL
        action_state = tk.DISABLED if processing else "readonly" # For comboboxes
        text_state = tk.DISABLED if processing else tk.NORMAL

        widgets_to_update = {
            'load_from_trans_button': state, 'load_file_button': state, 'paste_button': state,
            'input_text': text_state, 'provider_combo': action_state, 'api_key_entry': state,
            'instructions_text': text_state, 'process_button': state,
            'copy_output_button': state, 'save_output_button': state # Disable output buttons too initially
        }

        try:
            for widget_name, widget_state in widgets_to_update.items():
                widget = getattr(self, widget_name, None)
                if widget and widget.winfo_exists():
                    config_key = 'state'
                    if isinstance(widget, (scrolledtext.ScrolledText, ttk.Entry)):
                         # ScrolledText and Entry use state directly
                         widget.config(state=widget_state)
                    elif isinstance(widget, ttk.Combobox):
                         widget.config(state=widget_state)
                    elif isinstance(widget, ttk.Button):
                         widget.config(state=widget_state)

            # Special handling for model combobox - keep disabled if no model selected
            if hasattr(self,'model_combo') and self.model_combo.winfo_exists():
                 if not processing and self.llm_model_var.get():
                      self.model_combo.config(state='readonly')
                 else:
                      self.model_combo.config(state=tk.DISABLED)

            # Refine output button state after potentially setting them disabled above
            if not processing:
                 output_empty = True
                 if hasattr(self, 'output_text') and self.output_text.winfo_exists():
                     # Check if text area is empty *after* it's enabled
                     temp_state = self.output_text.cget('state')
                     self.output_text.config(state=tk.NORMAL)
                     output_empty = not self.output_text.get("1.0", tk.END).strip()
                     self.output_text.config(state=temp_state) # Restore original state (likely disabled)

                 if hasattr(self,'copy_output_button') and self.copy_output_button.winfo_exists():
                     self.copy_output_button.config(state=tk.NORMAL if not output_empty else tk.DISABLED)
                 if hasattr(self,'save_output_button') and self.save_output_button.winfo_exists():
                    self.save_output_button.config(state=tk.NORMAL if not output_empty else tk.DISABLED)


            # Update status label
            if processing:
                 if hasattr(self,'llm_status_var'): self.llm_status_var.set(self.gui_app.translate("llm_status_processing"))
            # Final status is set in _handle_llm_result

        except tk.TclError as e:
             print(f"LLM Tab: Error setting UI state (TclError: {e})")
        except Exception as e:
             print(f"LLM Tab: Error setting UI state (General Exception: {e})")


    def _update_status_from_processor(self, message):
         """Callback for LLMProcessor to update status."""
         if hasattr(self, 'llm_status_var') and hasattr(self, 'frame') and self.frame.winfo_exists():
             self.frame.after_idle(lambda m=message: self.llm_status_var.set(m))


    def _copy_output(self):
        """Copies the LLM output text to the clipboard."""
        text_to_copy = ""
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
            # Temporarily enable to get text
            original_state = self.output_text.cget('state')
            self.output_text.config(state=tk.NORMAL)
            text_to_copy = self.output_text.get("1.0", tk.END).strip()
            self.output_text.config(state=original_state) # Restore state

        if not text_to_copy:
             messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_output_to_copy"), parent=self.frame)
             return

        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(text_to_copy)
            self.frame.update()
            messagebox.showinfo(self.gui_app.translate("copied_title"), self.gui_app.translate("llm_info_copied_output"), parent=self.frame)
        except tk.TclError as e:
            messagebox.showerror(self.gui_app.translate("error_title"), f"{self.gui_app.translate('llm_error_copying')}\n{e}", parent=self.frame)


    def _save_output(self):
        """Saves the LLM output text to a file."""
        text_to_save = ""
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
             original_state = self.output_text.cget('state')
             self.output_text.config(state=tk.NORMAL)
             text_to_save = self.output_text.get("1.0", tk.END).strip()
             self.output_text.config(state=original_state)

        if not text_to_save:
            messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_output_to_save"), parent=self.frame)
            return

        filepath = filedialog.asksaveasfilename(
            title=self.gui_app.translate("llm_save_output_title"),
            defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="llm_output.txt", parent=self.frame )

        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f: f.write(text_to_save)
                messagebox.showinfo(self.gui_app.translate("saved_title"), self.gui_app.translate("llm_info_saved_output").format(file=filepath), parent=self.frame)
            except Exception as e:
                messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_saving_output").format(error=e), parent=self.frame)


    def on_close(self):
        """Cleanup actions when the application is closing."""
        print("LLM Tab closing.")
        pass

# --- END OF MODIFIED llm_tab.py ---