# --- START OF REVISED llm_tab.py ---

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import threading
import os
import sys
import typing
import ast # For parsing list string from combobox get

# Import Processor and Main App for type hinting
from llm_processor import LLMProcessor
if typing.TYPE_CHECKING:
    from gui import ModernTranscriptionApp

class LLMTab:
    """GUI Tab for LLM Processing with Templates."""
    LLM_PROVIDERS = list(LLMProcessor.MODEL_OPTIONS.keys())

    # Predefined Templates Keys (values are looked up in translations)
    PREDEFINED_TEMPLATES = {
        "Summarize": "template_summarize",
        "Meeting Minutes": "template_meeting_minutes",
        "Bullet Points": "template_bullet_points",
        "Format Email": "template_format_email",
    }

    def __init__(self, parent_notebook: ttk.Notebook, gui_app: 'ModernTranscriptionApp', llm_processor_instance: LLMProcessor):
        self.parent_notebook = parent_notebook
        self.gui_app = gui_app
        self.llm_processor = llm_processor_instance
        self.llm_processor.status_callback = self._update_status_from_processor

        # Get custom templates loaded by gui_app's config manager
        # Needs to happen *before* _create_widgets if _populate_template_listbox is called there
        self.custom_templates = self.gui_app.loaded_config.get("custom_llm_templates", {})

        self.frame = ttk.Frame(parent_notebook, padding="10")
        self.frame.columnconfigure(1, weight=1) # Main content area expands (right column)
        self.frame.rowconfigure(3, weight=1) # Input text expands
        self.frame.rowconfigure(6, weight=1) # Instructions expands
        self.frame.rowconfigure(9, weight=3) # Output expands

        # --- Variables ---
        self.llm_provider_var = tk.StringVar()
        self.llm_model_var = tk.StringVar()
        self.llm_api_key_var = tk.StringVar()
        self.llm_status_var = tk.StringVar(value="") # Set in update_ui_text
        self.selected_template_name = tk.StringVar() # Tracks selection in listbox

        self._create_widgets()
        # Populate listbox *after* widgets are created
        self._populate_template_listbox() # Initial population

        # Add trace *after* widgets using the variable are created
        self.llm_provider_var.trace_add("write", self._on_provider_change)
        # Set initial state based on potentially loaded config (provider might already be set)
        self._on_provider_change() # Call manually once to set initial model list

    def _create_widgets(self):
        # --- LEFT COLUMN: Templates ---
        self.template_frame = ttk.LabelFrame(self.frame, text="", padding=5) # TEXT REMOVED
        self.template_frame.grid(row=0, column=0, rowspan=8, sticky="nsw", padx=(0, 10), pady=(0,5))
        self.template_frame.rowconfigure(0, weight=1) # Allow listbox to expand vertically

        self.template_listbox = tk.Listbox(self.template_frame, exportselection=False, width=25, height=15)
        self.template_listbox.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 5))
        self.template_listbox.bind("<<ListboxSelect>>", self._on_template_select)

        # Scrollbar for template listbox
        template_scrollbar = ttk.Scrollbar(self.template_frame, orient="vertical", command=self.template_listbox.yview)
        template_scrollbar.grid(row=0, column=2, sticky="ns", pady=(0,5))
        self.template_listbox.config(yscrollcommand=template_scrollbar.set)

        # Buttons below template listbox
        template_btn_frame = ttk.Frame(self.template_frame)
        template_btn_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.save_template_button = ttk.Button(template_btn_frame, text="", command=self._save_template, style="Action.TButton", width=14) # TEXT REMOVED
        self.save_template_button.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.X)
        self.delete_template_button = ttk.Button(template_btn_frame, text="", command=self._delete_template, style="Action.TButton", width=14) # TEXT REMOVED
        self.delete_template_button.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.X)


        # --- RIGHT COLUMN: Main Content ---
        # Input Controls
        input_frame = ttk.Frame(self.frame)
        input_frame.grid(row=0, column=1, sticky="ew", pady=(0, 5))
        input_frame.columnconfigure(3, weight=1) # Allow paste button area to expand? No, keep left aligned
        self.input_label = ttk.Label(input_frame, text="") # TEXT REMOVED
        self.input_label.grid(row=0, column=0, sticky="w")
        self.load_from_trans_button = ttk.Button(input_frame, text="", command=self._load_from_transcription, style="Action.TButton") # TEXT REMOVED
        self.load_from_trans_button.grid(row=0, column=1, sticky="w", padx=5)
        self.load_file_button = ttk.Button(input_frame, text="", command=self._load_from_file, style="Action.TButton") # TEXT REMOVED
        self.load_file_button.grid(row=0, column=2, sticky="w", padx=5)
        self.paste_button = ttk.Button(input_frame, text="", command=self._paste_text, style="Action.TButton") # TEXT REMOVED
        self.paste_button.grid(row=0, column=3, sticky="w", padx=5)

        # Input Text Area
        input_text_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        input_text_frame.grid(row=1, column=1, rowspan=3, sticky="nsew", pady=(0,10))
        input_text_frame.rowconfigure(0, weight=1); input_text_frame.columnconfigure(0, weight=1)
        self.input_text = scrolledtext.ScrolledText(input_text_frame, wrap=tk.WORD, height=8, font=("Segoe UI", 10), borderwidth=0)
        self.input_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # Configuration Frame
        self.config_frame = ttk.LabelFrame(self.frame, text="", padding=10) # TEXT REMOVED
        self.config_frame.grid(row=4, column=1, sticky="ew", pady=(0, 10))
        self.config_frame.columnconfigure(1, weight=1) # Provider combo expands
        self.config_frame.columnconfigure(3, weight=1) # Model combo expands
        self.provider_label = ttk.Label(self.config_frame, text="") # TEXT REMOVED
        self.provider_label.grid(row=0, column=0, padx=(0, 5), pady=2, sticky="w")
        self.provider_combo = ttk.Combobox(self.config_frame, textvariable=self.llm_provider_var, values=self.LLM_PROVIDERS, state="readonly", width=25)
        self.provider_combo.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.model_label = ttk.Label(self.config_frame, text="") # TEXT REMOVED
        self.model_label.grid(row=0, column=2, padx=(10, 5), pady=2, sticky="w")
        self.model_combo = ttk.Combobox(self.config_frame, textvariable=self.llm_model_var, state="disabled", width=30) # State updated by _on_provider_change
        self.model_combo.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        self.api_key_label = ttk.Label(self.config_frame, text="") # TEXT REMOVED
        self.api_key_label.grid(row=1, column=0, padx=(0, 5), pady=2, sticky="w")
        self.api_key_entry = ttk.Entry(self.config_frame, textvariable=self.llm_api_key_var, width=40, show="*")
        self.api_key_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=2, sticky="ew")


        # Instructions Area
        self.instructions_label = ttk.Label(self.frame, text="") # TEXT REMOVED
        self.instructions_label.grid(row=5, column=1, sticky="w", pady=(5, 5))
        instructions_text_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        instructions_text_frame.grid(row=6, column=1, sticky="nsew", pady=(0,10))
        instructions_text_frame.rowconfigure(0, weight=1); instructions_text_frame.columnconfigure(0, weight=1)
        self.instructions_text = scrolledtext.ScrolledText(instructions_text_frame, wrap=tk.WORD, height=5, font=("Segoe UI", 10), borderwidth=0)
        self.instructions_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        # Placeholder text will be added by update_ui_text if empty

        # Output Controls
        output_control_frame = ttk.Frame(self.frame)
        output_control_frame.grid(row=7, column=1, sticky="ew", pady=(0, 5))
        output_control_frame.columnconfigure(1, weight=1) # Output label expands
        self.process_button = ttk.Button(output_control_frame, text="", command=self._process_text_async, style="Primary.TButton") # TEXT REMOVED
        self.process_button.grid(row=0, column=0, sticky="w")
        self.output_label = ttk.Label(output_control_frame, text="") # TEXT REMOVED
        self.output_label.grid(row=0, column=1, sticky="w", padx=(10, 0))
        # Buttons aligned right
        self.copy_output_button = ttk.Button(output_control_frame, text="", command=self._copy_output, style="Action.TButton", state=tk.DISABLED) # TEXT REMOVED
        self.copy_output_button.grid(row=0, column=2, sticky="e", padx=5)
        self.save_output_button = ttk.Button(output_control_frame, text="", command=self._save_output, style="Action.TButton", state=tk.DISABLED) # TEXT REMOVED
        self.save_output_button.grid(row=0, column=3, sticky="e", padx=5)

        # Output Text Area
        output_text_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        output_text_frame.grid(row=8, column=1, rowspan=2, sticky="nsew", pady=(0,5))
        output_text_frame.rowconfigure(0, weight=1); output_text_frame.columnconfigure(0, weight=1)
        self.output_text = scrolledtext.ScrolledText(output_text_frame, wrap=tk.WORD, height=10, font=("Segoe UI", 10), state=tk.DISABLED, borderwidth=0)
        self.output_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # Status Label for LLM Tab
        self.status_label_llm = ttk.Label(self.frame, textvariable=self.llm_status_var, anchor=tk.W, style="Status.TLabel", relief="sunken")
        self.status_label_llm.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(5,0)) # Span both columns

    def update_ui_text(self):
        """Updates widget text based on GUI language."""
        # print(f"DEBUG: llm_tab.update_ui_text called for lang {self.gui_app.current_language.get()}")
        if not hasattr(self, 'input_label') or not self.input_label.winfo_exists():
            # print("DEBUG: llm_tab widgets don't exist yet in update_ui_text")
            return

        try:
            self.input_label.config(text=self.gui_app.translate("llm_input_label"))
            self.load_from_trans_button.config(text=self.gui_app.translate("llm_load_transcription"))
            self.load_file_button.config(text=self.gui_app.translate("llm_load_file"))
            self.paste_button.config(text=self.gui_app.translate("llm_paste"))
            self.config_frame.config(text=self.gui_app.translate("llm_config_frame"))
            self.provider_label.config(text=self.gui_app.translate("llm_provider_label"))
            self.api_key_label.config(text=self.gui_app.translate("llm_api_key_label"))
            self.model_label.config(text=self.gui_app.translate("llm_model_label"))
            self.instructions_label.config(text=self.gui_app.translate("llm_instructions_label"))

            if hasattr(self, 'template_frame'): self.template_frame.config(text=self.gui_app.translate("llm_template_label"))
            self.save_template_button.config(text=self.gui_app.translate("llm_save_template_button"))
            self.delete_template_button.config(text=self.gui_app.translate("llm_delete_template_button"))

            # Handle instructions placeholder correctly
            if hasattr(self, 'instructions_text') and self.instructions_text.winfo_exists():
                current_instructions = ""; is_placeholder = False; is_empty = False
                try:
                    current_instructions = self.instructions_text.get("1.0", tk.END).strip()
                    is_empty = not current_instructions
                except tk.TclError: pass # Ignore if disabled

                if not is_empty:
                    # Check if current text matches *any* known placeholder
                    for lang_code in self.gui_app.translations:
                        placeholder_text = self.gui_app.translations[lang_code].get("llm_instructions_placeholder")
                        if placeholder_text and current_instructions == placeholder_text:
                            is_placeholder = True
                            break
                else:
                    is_placeholder = True # Treat empty as placeholder

                if is_placeholder:
                    # If it's empty or a placeholder, update it to the current language's placeholder
                    try:
                        if self.instructions_text.cget('state') == tk.NORMAL:
                            self.instructions_text.delete("1.0", tk.END)
                            self.instructions_text.insert("1.0", self.gui_app.translate("llm_instructions_placeholder"))
                    except tk.TclError: pass # Ignore if disabled

            self.process_button.config(text=self.gui_app.translate("llm_process_button"))
            self.output_label.config(text=self.gui_app.translate("llm_output_label"))
            self.copy_output_button.config(text=self.gui_app.translate("llm_copy_output"))
            self.save_output_button.config(text=self.gui_app.translate("llm_save_output"))

            # Update status if "Ready" or empty
            current_status = self.llm_status_var.get()
            is_ready_or_empty = not current_status # Treat empty as ready initially
            if not is_ready_or_empty:
                for lang_code in self.gui_app.translations:
                    ready_text = self.gui_app.translations[lang_code].get('llm_status_ready')
                    if ready_text and current_status == ready_text:
                        is_ready_or_empty = True
                        break
            if is_ready_or_empty:
                self.llm_status_var.set(self.gui_app.translate("llm_status_ready"))

            # Refresh template listbox names (handles predefined names changing language)
            self._populate_template_listbox()

        except tk.TclError as e:
            print(f"LLM Tab: TclError during update_ui_text: {e}", file=sys.__stderr__)
        except Exception as e:
            import traceback
            print(f"LLM Tab: Unexpected error during update_ui_text: {e}\n{traceback.format_exc()}", file=sys.__stderr__)


    # --- Other methods (_create_widgets, _load_from_transcription, etc.) ---
    # (Ensure they don't set text initially and handle widget existence)
    # ... (Methods _load_from_transcription, _load_from_file, _paste_text,
    #      _process_text_async, _run_llm_processing, _handle_llm_result,
    #      _set_ui_state, _update_status_from_processor, _copy_output, _save_output,
    #      _save_template, _delete_template, _populate_template_listbox,
    #      _on_template_select, _on_provider_change, set_model_safely, on_close
    #      remain the same as in the previous correct version provided in the chat history)
    # --- Methods previously moved or missing ---

    def _load_from_transcription(self):
        """Loads text from the main transcription result area into the LLM input."""
        try:
            # Use the getter method from the main app
            transcription_text = self.gui_app.get_transcription_text()
            if transcription_text:
                if hasattr(self, 'input_text') and self.input_text.winfo_exists():
                    self.input_text.config(state=tk.NORMAL)
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", transcription_text)
                self.llm_status_var.set(self.gui_app.translate("llm_status_loaded_transcription"))
            else:
                messagebox.showwarning(self.gui_app.translate("warning_title"),
                                       self.gui_app.translate("llm_warn_no_transcription"), parent=self.frame)
        except tk.TclError: print("Error loading from transcription: Widget destroyed?", file=sys.__stderr__)
        except Exception as e: messagebox.showerror(self.gui_app.translate("error_title"), f"{self.gui_app.translate('llm_error_loading_transcription')}: {e}", parent=self.frame)

    def _load_from_file(self):
        """Loads text from a user-selected file into the LLM input."""
        file_types = [
            (self.gui_app.translate("text_files_label"), "*.txt"),
            (self.gui_app.translate("all_files_label"), "*.*")
        ]
        filepath = filedialog.askopenfilename(
            title=self.gui_app.translate("llm_select_file_title"),
            filetypes=file_types,
            parent=self.frame
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if hasattr(self, 'input_text') and self.input_text.winfo_exists():
                    self.input_text.config(state=tk.NORMAL)
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", content)
                self.llm_status_var.set(self.gui_app.translate("llm_status_loaded_file").format(filename=os.path.basename(filepath)))
            except tk.TclError: print("Error loading from file: Widget destroyed?", file=sys.__stderr__)
            except Exception as e: messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_reading_file").format(error=e), parent=self.frame)

    def _paste_text(self):
        """Pastes text from the clipboard into the LLM input."""
        try:
            clipboard_text = self.frame.clipboard_get()
            if clipboard_text:
                if hasattr(self, 'input_text') and self.input_text.winfo_exists():
                    self.input_text.config(state=tk.NORMAL)
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", clipboard_text)
                self.llm_status_var.set(self.gui_app.translate("llm_status_pasted"))
            else:
                # Handle clipboard being empty gracefully
                messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_clipboard_empty"), parent=self.frame)
        except tk.TclError:
             # This often happens if the clipboard is empty or contains non-text data
             messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_clipboard_empty_or_error"), parent=self.frame) # Use a more specific key
        except Exception as e:
             messagebox.showerror(self.gui_app.translate("error_title"), f"{self.gui_app.translate('llm_error_pasting')}: {e}", parent=self.frame)

    def _process_text_async(self):
        """Combines instructions and input, then starts LLM processing."""
        provider = self.llm_provider_var.get()
        api_key = self.llm_api_key_var.get()
        model = self.llm_model_var.get()
        user_text = ""; instruction_text = "";
        placeholder = self.gui_app.translate("llm_instructions_placeholder")

        if hasattr(self, 'input_text') and self.input_text.winfo_exists():
            user_text = self.input_text.get("1.0", tk.END).strip()
        if hasattr(self, 'instructions_text') and self.instructions_text.winfo_exists():
            instruction_text = self.instructions_text.get("1.0", tk.END).strip()

        # Use instructions only if they are present and not the placeholder
        effective_instruction = instruction_text if (instruction_text and instruction_text != placeholder) else ""

        # Combine instruction and user text
        final_user_text = f"{effective_instruction}\n\n{user_text}".strip() if effective_instruction else user_text

        # --- Validations ---
        if not provider:
            messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_no_provider"), parent=self.frame)
            return
        if not api_key:
             # Ask user if they want to proceed without an API key (might work for local/free models)
             if not messagebox.askyesno(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_api_key"), parent=self.frame):
                 return # User cancelled
        if not model:
            messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_no_model"), parent=self.frame)
            return
        if not user_text: # Check original user text, not combined
            messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_no_input"), parent=self.frame)
            return
        if not final_user_text: # Check combined text is not somehow empty
             messagebox.showerror(self.gui_app.translate("error_title"), "Combined input and instruction text is empty.", parent=self.frame)
             return

        # --- UI Update & Thread Start ---
        self._set_ui_state(processing=True) # Disable UI elements
        # Clear previous output
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
            try:
                self.output_text.config(state=tk.NORMAL)
                self.output_text.delete("1.0", tk.END)
                self.output_text.config(state=tk.DISABLED)
            except tk.TclError: pass

        # Start processing in a background thread
        thread = threading.Thread(target=self._run_llm_processing, args=(provider, api_key, model, final_user_text), daemon=True)
        thread.start()

    def _run_llm_processing(self, provider, api_key, model, combined_user_text):
        """Worker function called by the thread."""
        # Calls the LLM processor instance passed during init
        result_text, error_message = self.llm_processor.process_text(
            provider, api_key, model, combined_user_text
        )
        # Schedule GUI update back on the main thread
        if hasattr(self,'frame') and self.frame.winfo_exists():
            self.frame.after_idle(self._handle_llm_result, result_text, error_message)

    def _handle_llm_result(self, result_text, error_message):
        """Updates the GUI after LLM processing finishes."""
        if not hasattr(self,'frame') or not self.frame.winfo_exists(): return # Check if tab still exists

        output_exists = hasattr(self, 'output_text') and self.output_text.winfo_exists()

        if output_exists:
             try: self.output_text.config(state=tk.NORMAL); self.output_text.delete("1.0", tk.END)
             except tk.TclError: output_exists = False # Widget gone

        if error_message:
            error_display_text = f"{self.gui_app.translate('error_title')}: {error_message}"
            if output_exists: self.output_text.insert(tk.END, error_display_text)
            self.llm_status_var.set(self.gui_app.translate("llm_status_error"))
            messagebox.showerror(self.gui_app.translate("error_title"), error_message, parent=self.frame)
        elif result_text is not None:
            if output_exists: self.output_text.insert(tk.END, result_text)
            self.llm_status_var.set(self.gui_app.translate("llm_status_completed"))
        else:
            # Case where result is None and error is None (should ideally not happen)
            unknown_error_text = f"{self.gui_app.translate('error_title')}: {self.gui_app.translate('llm_error_unknown')}"
            if output_exists: self.output_text.insert(tk.END, unknown_error_text)
            self.llm_status_var.set(self.gui_app.translate("llm_status_error"))
            messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate('llm_error_unknown'), parent=self.frame)

        if output_exists:
             try: self.output_text.config(state=tk.DISABLED)
             except tk.TclError: pass

        self._set_ui_state(processing=False) # Re-enable UI

    def _set_ui_state(self, processing: bool):
        """Enable/disable controls during processing."""
        state = tk.DISABLED if processing else tk.NORMAL
        action_state = tk.DISABLED if processing else "readonly" # For comboboxes
        text_state = tk.DISABLED if processing else tk.NORMAL # For text areas

        # Define widgets and their target state
        widgets_to_toggle = {
            'load_from_trans_button': state, 'load_file_button': state, 'paste_button': state,
            'input_text': text_state,
            'provider_combo': action_state, 'api_key_entry': state,
            'instructions_text': text_state,
            'process_button': state,
            'template_listbox': state, 'save_template_button': state, 'delete_template_button': state
        }

        try:
            for name, target_state in widgets_to_toggle.items():
                widget = getattr(self, name, None)
                if widget and widget.winfo_exists():
                    widget.config(state=target_state)

            # Handle model combobox separately (depends on provider and models)
            if hasattr(self,'model_combo') and self.model_combo.winfo_exists():
                if processing:
                    self.model_combo.config(state=tk.DISABLED)
                else:
                    # Re-enable only if provider is selected and has models
                    has_models = bool(self.model_combo.cget('values'))
                    self.model_combo.config(state="readonly" if self.llm_provider_var.get() and has_models else tk.DISABLED)

            # Handle output buttons based on output text content (only when enabling)
            if not processing:
                 output_empty = True
                 if hasattr(self, 'output_text') and self.output_text.winfo_exists():
                     try:
                         original_state = self.output_text.cget('state')
                         self.output_text.config(state=tk.NORMAL)
                         output_empty = not self.output_text.get("1.0", tk.END).strip()
                         self.output_text.config(state=original_state) # Restore original state
                     except tk.TclError: pass # Ignore if widget destroyed during check
                 copy_btn_state = tk.NORMAL if not output_empty else tk.DISABLED
                 save_btn_state = tk.NORMAL if not output_empty else tk.DISABLED
                 if hasattr(self,'copy_output_button') and self.copy_output_button.winfo_exists(): self.copy_output_button.config(state=copy_btn_state)
                 if hasattr(self,'save_output_button') and self.save_output_button.winfo_exists(): self.save_output_button.config(state=save_btn_state)
            else:
                 # Disable output buttons during processing
                 if hasattr(self,'copy_output_button') and self.copy_output_button.winfo_exists(): self.copy_output_button.config(state=tk.DISABLED)
                 if hasattr(self,'save_output_button') and self.save_output_button.winfo_exists(): self.save_output_button.config(state=tk.DISABLED)


            # Update status label during processing
            if processing:
                 if hasattr(self,'llm_status_var'):
                     self.llm_status_var.set(self.gui_app.translate("llm_status_processing"))

        except tk.TclError as e:
            print(f"LLM Tab: Error setting UI state (TclError: {e})", file=sys.__stderr__)
        except Exception as e:
            import traceback
            print(f"LLM Tab: Error setting UI state (Exception: {e}\n{traceback.format_exc()})", file=sys.__stderr__)

    def _update_status_from_processor(self, message):
         """Callback for LLMProcessor to update status label via main thread."""
         if hasattr(self, 'llm_status_var') and hasattr(self, 'frame') and self.frame.winfo_exists():
             # Use after_idle to ensure this runs in the main GUI thread
             self.frame.after_idle(lambda m=message: self.llm_status_var.set(m))

    def _copy_output(self):
        """Copies the LLM output text to the clipboard."""
        text_to_copy = ""; copied = False
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
            try:
                # Temporarily enable to get text
                original_state = self.output_text.cget('state')
                self.output_text.config(state=tk.NORMAL)
                text_to_copy = self.output_text.get("1.0", tk.END).strip()
                self.output_text.config(state=original_state) # Restore state
            except tk.TclError: pass # Widget might be destroyed
        if not text_to_copy:
            messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_output_to_copy"), parent=self.frame)
            return
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(text_to_copy)
            self.frame.update() # Make sure clipboard content is updated
            copied = True
        except tk.TclError as e:
            messagebox.showerror(self.gui_app.translate("error_title"), f"{self.gui_app.translate('llm_error_copying')}\n{e}", parent=self.frame)
        if copied:
            # Optionally show a brief confirmation
            messagebox.showinfo(self.gui_app.translate("copied_title"), self.gui_app.translate("llm_info_copied_output"), parent=self.frame)

    def _save_output(self):
        """Saves the LLM output text to a file."""
        text_to_save = ""
        if hasattr(self, 'output_text') and self.output_text.winfo_exists():
             try:
                 original_state = self.output_text.cget('state')
                 self.output_text.config(state=tk.NORMAL)
                 text_to_save = self.output_text.get("1.0", tk.END).strip()
                 self.output_text.config(state=original_state)
             except tk.TclError: pass
        if not text_to_save:
            messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_warn_no_output_to_save"), parent=self.frame)
            return

        file_types = [
            (self.gui_app.translate("text_files_label"), "*.txt"),
            (self.gui_app.translate("all_files_label"), "*.*")
        ]
        filepath = filedialog.asksaveasfilename(
            title=self.gui_app.translate("llm_save_output_title"),
            defaultextension=".txt",
            filetypes=file_types,
            initialfile="llm_output.txt", # Suggest a default name
            parent=self.frame
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(text_to_save)
                messagebox.showinfo(self.gui_app.translate("saved_title"), self.gui_app.translate("llm_info_saved_output").format(file=os.path.basename(filepath)), parent=self.frame)
            except Exception as e:
                messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_saving_output").format(error=e), parent=self.frame)

    def _save_template(self):
        """Saves the current instructions text as a new custom template."""
        if not hasattr(self, 'instructions_text') or not self.instructions_text.winfo_exists(): return
        try:
            template_text = self.instructions_text.get("1.0", tk.END).strip()
        except tk.TclError: return

        if not template_text or template_text == self.gui_app.translate("llm_instructions_placeholder"):
            messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_error_saving_template_text"), parent=self.frame)
            return

        template_name = simpledialog.askstring(
            self.gui_app.translate("llm_save_template_prompt_title"),
            self.gui_app.translate("llm_save_template_prompt_text"),
            parent=self.frame
        )

        if template_name:
            template_name = template_name.strip()
            if not template_name:
                messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_saving_template_name"), parent=self.frame)
                return

            # Check for conflicts with predefined keys (case-insensitive check might be better?)
            # Or check against the *translated* predefined names? Let's stick to keys for simplicity.
            if template_name in self.PREDEFINED_TEMPLATES or template_name == "--- Custom ---": # Use the separator string directly
                messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_saving_template_reserved"), parent=self.frame) # Use specific error key
                return

            self.custom_templates[template_name] = template_text
            self._populate_template_listbox()
            # Try to select the newly added template
            try:
                # Get all items, find the index of the new name
                all_items = self.template_listbox.get(0, tk.END)
                idx = all_items.index(template_name)
                self.template_listbox.selection_clear(0, tk.END) # Clear previous selection
                self.template_listbox.selection_set(idx)
                self.template_listbox.see(idx) # Scroll to the new item
            except ValueError:
                pass # Should not happen if populate worked correctly
            messagebox.showinfo(self.gui_app.translate("llm_template_saved_title"), self.gui_app.translate("llm_template_saved_msg").format(name=template_name), parent=self.frame)
        else:
            print("Template save cancelled.") # User pressed Cancel

    def _delete_template(self):
        """Deletes the selected custom template."""
        if not hasattr(self, 'template_listbox') or not self.template_listbox.winfo_exists(): return

        selected_indices = self.template_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("llm_error_delete_no_selection"), parent=self.frame)
            return

        selected_name = self.template_listbox.get(selected_indices[0])

        # Check if it's a predefined template key or the separator
        if selected_name in self.PREDEFINED_TEMPLATES or selected_name == "--- Custom ---":
            messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("llm_error_delete_predefined"), parent=self.frame)
            return

        # Confirm it's a custom template we know about
        if selected_name in self.custom_templates:
            if messagebox.askyesno(self.gui_app.translate("llm_confirm_delete_title"), self.gui_app.translate("llm_confirm_delete_msg").format(name=selected_name), parent=self.frame):
                del self.custom_templates[selected_name]
                self._populate_template_listbox()
                # Clear instructions if the deleted template was loaded
                if hasattr(self, 'instructions_text') and self.instructions_text.winfo_exists():
                     try:
                         current_inst = self.instructions_text.get("1.0", tk.END).strip()
                         # Check if the current text *was* the deleted template's text
                         # This is tricky, maybe just clear if the *selected* name matches? Safer: always clear.
                         self.instructions_text.delete("1.0", tk.END)
                         self.instructions_text.insert("1.0", self.gui_app.translate("llm_instructions_placeholder"))
                     except tk.TclError: pass
                self.selected_template_name.set("") # Clear selection variable
                messagebox.showinfo(self.gui_app.translate("llm_template_deleted_title"), self.gui_app.translate("llm_template_deleted_msg").format(name=selected_name), parent=self.frame)
        else:
            # This case might happen if the listbox gets out of sync with the dictionary
            messagebox.showerror(self.gui_app.translate("error_title"), f"Template '{selected_name}' not found in custom templates dictionary.", parent=self.frame)


    def _populate_template_listbox(self):
        """Clears and repopulates the template listbox, preserving selection if possible."""
        if not hasattr(self, 'template_listbox') or not self.template_listbox.winfo_exists(): return

        previously_selected_name = self.selected_template_name.get()
        new_selection_index = None

        try:
            self.template_listbox.config(state=tk.NORMAL) # Enable for modification
            self.template_listbox.delete(0, tk.END)

            current_index = 0
            # Add predefined templates (using translated names if desired, but keys are safer for logic)
            for name_key in self.PREDEFINED_TEMPLATES.keys():
                # display_name = self.gui_app.translate(name_key) # Could use translated name
                display_name = name_key # Using the key is simpler for matching later
                self.template_listbox.insert(tk.END, display_name)
                if display_name == previously_selected_name:
                    new_selection_index = current_index
                current_index += 1

            # Add separator and custom templates
            if self.custom_templates:
                 separator = "--- Custom ---"
                 self.template_listbox.insert(tk.END, separator)
                 # Don't track selection for the separator
                 current_index += 1
                 # Sort custom keys for consistent order
                 for name in sorted(self.custom_templates.keys()):
                     self.template_listbox.insert(tk.END, name)
                     if name == previously_selected_name:
                         new_selection_index = current_index
                     current_index += 1

            # Restore selection if the item still exists
            if new_selection_index is not None:
                self.template_listbox.selection_set(new_selection_index)
                self.template_listbox.see(new_selection_index)
            else:
                 self.selected_template_name.set("") # Clear selection if item disappeared

            self.template_listbox.config(state=tk.NORMAL) # Keep enabled for user selection

        except tk.TclError as e:
            print(f"LLM Tab: TclError populating template listbox: {e}", file=sys.__stderr__)
            # Attempt to recover state if possible
            if hasattr(self, 'template_listbox') and self.template_listbox.winfo_exists():
                self.template_listbox.config(state=tk.NORMAL)


    def _on_template_select(self, event=None):
        """Handles selection change in the template listbox."""
        if not hasattr(self, 'template_listbox') or not self.template_listbox.winfo_exists(): return

        selected_indices = self.template_listbox.curselection()
        if not selected_indices:
            self.selected_template_name.set("") # Clear selection if nothing is selected
            return

        selected_name = self.template_listbox.get(selected_indices[0])
        self.selected_template_name.set(selected_name) # Update the tracking variable

        template_text = ""
        if selected_name in self.PREDEFINED_TEMPLATES:
            # Get the actual template text using the translation key
            template_key = self.PREDEFINED_TEMPLATES[selected_name]
            template_text = self.gui_app.translate(template_key)
        elif selected_name in self.custom_templates:
            template_text = self.custom_templates[selected_name]
        elif selected_name == "--- Custom ---":
            # Don't load text for the separator, maybe clear instructions?
            template_text = self.gui_app.translate("llm_instructions_placeholder") # Or ""
            # return # Or just load placeholder

        # Update instructions text area
        if hasattr(self, 'instructions_text') and self.instructions_text.winfo_exists():
            try:
                self.instructions_text.config(state=tk.NORMAL)
                self.instructions_text.delete("1.0", tk.END)
                if template_text: # Insert only if we have text (handles separator case implicitly if placeholder)
                    self.instructions_text.insert("1.0", template_text)
                # Keep instructions text NORMAL for editing
            except tk.TclError: pass


    def _on_provider_change(self, *args):
        """Updates the model combobox when the provider changes."""
        selected_provider = self.llm_provider_var.get()
        print(f"LLM Tab: Provider changed to '{selected_provider}'")
        models = self.llm_processor.get_models_for_provider(selected_provider)

        try:
            if hasattr(self, 'model_combo') and self.model_combo.winfo_exists():
                # Always update the list of choices
                self.model_combo.config(values=models if models else []) # Ensure it's a list

                if models:
                    # If the current model isn't valid for the new provider, select the first model
                    current_model = self.llm_model_var.get()
                    if current_model not in models:
                        self.llm_model_var.set(models[0])
                        print(f"LLM Tab: Set default model to {models[0]}")
                    else:
                        print(f"LLM Tab: Kept existing model {current_model}") # Keep existing if valid
                    self.model_combo.config(state="readonly") # Enable selection
                else:
                    # No models for this provider
                    self.llm_model_var.set("") # Clear model variable
                    self.model_combo.config(state="disabled") # Disable combobox
                    print("LLM Tab: No models found, disabling model combobox.")
            else:
                print("LLM Tab Warning: Model combobox not available during provider change.", file=sys.__stderr__)
        except tk.TclError as e:
             print(f"LLM Tab: TclError during provider change handling: {e}", file=sys.__stderr__)
        except Exception as e:
             import traceback
             print(f"LLM Tab: Error during provider change handling: {e}\n{traceback.format_exc()}", file=sys.__stderr__)


    def set_model_safely(self, model_name_to_set: str):
        """Sets the model combobox value AFTER its list has been updated."""
        try:
            if hasattr(self, 'model_combo') and self.model_combo.winfo_exists():
                # Get the list of models currently in the combobox
                available_models_tcl = self.model_combo.cget('values')
                available_models = []
                # The value might be a Tcl list string like '{model1 model2}' or a Python list/tuple
                if isinstance(available_models_tcl, str):
                    try:
                        # Attempt to parse the Tcl list string
                        available_models = list(self.model_combo.tk.splitlist(available_models_tcl))
                    except (tk.TclError, ValueError, SyntaxError):
                        print(f"LLM Tab Warning: Could not parse model list string: '{available_models_tcl}'", file=sys.__stderr__)
                        available_models = [] # Fallback to empty list
                elif isinstance(available_models_tcl, (list, tuple)):
                    available_models = list(available_models_tcl)
                else:
                    available_models = [] # Fallback

                if model_name_to_set in available_models:
                    self.llm_model_var.set(model_name_to_set)
                    print(f"LLM Tab: Set model from config: {model_name_to_set}")
                else:
                    print(f"LLM Tab Warning: Saved model '{model_name_to_set}' not valid for provider '{self.llm_provider_var.get()}'. Current models: {available_models}")
                    # Optionally set to the first available model if the saved one is invalid
                    if available_models:
                        self.llm_model_var.set(available_models[0])
                        print(f"LLM Tab: Setting model to first available: {available_models[0]}")
                    else:
                        self.llm_model_var.set("") # No models available
            else:
                print("LLM Tab: Model combobox not ready to set model.")
        except tk.TclError as e:
            print(f"LLM Tab: TclError setting model '{model_name_to_set}': {e}", file=sys.__stderr__)
        except Exception as e:
            import traceback
            print(f"LLM Tab: Error in set_model_safely: {e}\n{traceback.format_exc()}", file=sys.__stderr__)

    def on_close(self):
        """Cleanup actions when the application is closing."""
        print("LLM Tab closing.")
        # No specific resources to release here currently (threads are daemons)
        pass

# --- END OF REVISED llm_tab.py ---