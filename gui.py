# --- START OF MODIFIED FILE gui.py ---

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import io
import os
import sys
from tkinter.scrolledtext import ScrolledText
# from datetime import timedelta # Moved formatting to utils
from transcriber import AudioTranscriber
from utils import format_duration # Import the utility
from recorder_tab import RecorderTab
# --- NEW: Import LLM components ---
from llm_tab import LLMTab
from llm_processor import LLMProcessor
# --- END NEW ---
import json # Used for potentially loading translations later if needed


class ConsoleOutput(io.StringIO):
    # ... (Keep ConsoleOutput class as is) ...
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, message):
        try:
            if self.text_widget.winfo_exists():
                self.text_widget.after_idle(self._insert_text, message)
        except tk.TclError:
            print(f"Console Write Error (widget destroyed?): {message.strip()}")
            pass
        except Exception as e:
             print(f"Console Write Error (General Exception): {e} - Message: {message.strip()}")
        super().write(message)

    def _insert_text(self, message):
        try:
            if self.text_widget.winfo_exists():
                self.text_widget.insert(tk.END, message)
                self.text_widget.see(tk.END)
        except tk.TclError:
             print(f"Console Insert Error (widget destroyed?): {message.strip()}")
        except Exception as e:
             print(f"Console Insert Error (General Exception): {e} - Message: {message.strip()}")


class ModernTranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.transcriber = AudioTranscriber(self)
        self.llm_processor = LLMProcessor() # NEW: Instantiate LLM Processor
        self.system_type = "mac" if sys.platform == "darwin" else "windows"

        self.setup_translations() # Define translations first
        self.current_language = tk.StringVar(value="English") # Default language code

        # Initialize variables that depend on translation AFTER translations are set up
        self.status_var = tk.StringVar(value=self.translate("status_ready"))
        self.current_task = tk.StringVar(value="")
        self.model_desc_var = tk.StringVar(value=self.translate("model_desc_large"))

        self.setup_ui_styles()
        self.create_widgets() # Create all widgets

        # Set up the trace *after* widgets are created
        self.current_language.trace_add("write", self.change_language)

        # Call update_ui_text AFTER all widgets, including tab widgets, are created
        self.update_ui_text()

        # Redirect stdout only after console widget exists and UI is built
        if hasattr(self, 'console_output') and self.console_output and self.console_output.winfo_exists():
            sys.stdout = ConsoleOutput(self.console_output)
            print(self.translate("welcome_message"))
        else:
            print("WARNING: Console output widget not found or ready, stdout not redirected.")

        # Handle application closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)


    def setup_translations(self):
        # --- NEW: LLM Tab Translations ---
        llm_translations_it = {
            "tab_llm": "Elaborazione LLM",
            "llm_input_label": "Testo di Input:",
            "llm_load_transcription": "⎗ Carica da Trascrizione",
            "llm_load_file": "📂 Carica File...",
            "llm_paste": "📋 Incolla",
            "llm_config_frame": "Configurazione LLM",
            "llm_provider_label": "Provider API:",
            "llm_api_key_label": "Chiave API:",
            "llm_model_label": "Modello:",
            "llm_instructions_label": "Istruzioni (Prompt di Sistema):",
            "llm_instructions_placeholder": "Es: Riassumi il testo seguente in punti chiave.",
            "llm_process_button": "✨ Elabora con LLM",
            "llm_output_label": "Risultato LLM:",
            "llm_copy_output": "📋 Copia Output",
            "llm_save_output": "💾 Salva Output...",
            "llm_status_loaded_transcription": "Caricato dalla trascrizione.",
            "llm_status_loaded_file": "File caricato: {filename}",
            "llm_status_pasted": "Testo incollato dagli appunti.",
            "llm_status_processing": "Elaborazione LLM in corso...",
            "llm_status_completed": "Elaborazione LLM completata.",
            "llm_status_error": "Errore durante l'elaborazione LLM.",
            "llm_status_ready": "Pronto per l'elaborazione LLM.",
            "llm_select_file_title": "Seleziona File di Testo",
            "llm_save_output_title": "Salva Output LLM",
            "llm_warn_no_transcription": "Nessun testo di trascrizione disponibile da caricare.",
            "llm_error_loading_transcription": "Errore nel caricare il testo della trascrizione",
            "llm_error_reading_file": "Errore nella lettura del file: {error}",
            "llm_warn_clipboard_empty": "Nessun testo trovato negli appunti.",
            "llm_error_pasting": "Errore durante l'operazione Incolla",
            "llm_error_no_provider": "Seleziona un provider API LLM!",
            "llm_error_no_model": "Seleziona un modello LLM!",
            "llm_error_no_input": "Inserisci del testo nell'area di Input!",
            "llm_warn_no_api_key": "La chiave API è vuota. Assicurati che sia impostata tramite variabili d'ambiente o inseriscila qui. Continuare?",
            "llm_error_unknown": "Si è verificato un errore sconosciuto durante l'elaborazione.",
            "llm_warn_no_output_to_copy": "Nessun output da copiare.",
            "llm_warn_no_output_to_save": "Nessun output da salvare.",
            "llm_info_copied_output": "Output LLM copiato negli appunti!",
            "llm_info_saved_output": "Output LLM salvato in {file}",
            "llm_error_copying": "Errore durante la copia dell'output LLM.",
            "llm_error_saving_output": "Errore durante il salvataggio dell'output LLM: {error}"
        }
        llm_translations_en = {
            "tab_llm": "LLM Processing",
            "llm_input_label": "Input Text:",
            "llm_load_transcription": "⎗ Load from Transcription",
            "llm_load_file": "📂 Load File...",
            "llm_paste": "📋 Paste",
            "llm_config_frame": "LLM Configuration",
            "llm_provider_label": "API Provider:",
            "llm_api_key_label": "API Key:",
            "llm_model_label": "Model:",
            "llm_instructions_label": "Instructions (System Prompt):",
            "llm_instructions_placeholder": "E.g.: Summarize the following text into key bullet points.",
            "llm_process_button": "✨ Process with LLM",
            "llm_output_label": "LLM Result:",
            "llm_copy_output": "📋 Copy Output",
            "llm_save_output": "💾 Save Output...",
            "llm_status_loaded_transcription": "Loaded from transcription.",
            "llm_status_loaded_file": "Loaded file: {filename}",
            "llm_status_pasted": "Pasted text from clipboard.",
            "llm_status_processing": "LLM processing...",
            "llm_status_completed": "LLM processing completed.",
            "llm_status_error": "Error during LLM processing.",
            "llm_status_ready": "Ready for LLM processing.",
            "llm_select_file_title": "Select Text File",
            "llm_save_output_title": "Save LLM Output",
            "llm_warn_no_transcription": "No transcription text available to load.",
            "llm_error_loading_transcription": "Error loading transcription text",
            "llm_error_reading_file": "Error reading file: {error}",
            "llm_warn_clipboard_empty": "No text found on clipboard.",
            "llm_error_pasting": "Error during paste operation",
            "llm_error_no_provider": "Please select an LLM API provider!",
            "llm_error_no_model": "Please select an LLM model!",
            "llm_error_no_input": "Please enter text in the Input area!",
            "llm_warn_no_api_key": "API Key is empty. Ensure it's set via environment variables or enter it here. Continue?",
            "llm_error_unknown": "An unknown error occurred during processing.",
            "llm_warn_no_output_to_copy": "No output to copy.",
            "llm_warn_no_output_to_save": "No output to save.",
            "llm_info_copied_output": "LLM output copied to clipboard!",
            "llm_info_saved_output": "LLM output saved to {file}",
            "llm_error_copying": "Error copying LLM output.",
            "llm_error_saving_output": "Error saving LLM output: {error}"
        }
        llm_translations_fr = {
            "tab_llm": "Traitement LLM",
            "llm_input_label": "Texte d'Entrée :",
            "llm_load_transcription": "⎗ Charger depuis Transcription",
            "llm_load_file": "📂 Charger Fichier...",
            "llm_paste": "📋 Coller",
            "llm_config_frame": "Configuration LLM",
            "llm_provider_label": "Fournisseur API :",
            "llm_api_key_label": "Clé API :",
            "llm_model_label": "Modèle :",
            "llm_instructions_label": "Instructions (Prompt Système) :",
            "llm_instructions_placeholder": "Ex : Résumez le texte suivant en points clés.",
            "llm_process_button": "✨ Traiter avec LLM",
            "llm_output_label": "Résultat LLM :",
            "llm_copy_output": "📋 Copier Sortie",
            "llm_save_output": "💾 Enregistrer Sortie...",
            "llm_status_loaded_transcription": "Chargé depuis la transcription.",
            "llm_status_loaded_file": "Fichier chargé : {filename}",
            "llm_status_pasted": "Texte collé depuis le presse-papiers.",
            "llm_status_processing": "Traitement LLM en cours...",
            "llm_status_completed": "Traitement LLM terminé.",
            "llm_status_error": "Erreur pendant le traitement LLM.",
            "llm_status_ready": "Prêt pour le traitement LLM.",
            "llm_select_file_title": "Sélectionner un Fichier Texte",
            "llm_save_output_title": "Enregistrer la Sortie LLM",
            "llm_warn_no_transcription": "Aucun texte de transcription disponible à charger.",
            "llm_error_loading_transcription": "Erreur lors du chargement du texte de transcription",
            "llm_error_reading_file": "Erreur de lecture du fichier : {error}",
            "llm_warn_clipboard_empty": "Aucun texte trouvé dans le presse-papiers.",
            "llm_error_pasting": "Erreur lors de l'opération Coller",
            "llm_error_no_provider": "Veuillez sélectionner un fournisseur d'API LLM !",
            "llm_error_no_model": "Veuillez sélectionner un modèle LLM !",
            "llm_error_no_input": "Veuillez entrer du texte dans la zone d'Entrée !",
            "llm_warn_no_api_key": "La clé API est vide. Assurez-vous qu'elle est définie via les variables d'environnement ou saisissez-la ici. Continuer ?",
            "llm_error_unknown": "Une erreur inconnue s'est produite lors du traitement.",
            "llm_warn_no_output_to_copy": "Aucune sortie à copier.",
            "llm_warn_no_output_to_save": "Aucune sortie à enregistrer.",
            "llm_info_copied_output": "Sortie LLM copiée dans le presse-papiers !",
            "llm_info_saved_output": "Sortie LLM enregistrée dans {file}",
            "llm_error_copying": "Erreur lors de la copie de la sortie LLM.",
            "llm_error_saving_output": "Erreur lors de l'enregistrement de la sortie LLM : {error}"
        }
        llm_translations_zh = {
            "tab_llm": "LLM 处理",
            "llm_input_label": "输入文本:",
            "llm_load_transcription": "⎗ 从转录加载",
            "llm_load_file": "📂 加载文件...",
            "llm_paste": "📋 粘贴",
            "llm_config_frame": "LLM 配置",
            "llm_provider_label": "API 提供商:",
            "llm_api_key_label": "API 密钥:",
            "llm_model_label": "模型:",
            "llm_instructions_label": "说明 (系统提示):",
            "llm_instructions_placeholder": "例如：将以下文本总结为关键要点。",
            "llm_process_button": "✨ 使用 LLM 处理",
            "llm_output_label": "LLM 结果:",
            "llm_copy_output": "📋 复制输出",
            "llm_save_output": "💾 保存输出...",
            "llm_status_loaded_transcription": "已从转录加载。",
            "llm_status_loaded_file": "已加载文件: {filename}",
            "llm_status_pasted": "已从剪贴板粘贴文本。",
            "llm_status_processing": "LLM 处理中...",
            "llm_status_completed": "LLM 处理完成。",
            "llm_status_error": "LLM 处理过程中出错。",
            "llm_status_ready": "准备进行 LLM 处理。",
            "llm_select_file_title": "选择文本文件",
            "llm_save_output_title": "保存 LLM 输出",
            "llm_warn_no_transcription": "没有可加载的转录文本。",
            "llm_error_loading_transcription": "加载转录文本时出错",
            "llm_error_reading_file": "读取文件时出错: {error}",
            "llm_warn_clipboard_empty": "剪贴板中未找到文本。",
            "llm_error_pasting": "粘贴操作期间出错",
            "llm_error_no_provider": "请选择一个 LLM API 提供商！",
            "llm_error_no_model": "请选择一个 LLM 模型！",
            "llm_error_no_input": "请在输入区域输入文本！",
            "llm_warn_no_api_key": "API 密钥为空。请确保通过环境变量设置或在此处输入。继续？",
            "llm_error_unknown": "处理过程中发生未知错误。",
            "llm_warn_no_output_to_copy": "没有要复制的输出。",
            "llm_warn_no_output_to_save": "没有要保存的输出。",
            "llm_info_copied_output": "LLM 输出已复制到剪贴板！",
            "llm_info_saved_output": "LLM 输出已保存到 {file}",
            "llm_error_copying": "复制 LLM 输出时出错。",
            "llm_error_saving_output": "保存 LLM 输出时出错: {error}"
        }
        # --- END NEW LLM Translations ---

        self.translations = {
            "Italiano": {
                # ... (existing Italian translations) ...
                **llm_translations_it # Merge LLM translations
            },
            "English": {
                # ... (existing English translations) ...
                **llm_translations_en # Merge LLM translations
            },
             "Francais": {
                # ... (existing French translations) ...
                **llm_translations_fr # Merge LLM translations
             },
             "中文": {
                # ... (existing Chinese translations) ...
                **llm_translations_zh # Merge LLM translations
             }
        }
        self.model_descriptions = {
            "tiny": "model_desc_tiny",
            "base": "model_desc_base",
            "small": "model_desc_small",
            "medium": "model_desc_medium",
            "large": "model_desc_large",
        }

    def translate(self, key):
        # ... (translate method remains the same) ...
        lang_code = self.current_language.get()
        return self.translations.get(lang_code, self.translations['English']).get(key, f"<{key}>")


    def setup_ui_styles(self):
        # ... (setup_ui_styles method remains the same) ...
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except tk.TclError:
             available_themes = self.style.theme_names()
             print(f"Theme 'clam' not found. Available themes: {available_themes}")
             if available_themes:
                 self.style.theme_use(available_themes[0]) # Use first available as fallback

        self.primary_color = "#3498db"; self.secondary_color = "#2980b9"; self.bg_color = "#f5f5f5"
        self.text_color = "#2c3e50"; self.success_color = "#2ecc71"; self.warning_color = "#e74c3c"
        self.root.configure(bg=self.bg_color)
        default_font = ("Segoe UI", 10); bold_font = ("Segoe UI", 10, "bold")
        heading_font = ("Segoe UI", 14, "bold"); console_font = ("Consolas", 10)

        self.style.configure("Card.TFrame", background=self.bg_color, relief="raised", borderwidth=1)
        self.style.configure("Primary.TButton", background=self.primary_color, foreground="white", padding=10, font=bold_font)
        self.style.map("Primary.TButton", background=[("active", self.secondary_color), ("disabled", "#bdc3c7")]) # Adjusted disabled color
        self.style.configure("Action.TButton", background=self.secondary_color, foreground="white", padding=8, font=("Segoe UI", 9))
        self.style.map("Action.TButton", background=[("active", self.primary_color), ("disabled", "#bdc3c7")]) # Adjusted disabled color
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=default_font)
        self.style.configure("Heading.TLabel", background=self.bg_color, foreground=self.text_color, font=heading_font)
        self.style.configure("Status.TLabel", background="#ecf0f1", foreground=self.text_color, padding=5, relief="sunken", font=default_font)
        self.style.configure("TProgressbar", background=self.primary_color, troughcolor="#d1d1d1", thickness=10)
        self.style.configure("TCombobox", padding=5, font=default_font)
        self.style.configure("TLabelframe.Label", font=bold_font, foreground=self.text_color, background=self.bg_color)
        self.style.configure("TRadiobutton", background=self.bg_color, font=default_font)
        self.style.configure("TNotebook.Tab", font=default_font, padding=[5, 2])


    def create_widgets(self):
        # --- Variables ---
        self.file_path = tk.StringVar()
        self.model_var = tk.StringVar(value="large")
        self.transcription_language_var = tk.StringVar(value="italiano")
        self.progress_var = tk.DoubleVar(value=0)
        self.use_gpu_var = tk.BooleanVar(value=False)
        # Status vars initialized in __init__

        # --- Main Layout (Header + Notebook) ---
        self.header_frame = ttk.Frame(self.root, style="Card.TFrame", padding=(20, 10, 20, 10))
        # ... (Header frame content remains the same - Title, Subtitle, Language Selector) ...
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        self.header_frame.columnconfigure(1, weight=1)
        self.app_title_label = ttk.Label(self.header_frame, text="", style="Heading.TLabel")
        self.app_title_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.app_subtitle_label = ttk.Label(self.header_frame, text="", style="TLabel")
        self.app_subtitle_label.grid(row=0, column=1, sticky="w", padx=(0, 20))
        lang_select_frame = ttk.Frame(self.header_frame, style="Card.TFrame")
        lang_select_frame.grid(row=0, column=2, sticky="e")
        self.lang_select_label = ttk.Label(lang_select_frame, text="")
        self.lang_select_label.pack(side=tk.LEFT, padx=(0, 5))
        self.lang_options = {"English": "English", "Italiano": "Italiano", "Français": "Français", "中文": "中文"}
        self.language_selector = ttk.Combobox(lang_select_frame, textvariable=self.current_language,
                                              values=list(self.lang_options.keys()), state="readonly", width=10)
        self.language_selector.set("English") # Default display name
        self.language_selector.bind("<<ComboboxSelected>>", self.on_language_select)
        self.language_selector.pack(side=tk.LEFT)


        # --- Main Content Notebook ---
        self.main_notebook = ttk.Notebook(self.root, padding=(20, 10, 20, 10))
        self.main_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # --- Create Transcription Tab Frame ---
        self.transcription_tab_frame = ttk.Frame(self.main_notebook, padding="10") # Store reference
        # Add transcription tab FIRST (index 0)
        self.main_notebook.add(self.transcription_tab_frame, text="") # Text set in update_ui_text
        # Configure grid for transcription tab content
        self.transcription_tab_frame.columnconfigure(0, weight=1)
        self.transcription_tab_frame.rowconfigure(4, weight=1) # Make results notebook expand

        # --- Widgets for Transcription Tab (inside transcription_tab_frame) ---
        # ... (File selection, Options, Buttons, Progress - remain the same) ...
        self.file_frame = ttk.LabelFrame(self.transcription_tab_frame, text="", padding=10)
        self.file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15)); self.file_frame.columnconfigure(1, weight=1)
        self.wav_file_label = ttk.Label(self.file_frame, text=""); self.wav_file_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path, width=60); self.file_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.browse_button = ttk.Button(self.file_frame, text="", command=self.select_file, style="Action.TButton"); self.browse_button.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        self.options_frame = ttk.LabelFrame(self.transcription_tab_frame, text="", padding=10)
        self.options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15)); self.options_frame.columnconfigure(2, weight=1)
        self.model_label = ttk.Label(self.options_frame, text=""); self.model_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        models = ["tiny", "base", "small", "medium", "large"]
        self.model_combobox = ttk.Combobox(self.options_frame, textvariable=self.model_var, values=models, state="readonly", width=15); self.model_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5); self.model_combobox.set("large")
        self.model_desc_label = ttk.Label(self.options_frame, textvariable=self.model_desc_var, anchor="w"); self.model_desc_label.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
        self.model_combobox.bind("<<ComboboxSelected>>", self.update_model_description)
        self.transcription_language_label = ttk.Label(self.options_frame, text=""); self.transcription_language_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.transcription_languages = ["italiano", "inglese", "francese", "tedesco", "spagnolo", "giapponese", "cinese"]
        self.language_combobox = ttk.Combobox(self.options_frame, textvariable=self.transcription_language_var, values=self.transcription_languages, state="readonly", width=15); self.language_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5); self.language_combobox.set("italiano")
        self.acceleration_label = ttk.Label(self.options_frame, text=""); self.acceleration_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.gpu_check = ttk.Checkbutton(self.options_frame, text="", variable=self.use_gpu_var); self.gpu_check.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        self.gpu_check.bind("<Enter>", self.show_gpu_tooltip); self.gpu_tooltip = None

        buttons_frame = ttk.Frame(self.transcription_tab_frame); buttons_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self.start_button = ttk.Button(buttons_frame, text="", command=self.start_transcription, style="Primary.TButton"); self.start_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.stop_button = ttk.Button(buttons_frame, text="", command=self.stop_transcription, style="Action.TButton", state=tk.DISABLED); self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)
        action_buttons_right = ttk.Frame(buttons_frame); action_buttons_right.pack(side=tk.RIGHT)
        self.save_button = ttk.Button(action_buttons_right, text="", command=self.save_transcription, style="Action.TButton"); self.save_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.copy_button = ttk.Button(action_buttons_right, text="", command=self.copy_to_clipboard, style="Action.TButton"); self.copy_button.pack(side=tk.RIGHT, padx=5, pady=5)

        progress_frame = ttk.Frame(self.transcription_tab_frame); progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15)); progress_frame.columnconfigure(0, weight=1)
        self.current_task_label = ttk.Label(progress_frame, textvariable=self.current_task, anchor="w"); self.current_task_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, mode="indeterminate", length=100, style="TProgressbar"); self.progress_bar.grid(row=1, column=0, sticky="ew")


        # --- Results Notebook (Transcription Text / Console) ---
        self.results_notebook = ttk.Notebook(self.transcription_tab_frame)
        self.results_notebook.grid(row=4, column=0, sticky="nsew", pady=(0, 5))

        # -- Transcription Result Tab --
        transcription_result_frame = ttk.Frame(self.results_notebook, padding=10); transcription_result_frame.pack(fill=tk.BOTH, expand=True); transcription_result_frame.columnconfigure(0, weight=1); transcription_result_frame.rowconfigure(1, weight=1)
        self.results_notebook.add(transcription_result_frame, text="") # Text set later
        self.transcription_result_label = ttk.Label(transcription_result_frame, text=""); self.transcription_result_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        result_text_frame = ttk.Frame(transcription_result_frame, borderwidth=1, relief="sunken"); result_text_frame.grid(row=1, column=0, sticky="nsew"); result_text_frame.rowconfigure(0, weight=1); result_text_frame.columnconfigure(0, weight=1)
        self.result_text = ScrolledText(result_text_frame, wrap=tk.WORD, width=80, height=10, font=("Segoe UI", 11), background="white", foreground=self.text_color, borderwidth=0, relief="flat"); self.result_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # -- Console Tab --
        console_frame = ttk.Frame(self.results_notebook, padding=10); console_frame.pack(fill=tk.BOTH, expand=True); console_frame.columnconfigure(0, weight=1); console_frame.rowconfigure(1, weight=1)
        self.results_notebook.add(console_frame, text="") # Text set later
        self.console_output_label = ttk.Label(console_frame, text=""); self.console_output_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        console_text_frame = ttk.Frame(console_frame, borderwidth=1, relief="sunken"); console_text_frame.grid(row=1, column=0, sticky="nsew"); console_text_frame.rowconfigure(0, weight=1); console_text_frame.columnconfigure(0, weight=1)
        self.console_output = ScrolledText(console_text_frame, wrap=tk.WORD, width=80, height=10, background="#f0f0f0", foreground="#333", font=("Consolas", 10), borderwidth=0, relief="flat"); self.console_output.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)


        # --- Create and Add Recorder Tab ---
        self.recorder_tab = RecorderTab(self.main_notebook, self.update_transcription_path)
        # Add recorder tab (index 1)
        self.main_notebook.add(self.recorder_tab.frame, text="") # Text set later


        # --- NEW: Create and Add LLM Tab ---
        self.llm_tab = LLMTab(self.main_notebook, self, self.llm_processor) # Pass GUI instance and processor
        # Add LLM tab (index 2)
        self.main_notebook.add(self.llm_tab.frame, text="") # Text set later


        # --- Status Bar ---
        self.status_frame = ttk.Frame(self.root, style="Status.TFrame", borderwidth=1, relief='groove')
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)


    def update_ui_text(self):
        """Updates all UI elements with text based on the current language."""
        if not hasattr(self, 'main_notebook') or not self.main_notebook.winfo_exists(): return

        self.root.title(self.translate("window_title"))
        self.app_title_label.config(text=self.translate("app_title"))
        self.app_subtitle_label.config(text=self.translate("app_subtitle"))
        self.lang_select_label.config(text=self.translate("language_select_label"))

        # --- Update Main Notebook Tab Titles ---
        try:
            tab_count = len(self.main_notebook.tabs())
            if tab_count > 0: self.main_notebook.tab(0, text=self.translate("tab_transcription"))
            if tab_count > 1: self.main_notebook.tab(1, text=self.translate("tab_recorder"))
            if tab_count > 2: self.main_notebook.tab(2, text=self.translate("tab_llm")) # NEW: LLM Tab Title
        except tk.TclError as e: print(f"Error updating main notebook tabs: {e}")

        # --- Update Transcription Tab Widgets ---
        if hasattr(self, 'file_frame') and self.file_frame.winfo_exists():
            self.file_frame.config(text=self.translate("select_audio_frame"))
            self.wav_file_label.config(text=self.translate("wav_file_label"))
            self.browse_button.config(text=self.translate("browse_button"))
            # ... (rest of transcription tab widgets) ...
            self.options_frame.config(text=self.translate("options_frame"))
            self.model_label.config(text=self.translate("model_label"))
            self.transcription_language_label.config(text=self.translate("language_label"))
            self.acceleration_label.config(text=self.translate("acceleration_label"))
            self.gpu_check.config(text=self.translate("use_gpu_checkbox"))
            self.update_model_description()
            self.start_button.config(text=self.translate("start_button"))
            self.stop_button.config(text=self.translate("stop_button"))
            self.copy_button.config(text=self.translate("copy_button"))
            self.save_button.config(text=self.translate("save_button"))

        if hasattr(self, 'results_notebook') and self.results_notebook.winfo_exists():
             try: # Update results notebook tabs (nested)
                 if len(self.results_notebook.tabs()) >= 2:
                    self.results_notebook.tab(0, text=self.translate("tab_transcription"))
                    self.results_notebook.tab(1, text=self.translate("tab_console"))
             except tk.TclError as e: print(f"Error updating results notebook tabs: {e}")
        if hasattr(self, 'transcription_result_label') and self.transcription_result_label.winfo_exists():
            self.transcription_result_label.config(text=self.translate("transcription_result_label"))
        if hasattr(self, 'console_output_label') and self.console_output_label.winfo_exists():
            self.console_output_label.config(text=self.translate("console_output_label"))

        # --- NEW: Update LLM Tab Widgets ---
        if hasattr(self, 'llm_tab') and self.llm_tab.frame.winfo_exists():
            self.llm_tab.update_ui_text() # Delegate to the tab's own update method

        # Update status bar text only if it's currently "Ready"
        current_status = self.status_var.get()
        if current_status == self.translate("status_ready"): # Avoid overriding specific statuses
             self.status_var.set(self.translate("status_ready"))


    # --- NEW Method for LLM Tab ---
    def get_transcription_text(self):
        """Returns the current text from the transcription result widget."""
        if hasattr(self, 'result_text') and self.result_text.winfo_exists():
            return self.result_text.get("1.0", tk.END).strip()
        return ""
    # --- END NEW Method ---

    # --- Other methods (on_language_select, change_language, etc.) ---
    # ... (Keep all other existing methods like on_language_select, change_language, select_file, ...)
    # ... (update_transcription_path, start_transcription, stop_transcription, copy_to_clipboard, save_transcription, ...)
    # ... (console_output_insert, console_output_delete_all, result_text_set, result_text_clear, ...)
    # ... (update_progress_state, finalize_ui_state) the same ...
    def on_language_select(self, event=None):
        selected_display_name = self.language_selector.get()
        # Map display name back to code if needed, or just use display name if keys match
        new_lang_code = selected_display_name # Assuming keys in translations dict match display names
        self.current_language.set(new_lang_code)

    def change_language(self, *args):
        self.update_ui_text()

    def update_model_description(self, event=None):
        if hasattr(self, 'model_combobox'):
             selected_model = self.model_combobox.get()
             desc_key = self.model_descriptions.get(selected_model, "model_desc_large")
             self.model_desc_var.set(self.translate(desc_key))

    def show_gpu_tooltip(self, event):
        if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip and self.gpu_tooltip.winfo_exists(): self.gpu_tooltip.destroy()
        self.gpu_tooltip = tk.Toplevel(self.root); self.gpu_tooltip.wm_overrideredirect(True)
        x, y = event.x_root + 15, event.y_root + 10; self.gpu_tooltip.wm_geometry(f"+{x}+{y}")
        msg = self.translate("gpu_tooltip_mac") if self.system_type == "mac" else self.translate("gpu_tooltip_windows")
        label = ttk.Label(self.gpu_tooltip, text=msg, justify=tk.LEFT, background="#ffffe0", relief="solid", borderwidth=1, padding=5, font=("Segoe UI", 9)); label.pack(ipadx=1, ipady=1)
        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id: self.root.after_cancel(self._tooltip_after_id)
        self._tooltip_after_id = self.root.after(5000, self._destroy_tooltip)
        if hasattr(self, 'gpu_check'): self.gpu_check.unbind("<Leave>"); self.gpu_check.bind("<Leave>", self._on_leave_tooltip)

    def _destroy_tooltip(self):
        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id:
            try: self.root.after_cancel(self._tooltip_after_id)
            except ValueError: pass
            self._tooltip_after_id = None
        if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip and self.gpu_tooltip.winfo_exists(): self.gpu_tooltip.destroy()
        self.gpu_tooltip = None
        if hasattr(self, 'gpu_check') and self.gpu_check.winfo_exists():
            try: self.gpu_check.unbind("<Leave>")
            except tk.TclError: pass

    def _on_leave_tooltip(self, event=None): self._destroy_tooltip()

    def get_language_code(self, language_name):
        language_map = { "italiano": "italian", "inglese": "english", "francese": "french", "tedesco": "german", "spagnolo": "spanish", "giapponese": "japanese", "cinese": "chinese" }
        return language_map.get(language_name.lower(), "italian")

    def select_file(self):
        initial_dir = os.path.dirname(self.file_path.get()) if self.file_path.get() else "/"
        file = filedialog.askopenfilename( title=self.translate("select_audio_frame"), initialdir=initial_dir, filetypes=[("WAV files", "*.wav"), ("Audio files", "*.mp3 *.flac *.ogg"), ("All files", "*.*")] ) # Allow more types
        if file:
            self.file_path.set(file)
            # Try getting info using transcriber's helper which uses wave
            if file.lower().endswith(".wav"):
                file_info = self.transcriber.get_audio_info(file)
                if file_info:
                    duration, channels, rate = file_info
                    duration_str = format_duration(duration)
                    filename = os.path.basename(file)
                    info_msg = self.translate("selected_file_info").format( filename=filename, duration=duration_str, channels=channels, rate=rate )
                    self.console_output_insert(info_msg)
                else: self.console_output_insert(f"Could not read WAV info for: {os.path.basename(file)}\n")
            else:
                # For non-wav, just show filename. Duration/info reading needs other libraries (like soundfile, used in audio_handler)
                self.console_output_insert(f"Selected non-WAV file: {os.path.basename(file)}\n")


    def update_transcription_path(self, file_path):
         if file_path and os.path.exists(file_path):
             self.file_path.set(file_path); print(f"Transcription file path set to: {file_path}")
             if hasattr(self, 'main_notebook'):
                  try: # Select transcription tab (usually index 0)
                      self.main_notebook.select(0)
                  except tk.TclError: print("Could not switch to transcription tab (TclError).")
                  except Exception as e: print(f"Could not switch to transcription tab (Error: {e}).")
         else: print(f"Invalid file path received from recorder: {file_path}")

    def start_transcription(self):
        input_file = self.file_path.get(); model_type = self.model_var.get()
        language = self.get_language_code(self.transcription_language_var.get()); use_gpu = self.use_gpu_var.get()
        if not input_file or not os.path.isfile(input_file): messagebox.showerror(self.translate("error_title"), self.translate("error_no_file")); return
        self.start_button.config(state=tk.DISABLED); self.stop_button.config(state=tk.NORMAL)
        self.console_output_delete_all(); self.result_text_clear()
        self.transcriber.start_transcription_async(input_file, model_type, language, use_gpu, self.system_type)

    def stop_transcription(self):
        if hasattr(self.transcriber, 'request_stop'):
             self.transcriber.request_stop(); self.console_output_insert(self.translate("stop_requested_info"))
             self.status_var.set(self.translate("status_stopping")); self.current_task.set(self.translate("progress_label_interrupted"))
             if hasattr(self, 'stop_button') and self.stop_button.winfo_exists(): self.stop_button.config(state=tk.DISABLED)

    def copy_to_clipboard(self):
        try:
            text_to_copy = self.result_text.get("1.0", tk.END).strip()
            if not text_to_copy: messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save")); return
            self.root.clipboard_clear(); self.root.clipboard_append(text_to_copy); self.root.update()
            messagebox.showinfo(self.translate("copied_title"), self.translate("copied_message"))
        except tk.TclError: messagebox.showerror(self.translate("error_title"), "Error copying text.")

    def save_transcription(self):
        text = self.result_text.get("1.0", tk.END).strip()
        if not text: messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save")); return
        original_filename = os.path.basename(self.file_path.get())
        suggested_filename = os.path.splitext(original_filename)[0] + "_transcription.txt" if original_filename else self.translate('tab_transcription').lower() + ".txt"
        file = filedialog.asksaveasfilename( title=self.translate("save_button"), defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], initialfile=suggested_filename, initialdir=os.path.dirname(self.file_path.get()) if self.file_path.get() else "/" )
        if file:
            try:
                with open(file, "w", encoding="utf-8") as f: f.write(text)
                messagebox.showinfo(self.translate("saved_title"), self.translate("saved_message").format(file=file))
            except Exception as e: messagebox.showerror(self.translate("error_title"), self.translate("error_saving").format(error=str(e)))

    def console_output_insert(self, text):
        try:
             if hasattr(self, 'console_output') and self.console_output.winfo_exists():
                 self.console_output.after_idle(lambda t=text: (self.console_output.insert(tk.END, t), self.console_output.see(tk.END)))
             else: print(f"GUI Console Log: {text.strip()}")
        except Exception as e: print(f"Error inserting to console: {e}\nMessage: {text.strip()}")

    def console_output_delete_all(self):
        try:
            if hasattr(self, 'console_output') and self.console_output.winfo_exists(): self.console_output.after_idle(lambda: self.console_output.delete(1.0, tk.END))
        except tk.TclError: pass

    def result_text_set(self, text):
        try:
            if hasattr(self, 'result_text') and self.result_text.winfo_exists():
                 self.result_text.after_idle(lambda t=text: (self.result_text.delete(1.0, tk.END), self.result_text.insert(tk.END, t), self.result_text.see(tk.END)))
        except tk.TclError: pass

    def result_text_clear(self):
         try:
            if hasattr(self, 'result_text') and self.result_text.winfo_exists(): self.result_text.after_idle(lambda: self.result_text.delete(1.0, tk.END))
         except tk.TclError: pass

    def update_progress_state(self, task_key=None, status_key=None, progress_mode="start"):
        task_text = self.translate(task_key) if task_key else self.current_task.get()
        status_text = self.translate(status_key) if status_key else self.status_var.get()
        def _update():
            try:
                if not self.root.winfo_exists(): return
                self.current_task.set(task_text); self.status_var.set(status_text)
                if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                    if progress_mode == "start" or progress_mode == "indeterminate": self.progress_bar.config(mode="indeterminate"); self.progress_bar.start(10)
                    elif progress_mode == "stop": self.progress_bar.stop(); self.progress_bar.config(mode="determinate"); self.progress_var.set(0)
                    elif progress_mode == "determinate": self.progress_bar.config(mode="determinate")
            except tk.TclError: print(f"Status Update Failed (TclError): Task={task_text}, Status={status_text}")
            except Exception as e: print(f"Status Update Failed (Other Error): {e} - Task={task_text}, Status={status_text}")
        self.root.after_idle(_update)

    def finalize_ui_state(self, success=True, interrupted=False):
        def _finalize():
            try:
                if not self.root.winfo_exists(): return
                if hasattr(self, 'start_button') and self.start_button.winfo_exists(): self.start_button.config(state=tk.NORMAL)
                if hasattr(self, 'stop_button') and self.stop_button.winfo_exists(): self.stop_button.config(state=tk.DISABLED)
                if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists(): self.progress_bar.stop(); self.progress_var.set(0)
                if interrupted: final_status_key, final_task_key = "status_interrupted", "progress_label_interrupted"
                elif success: final_status_key, final_task_key = "status_completed", "progress_label_completed"
                else: final_status_key, final_task_key = "status_error", "progress_label_error"
                self.status_var.set(self.translate(final_status_key)); self.current_task.set(self.translate(final_task_key))
            except tk.TclError: print("Failed to finalize UI state (TclError).")
            except Exception as e: print(f"Failed to finalize UI state (Other Error): {e}")
        self.root.after_idle(_finalize)

    def on_closing(self):
        """Handle application closing, including tab cleanup."""
        if messagebox.askokcancel(self.translate("ask_close_title"), self.translate("ask_close_message")):
            print("Exiting application...")
            # Cleanup Recorder Tab
            if hasattr(self, 'recorder_tab') and self.recorder_tab:
                 try: self.recorder_tab.on_close()
                 except Exception as e: print(f"Error during recorder tab cleanup: {e}")
            # Cleanup LLM Tab
            if hasattr(self, 'llm_tab') and self.llm_tab: # NEW
                 try: self.llm_tab.on_close()
                 except Exception as e: print(f"Error during LLM tab cleanup: {e}")
            # Stop Transcriber (if running)
            if hasattr(self.transcriber, 'request_stop'):
                 self.transcriber.request_stop() # Request stop if transcription is running

            self.root.destroy()

# --- END OF MODIFIED FILE gui.py ---