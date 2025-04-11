# --- START OF MODIFIED FILE gui.py ---

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import io
import os
import sys
from tkinter.scrolledtext import ScrolledText # Keep for ConsoleOutput type hint maybe
from transcriber import AudioTranscriber
from utils import format_duration
from recorder_tab import RecorderTab
from llm_tab import LLMTab
from llm_processor import LLMProcessor
# --- NEW IMPORTS ---
from header_frame import HeaderFrame
from transcription_tab_ui import TranscriptionTabUI
from status_bar import StatusBar
# --- END NEW IMPORTS ---
# import json # Keep if needed elsewhere

class ConsoleOutput(io.StringIO):
    # ... (ConsoleOutput class remains the same) ...
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, message):
        try:
            if self.text_widget and self.text_widget.winfo_exists(): # Check widget exists
                self.text_widget.after_idle(self._insert_text, message)
            else:
                print(f"Console Write Error (widget gone?): {message.strip()}")
        except tk.TclError:
            print(f"Console Write Error (TclError): {message.strip()}")
        except Exception as e:
             print(f"Console Write Error (General Exception): {e} - Message: {message.strip()}")
        super().write(message) # Write to buffer anyway

    def _insert_text(self, message):
        try:
            if self.text_widget and self.text_widget.winfo_exists(): # Check widget exists
                self.text_widget.insert(tk.END, message)
                self.text_widget.see(tk.END)
        except tk.TclError:
             print(f"Console Insert Error (TclError): {message.strip()}")
        except Exception as e:
             print(f"Console Insert Error (General Exception): {e} - Message: {message.strip()}")


class ModernTranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.transcriber = AudioTranscriber(self)
        self.llm_processor = LLMProcessor()
        self.system_type = "mac" if sys.platform == "darwin" else "windows"

        self.setup_translations()
        self.current_language = tk.StringVar(value="English")

        # --- Core Application State Variables ---
        self.status_var = tk.StringVar(value=self.translate("status_ready"))
        self.current_task = tk.StringVar(value="")
        self.file_path = tk.StringVar()
        self.model_var = tk.StringVar(value="large")
        self.transcription_language_var = tk.StringVar(value="italiano")
        self.progress_var = tk.DoubleVar(value=0)
        self.use_gpu_var = tk.BooleanVar(value=False)
        self.model_desc_var = tk.StringVar(value=self.translate("model_desc_large"))
        # --- End Core Variables ---

        self.setup_ui_styles() # Setup styles before creating widgets that use them
        self.create_widgets() # Create UI by instantiating components

        # Set up language change trace *after* widgets using the variable are created
        self.current_language.trace_add("write", self.change_language)

        # Initial UI text update after everything is created
        self.update_ui_text()

        # Redirect stdout - ensure console widget is available via the transcription tab instance
        if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'console_output') and self.transcription_tab.console_output.winfo_exists():
            sys.stdout = ConsoleOutput(self.transcription_tab.console_output)
            print(self.translate("welcome_message"))
        else:
            print("WARNING: Console output widget not found/ready for stdout redirection.")

        # Handle application closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)


    def setup_translations(self):
        # ... (Keep the full translations dictionary as before) ...
        llm_translations_it = { "tab_llm": "Elaborazione LLM", "llm_input_label": "Testo di Input:", "llm_load_transcription": "⎗ Carica da Trascrizione", "llm_load_file": "📂 Carica File...", "llm_paste": "📋 Incolla", "llm_config_frame": "Configurazione LLM", "llm_provider_label": "Provider API:", "llm_api_key_label": "Chiave API:", "llm_model_label": "Modello:", "llm_instructions_label": "Istruzioni (Prompt di Sistema):", "llm_instructions_placeholder": "Es: Riassumi il testo seguente in punti chiave.", "llm_process_button": "✨ Elabora con LLM", "llm_output_label": "Risultato LLM:", "llm_copy_output": "📋 Copia Output", "llm_save_output": "💾 Salva Output...", "llm_status_loaded_transcription": "Caricato dalla trascrizione.", "llm_status_loaded_file": "File caricato: {filename}", "llm_status_pasted": "Testo incollato dagli appunti.", "llm_status_processing": "Elaborazione LLM in corso...", "llm_status_completed": "Elaborazione LLM completata.", "llm_status_error": "Errore durante l'elaborazione LLM.", "llm_status_ready": "Pronto per l'elaborazione LLM.", "llm_select_file_title": "Seleziona File di Testo", "llm_save_output_title": "Salva Output LLM", "llm_warn_no_transcription": "Nessun testo di trascrizione disponibile da caricare.", "llm_error_loading_transcription": "Errore nel caricare il testo della trascrizione", "llm_error_reading_file": "Errore nella lettura del file: {error}", "llm_warn_clipboard_empty": "Nessun testo trovato negli appunti.", "llm_error_pasting": "Errore durante l'operazione Incolla", "llm_error_no_provider": "Seleziona un provider API LLM!", "llm_error_no_model": "Seleziona un modello LLM!", "llm_error_no_input": "Inserisci del testo nell'area di Input!", "llm_warn_no_api_key": "La chiave API è vuota. Assicurati che sia impostata tramite variabili d'ambiente o inseriscila qui. Continuare?", "llm_error_unknown": "Si è verificato un errore sconosciuto durante l'elaborazione.", "llm_warn_no_output_to_copy": "Nessun output da copiare.", "llm_warn_no_output_to_save": "Nessun output da salvare.", "llm_info_copied_output": "Output LLM copiato negli appunti!", "llm_info_saved_output": "Output LLM salvato in {file}", "llm_error_copying": "Errore durante la copia dell'output LLM.", "llm_error_saving_output": "Errore durante il salvataggio dell'output LLM: {error}" }
        llm_translations_en = { "tab_llm": "LLM Processing", "llm_input_label": "Input Text:", "llm_load_transcription": "⎗ Load from Transcription", "llm_load_file": "📂 Load File...", "llm_paste": "📋 Paste", "llm_config_frame": "LLM Configuration", "llm_provider_label": "API Provider:", "llm_api_key_label": "API Key:", "llm_model_label": "Model:", "llm_instructions_label": "Instructions (System Prompt):", "llm_instructions_placeholder": "E.g.: Summarize the following text into key bullet points.", "llm_process_button": "✨ Process with LLM", "llm_output_label": "LLM Result:", "llm_copy_output": "📋 Copy Output", "llm_save_output": "💾 Save Output...", "llm_status_loaded_transcription": "Loaded from transcription.", "llm_status_loaded_file": "Loaded file: {filename}", "llm_status_pasted": "Pasted text from clipboard.", "llm_status_processing": "LLM processing...", "llm_status_completed": "LLM processing completed.", "llm_status_error": "Error during LLM processing.", "llm_status_ready": "Ready for LLM processing.", "llm_select_file_title": "Select Text File", "llm_save_output_title": "Save LLM Output", "llm_warn_no_transcription": "No transcription text available to load.", "llm_error_loading_transcription": "Error loading transcription text", "llm_error_reading_file": "Error reading file: {error}", "llm_warn_clipboard_empty": "No text found on clipboard.", "llm_error_pasting": "Error during paste operation", "llm_error_no_provider": "Please select an LLM API provider!", "llm_error_no_model": "Please select an LLM model!", "llm_error_no_input": "Please enter text in the Input area!", "llm_warn_no_api_key": "API Key is empty. Ensure it's set via environment variables or enter it here. Continue?", "llm_error_unknown": "An unknown error occurred during processing.", "llm_warn_no_output_to_copy": "No output to copy.", "llm_warn_no_output_to_save": "No output to save.", "llm_info_copied_output": "LLM output copied to clipboard!", "llm_info_saved_output": "LLM output saved to {file}", "llm_error_copying": "Error copying LLM output.", "llm_error_saving_output": "Error saving LLM output: {error}" }
        llm_translations_fr = { "tab_llm": "Traitement LLM", "llm_input_label": "Texte d'Entrée :", "llm_load_transcription": "⎗ Charger depuis Transcription", "llm_load_file": "📂 Charger Fichier...", "llm_paste": "📋 Coller", "llm_config_frame": "Configuration LLM", "llm_provider_label": "Fournisseur API :", "llm_api_key_label": "Clé API :", "llm_model_label": "Modèle :", "llm_instructions_label": "Instructions (Prompt Système) :", "llm_instructions_placeholder": "Ex : Résumez le texte suivant en points clés.", "llm_process_button": "✨ Traiter avec LLM", "llm_output_label": "Résultat LLM :", "llm_copy_output": "📋 Copier Sortie", "llm_save_output": "💾 Enregistrer Sortie...", "llm_status_loaded_transcription": "Chargé depuis la transcription.", "llm_status_loaded_file": "Fichier chargé : {filename}", "llm_status_pasted": "Texte collé depuis le presse-papiers.", "llm_status_processing": "Traitement LLM en cours...", "llm_status_completed": "Traitement LLM terminé.", "llm_status_error": "Erreur pendant le traitement LLM.", "llm_status_ready": "Prêt pour le traitement LLM.", "llm_select_file_title": "Sélectionner un Fichier Texte", "llm_save_output_title": "Enregistrer la Sortie LLM", "llm_warn_no_transcription": "Aucun texte de transcription disponible à charger.", "llm_error_loading_transcription": "Erreur lors du chargement du texte de transcription", "llm_error_reading_file": "Erreur de lecture du fichier : {error}", "llm_warn_clipboard_empty": "Aucun texte trouvé dans le presse-papiers.", "llm_error_pasting": "Erreur lors de l'opération Coller", "llm_error_no_provider": "Veuillez sélectionner un fournisseur d'API LLM !", "llm_error_no_model": "Veuillez sélectionner un modèle LLM !", "llm_error_no_input": "Veuillez entrer du texte dans la zone d'Entrée !", "llm_warn_no_api_key": "La clé API est vide. Assurez-vous qu'elle est définie via les variables d'environnement ou saisissez-la ici. Continuer ?", "llm_error_unknown": "Une erreur inconnue s'est produite lors du traitement.", "llm_warn_no_output_to_copy": "Aucune sortie à copier.", "llm_warn_no_output_to_save": "Aucune sortie à enregistrer.", "llm_info_copied_output": "Sortie LLM copiée dans le presse-papiers !", "llm_info_saved_output": "Sortie LLM enregistrée dans {file}", "llm_error_copying": "Erreur lors de la copie de la sortie LLM.", "llm_error_saving_output": "Erreur lors de l'enregistrement de la sortie LLM : {error}" }
        llm_translations_zh = { "tab_llm": "LLM 处理", "llm_input_label": "输入文本:", "llm_load_transcription": "⎗ 从转录加载", "llm_load_file": "📂 加载文件...", "llm_paste": "📋 粘贴", "llm_config_frame": "LLM 配置", "llm_provider_label": "API 提供商:", "llm_api_key_label": "API 密钥:", "llm_model_label": "模型:", "llm_instructions_label": "说明 (系统提示):", "llm_instructions_placeholder": "例如：将以下文本总结为关键要点。", "llm_process_button": "✨ 使用 LLM 处理", "llm_output_label": "LLM 结果:", "llm_copy_output": "📋 复制输出", "llm_save_output": "💾 保存输出...", "llm_status_loaded_transcription": "已从转录加载。", "llm_status_loaded_file": "已加载文件: {filename}", "llm_status_pasted": "已从剪贴板粘贴文本。", "llm_status_processing": "LLM 处理中...", "llm_status_completed": "LLM 处理完成。", "llm_status_error": "LLM 处理过程中出错。", "llm_status_ready": "准备进行 LLM 处理。", "llm_select_file_title": "选择文本文件", "llm_save_output_title": "保存 LLM 输出", "llm_warn_no_transcription": "没有可加载的转录文本。", "llm_error_loading_transcription": "加载转录文本时出错", "llm_error_reading_file": "读取文件时出错: {error}", "llm_warn_clipboard_empty": "剪贴板中未找到文本。", "llm_error_pasting": "粘贴操作期间出错", "llm_error_no_provider": "请选择一个 LLM API 提供商！", "llm_error_no_model": "请选择一个 LLM 模型！", "llm_error_no_input": "请在输入区域输入文本！", "llm_warn_no_api_key": "API 密钥为空。请确保通过环境变量设置或在此处输入。继续？", "llm_error_unknown": "处理过程中发生未知错误。", "llm_warn_no_output_to_copy": "没有要复制的输出。", "llm_warn_no_output_to_save": "没有要保存的输出。", "llm_info_copied_output": "LLM 输出已复制到剪贴板！", "llm_info_saved_output": "LLM 输出已保存到 {file}", "llm_error_copying": "复制 LLM 输出时出错。", "llm_error_saving_output": "保存 LLM 输出时出错: {error}" }

        self.translations = {
            "Italiano": {
                "window_title": "AudioScript - Trascrizione & Registrazione & LLM",
                "app_subtitle": "Trascrizione, Registrazione e Elaborazione LLM",
                 # ... other Italian translations ...
                "select_audio_frame": "Seleziona File Audio (WAV/MP3)", # Updated example
                "status_ready": "Pronto",
                "status_stopping": "Interruzione...",
                "status_loading_model": "Caricamento modello...",
                "status_transcribing": "Trascrizione...",
                "status_completed": "Completato",
                "status_error": "Errore",
                "status_interrupted": "Interrotto",
                "error_title": "Errore",
                "error_no_file": "Seleziona un file audio valido!",
                "error_saving": "Errore salvataggio: {error}",
                "error_reading_info": "Errore lettura info file: {error}",
                # ... rest of Italian ...
                **llm_translations_it
            },
            "English": {
                 "window_title": "AudioScript - Transcription & Recording & LLM",
                 "app_subtitle": "Transcription, Recording & LLM Processing",
                 # ... other English translations ...
                 "select_audio_frame": "Select Audio File (WAV/MP3)", # Updated example
                 "status_ready": "Ready",
                 "status_stopping": "Stopping...",
                 "status_loading_model": "Loading model...",
                 "status_transcribing": "Transcribing...",
                 "status_completed": "Completed",
                 "status_error": "Error",
                 "status_interrupted": "Interrupted",
                 "error_title": "Error",
                 "error_no_file": "Select a valid audio file!",
                 "error_saving": "Error saving: {error}",
                 "error_reading_info": "Error reading file info: {error}",
                 # ... rest of English ...
                **llm_translations_en
            },
             "Francais": {
                 "window_title": "AudioScript - Transcription & Enregistrement & LLM",
                 "app_subtitle": "Transcription, Enregistrement et Traitement LLM",
                 # ... other French translations ...
                 "select_audio_frame": "Sélectionner Fichier Audio (WAV/MP3)", # Updated example
                 "status_ready": "Prêt",
                 "status_stopping": "Arrêt...",
                 "status_loading_model": "Chargement modèle...",
                 "status_transcribing": "Transcription...",
                 "status_completed": "Terminé",
                 "status_error": "Erreur",
                 "status_interrupted": "Interrompu",
                 "error_title": "Erreur",
                 "error_no_file": "Sélectionnez un fichier audio valide !",
                 "error_saving": "Erreur sauvegarde : {error}",
                 "error_reading_info": "Erreur lecture info fichier : {error}",
                 # ... rest of French ...
                **llm_translations_fr
             },
             "中文": {
                 "window_title": "AudioScript - 转录 & 录制 & LLM",
                 "app_subtitle": "转录、录制和 LLM 处理",
                 # ... other Chinese translations ...
                 "select_audio_frame": "选择音频文件 (WAV/MP3)", # Updated example
                 "status_ready": "准备就绪",
                 "status_stopping": "正在停止...",
                 "status_loading_model": "正在加载模型...",
                 "status_transcribing": "正在转录...",
                 "status_completed": "完成",
                 "status_error": "错误",
                 "status_interrupted": "已中断",
                 "error_title": "错误",
                 "error_no_file": "请选择有效的音频文件！",
                 "error_saving": "保存出错：{error}",
                 "error_reading_info": "读取文件信息出错：{error}",
                 # ... rest of Chinese ...
                **llm_translations_zh
             }
        }
        self.model_descriptions = {
            "tiny": "model_desc_tiny", "base": "model_desc_base", "small": "model_desc_small",
            "medium": "model_desc_medium", "large": "model_desc_large",
        }

    def translate(self, key):
        lang_code = self.current_language.get()
        return self.translations.get(lang_code, self.translations['English']).get(key, f"<{key}>")

    def setup_ui_styles(self):
        # ... (setup_ui_styles method remains the same) ...
        self.style = ttk.Style()
        try: self.style.theme_use('clam')
        except tk.TclError:
             available_themes = self.style.theme_names(); print(f"Theme 'clam' not found. Available: {available_themes}")
             if available_themes: self.style.theme_use(available_themes[0])
        self.primary_color = "#3498db"; self.secondary_color = "#2980b9"; self.bg_color = "#f5f5f5"
        self.text_color = "#2c3e50"; self.success_color = "#2ecc71"; self.warning_color = "#e74c3c"
        self.root.configure(bg=self.bg_color)
        default_font = ("Segoe UI", 10); bold_font = ("Segoe UI", 10, "bold")
        heading_font = ("Segoe UI", 14, "bold"); console_font = ("Consolas", 10)
        self.style.configure("Card.TFrame", background=self.bg_color, relief="raised", borderwidth=1)
        self.style.configure("Primary.TButton", background=self.primary_color, foreground="white", padding=10, font=bold_font)
        self.style.map("Primary.TButton", background=[("active", self.secondary_color), ("disabled", "#bdc3c7")])
        self.style.configure("Action.TButton", background=self.secondary_color, foreground="white", padding=8, font=("Segoe UI", 9))
        self.style.map("Action.TButton", background=[("active", self.primary_color), ("disabled", "#bdc3c7")])
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

        # --- Instantiate UI Components ---
        # Header (packs itself at the top)
        self.header = HeaderFrame(self.root, self)

        # Main Notebook (packed below header)
        self.main_notebook = ttk.Notebook(self.root, padding=(20, 10, 20, 10))
        self.main_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Transcription Tab UI (gets added to notebook)
        self.transcription_tab = TranscriptionTabUI(self.main_notebook, self)
        self.main_notebook.add(self.transcription_tab.frame, text="") # Text set later

        # Recorder Tab (gets added to notebook)
        self.recorder_tab = RecorderTab(self.main_notebook, self.update_transcription_path)
        self.main_notebook.add(self.recorder_tab.frame, text="") # Text set later

        # LLM Tab (gets added to notebook)
        self.llm_tab = LLMTab(self.main_notebook, self, self.llm_processor)
        self.main_notebook.add(self.llm_tab.frame, text="") # Text set later

        # Status Bar (packs itself at the bottom)
        self.status_bar = StatusBar(self.root, self)

        # --- Store direct references if needed frequently (optional) ---
        # Example: self.result_text = self.transcription_tab.result_text
        # Generally, accessing via self.transcription_tab.result_text is fine

    def update_ui_text(self):
        """Updates UI text by delegating to components."""
        if not hasattr(self, 'main_notebook') or not self.main_notebook.winfo_exists(): return

        self.root.title(self.translate("window_title"))

        # Update Header
        if hasattr(self, 'header'): self.header.update_ui_text()

        # Update Main Notebook Tab Titles
        try:
            tabs = self.main_notebook.tabs()
            if len(tabs) > 0: self.main_notebook.tab(0, text=self.translate("tab_transcription"))
            if len(tabs) > 1: self.main_notebook.tab(1, text=self.translate("tab_recorder"))
            if len(tabs) > 2: self.main_notebook.tab(2, text=self.translate("tab_llm"))
        except tk.TclError as e: print(f"Error updating main notebook tabs: {e}")

        # Update Transcription Tab Content
        if hasattr(self, 'transcription_tab'): self.transcription_tab.update_ui_text()

        # Update Recorder Tab Content (if it has an update method)
        if hasattr(self, 'recorder_tab') and hasattr(self.recorder_tab, 'update_ui_text'):
             self.recorder_tab.update_ui_text() # Assuming RecorderTab might get one

        # Update LLM Tab Content
        if hasattr(self, 'llm_tab'): self.llm_tab.update_ui_text()

        # Update Status Bar (if needed - currently uses textvariable)
        # if hasattr(self, 'status_bar'): self.status_bar.update_ui_text()

        # Update main status bar if ready
        current_status = self.status_var.get()
        is_ready = False
        for code in self.translations:
             if current_status == self.translations[code].get('status_ready'):
                 is_ready = True; break
        if is_ready: self.status_var.set(self.translate("status_ready"))


    # --- Methods Accessing Widgets (Now via component instances) ---

    def get_transcription_text(self):
        """Returns the current text from the transcription result widget."""
        if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'result_text') and self.transcription_tab.result_text.winfo_exists():
            return self.transcription_tab.result_text.get("1.0", tk.END).strip()
        return ""

    def console_output_insert(self, text):
        try:
             # Access console via transcription_tab instance
             if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'console_output') and self.transcription_tab.console_output.winfo_exists():
                 # If stdout is redirected, use that, otherwise insert directly
                 if isinstance(sys.stdout, ConsoleOutput) and sys.stdout.text_widget == self.transcription_tab.console_output:
                      sys.stdout.write(text)
                 else:
                      # Fallback: Direct insert via after_idle
                      console_widget = self.transcription_tab.console_output
                      console_widget.after_idle(lambda w=console_widget, t=text: (
                         w.insert(tk.END, t),
                         w.see(tk.END)
                      ))
             else:
                 print(f"GUI Console Log (Widget missing): {text.strip()}")
        except Exception as e:
             print(f"Error inserting to console: {e}\nMessage: {text.strip()}")

    def console_output_delete_all(self):
        try:
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'console_output') and self.transcription_tab.console_output.winfo_exists():
                console_widget = self.transcription_tab.console_output
                console_widget.after_idle(lambda w=console_widget: w.delete(1.0, tk.END))
        except tk.TclError:
             pass # Ignore if widget destroyed

    def result_text_set(self, text):
        try:
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'result_text') and self.transcription_tab.result_text.winfo_exists():
                 result_widget = self.transcription_tab.result_text
                 result_widget.after_idle(lambda w=result_widget, t=text: (
                     w.delete(1.0, tk.END),
                     w.insert(tk.END, t),
                     w.see(tk.END)
                 ))
        except tk.TclError:
             pass

    def result_text_clear(self):
         try:
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'result_text') and self.transcription_tab.result_text.winfo_exists():
                 result_widget = self.transcription_tab.result_text
                 result_widget.after_idle(lambda w=result_widget: w.delete(1.0, tk.END))
         except tk.TclError:
             pass

    # --- Core Logic Methods (Callbacks, Actions) ---
    # These methods now access UI elements via the component instances (e.g., self.transcription_tab.start_button)

    def on_language_select(self, event=None):
        # This method is bound to the combobox in HeaderFrame,
        # but the logic affects the whole app, so it stays here.
        # The textvariable is already updated. We just need to trigger the change handler.
        self.current_language.set(self.current_language.get()) # Force trace update if needed
        # self.change_language() # Or call directly if trace doesn't fire reliably

    def change_language(self, *args):
        """Handles language change for the entire application."""
        print(f"Language changed to: {self.current_language.get()}")
        self.update_ui_text() # Update all components
        # Update model description specifically, as it depends on language
        self.update_model_description()

    def update_model_description(self, event=None):
        # Accesses model_var (main app) and model_desc_var (main app)
        # The label widget itself is in transcription_tab
        if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'model_combobox'):
             selected_model = self.model_var.get()
             desc_key = self.model_descriptions.get(selected_model, "model_desc_large")
             self.model_desc_var.set(self.translate(desc_key)) # Update the shared variable

    def show_gpu_tooltip(self, event):
        # Tooltip logic remains here as it's generic UI behavior
        if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip and self.gpu_tooltip.winfo_exists(): self.gpu_tooltip.destroy()
        self.gpu_tooltip = tk.Toplevel(self.root); self.gpu_tooltip.wm_overrideredirect(True)
        x, y = event.x_root + 15, event.y_root + 10; self.gpu_tooltip.wm_geometry(f"+{x}+{y}")
        msg = self.translate("gpu_tooltip_mac") if self.system_type == "mac" else self.translate("gpu_tooltip_windows")
        label = ttk.Label(self.gpu_tooltip, text=msg, justify=tk.LEFT, background="#ffffe0", relief="solid", borderwidth=1, padding=5, font=("Segoe UI", 9)); label.pack(ipadx=1, ipady=1)
        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id: self.root.after_cancel(self._tooltip_after_id)
        self._tooltip_after_id = self.root.after(5000, self._destroy_tooltip)
        # The binding target is in transcription_tab
        if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'gpu_check'):
             self.transcription_tab.gpu_check.unbind("<Leave>"); # Remove previous binding first
             self.transcription_tab.gpu_check.bind("<Leave>", self._on_leave_tooltip) # Bind leave event

    def _destroy_tooltip(self):
        # Logic remains here
        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id:
            try: self.root.after_cancel(self._tooltip_after_id)
            except ValueError: pass
            self._tooltip_after_id = None
        if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip and self.gpu_tooltip.winfo_exists(): self.gpu_tooltip.destroy()
        self.gpu_tooltip = None
        # Unbind from the widget in transcription_tab
        if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'gpu_check') and self.transcription_tab.gpu_check.winfo_exists():
            try: self.transcription_tab.gpu_check.unbind("<Leave>")
            except tk.TclError: pass

    def _on_leave_tooltip(self, event=None):
        # Logic remains here
        self._destroy_tooltip()

    def get_language_code(self, language_name):
        # Logic remains here
        language_map = { "italiano": "italian", "inglese": "english", "francese": "french", "tedesco": "german", "spagnolo": "spanish", "giapponese": "japanese", "cinese": "chinese" }
        return language_map.get(language_name.lower(), "italian")

    def select_file(self):
        # File dialog logic remains here, updates main app's file_path var
        initial_dir = os.path.dirname(self.file_path.get()) if self.file_path.get() else "/"
        file = filedialog.askopenfilename( title=self.translate("select_audio_frame"), initialdir=initial_dir, filetypes=[("Audio files", "*.wav *.mp3 *.flac *.ogg"), ("All files", "*.*")] )
        if file:
            self.file_path.set(file) # Update the shared variable
            if file.lower().endswith(".wav"):
                file_info = self.transcriber.get_audio_info(file)
                if file_info:
                    duration, channels, rate = file_info; duration_str = format_duration(duration)
                    filename = os.path.basename(file)
                    info_msg = self.translate("selected_file_info").format( filename=filename, duration=duration_str, channels=channels, rate=rate )
                    self.console_output_insert(info_msg)
                else: self.console_output_insert(f"Could not read WAV info for: {os.path.basename(file)}\n")
            else:
                self.console_output_insert(f"Selected non-WAV file: {os.path.basename(file)}\n")

    def update_transcription_path(self, file_path):
         # Logic remains here, updates main app's file_path var and switches tab
         if file_path and os.path.exists(file_path):
             self.file_path.set(file_path); print(f"Transcription file path set to: {file_path}")
             if hasattr(self, 'main_notebook'):
                  try: self.main_notebook.select(0) # Select transcription tab (index 0)
                  except tk.TclError: print("Could not switch to transcription tab (TclError).")
                  except Exception as e: print(f"Could not switch to transcription tab (Error: {e}).")
         else: print(f"Invalid file path received from recorder: {file_path}")

    def start_transcription(self):
        # Gets vars from main app, calls transcriber, updates UI state via methods below
        input_file = self.file_path.get(); model_type = self.model_var.get()
        language = self.get_language_code(self.transcription_language_var.get()); use_gpu = self.use_gpu_var.get()
        if not input_file or not os.path.isfile(input_file): messagebox.showerror(self.translate("error_title"), self.translate("error_no_file")); return

        # --- Update UI State (Access widgets via transcription_tab) ---
        if hasattr(self, 'transcription_tab'):
             if hasattr(self.transcription_tab,'start_button') and self.transcription_tab.start_button.winfo_exists():
                 self.transcription_tab.start_button.config(state=tk.DISABLED)
             if hasattr(self.transcription_tab,'stop_button') and self.transcription_tab.stop_button.winfo_exists():
                 self.transcription_tab.stop_button.config(state=tk.NORMAL)
        # --- End UI State Update ---

        self.console_output_delete_all(); self.result_text_clear()
        self.transcriber.start_transcription_async(input_file, model_type, language, use_gpu, self.system_type)

    def stop_transcription(self):
        # Calls transcriber, updates UI state via methods below
        if hasattr(self.transcriber, 'request_stop'):
             self.transcriber.request_stop(); self.console_output_insert(self.translate("stop_requested_info"))
             self.status_var.set(self.translate("status_stopping")); self.current_task.set(self.translate("progress_label_interrupted"))
             # --- Update UI State ---
             if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab,'stop_button') and self.transcription_tab.stop_button.winfo_exists():
                 self.transcription_tab.stop_button.config(state=tk.DISABLED)
             # --- End UI State Update ---

    def copy_to_clipboard(self):
        # Gets text via self.get_transcription_text(), interacts with clipboard
        try:
            text_to_copy = self.get_transcription_text() # Use helper method
            if not text_to_copy: messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save")); return
            self.root.clipboard_clear(); self.root.clipboard_append(text_to_copy); self.root.update()
            messagebox.showinfo(self.translate("copied_title"), self.translate("copied_message"))
        except tk.TclError: messagebox.showerror(self.translate("error_title"), "Error copying text.")

    def save_transcription(self):
        # Gets text via self.get_transcription_text(), shows file dialog
        text = self.get_transcription_text() # Use helper method
        if not text: messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save")); return
        original_filename = os.path.basename(self.file_path.get())
        suggested_filename = os.path.splitext(original_filename)[0] + "_transcription.txt" if original_filename else self.translate('tab_transcription').lower() + ".txt"
        file = filedialog.asksaveasfilename( title=self.translate("save_button"), defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], initialfile=suggested_filename, initialdir=os.path.dirname(self.file_path.get()) if self.file_path.get() else "/" )
        if file:
            try:
                with open(file, "w", encoding="utf-8") as f: f.write(text)
                messagebox.showinfo(self.translate("saved_title"), self.translate("saved_message").format(file=file))
            except Exception as e: messagebox.showerror(self.translate("error_title"), self.translate("error_saving").format(error=str(e)))

    # --- UI State Management Methods ---
    # These methods update shared state vars and progress bar (which is in transcription_tab)

    def update_progress_state(self, task_key=None, status_key=None, progress_mode="start"):
        task_text = self.translate(task_key) if task_key else self.current_task.get()
        status_text = self.translate(status_key) if status_key else self.status_var.get()
        def _update():
            try:
                if not self.root.winfo_exists(): return
                self.current_task.set(task_text) # Update shared task variable
                self.status_var.set(status_text) # Update shared status variable
                # Access progress bar via transcription_tab instance
                if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'progress_bar') and self.transcription_tab.progress_bar.winfo_exists():
                    pb = self.transcription_tab.progress_bar
                    if progress_mode == "start" or progress_mode == "indeterminate": pb.config(mode="indeterminate"); pb.start(10)
                    elif progress_mode == "stop": pb.stop(); pb.config(mode="determinate"); self.progress_var.set(0)
                    elif progress_mode == "determinate": pb.config(mode="determinate") # Keep mode determinate if specified
            except tk.TclError: print(f"Status Update Failed (TclError): Task={task_text}, Status={status_text}")
            except Exception as e: print(f"Status Update Failed (Other Error): {e} - Task={task_text}, Status={status_text}")
        self.root.after_idle(_update)

    def finalize_ui_state(self, success=True, interrupted=False):
        def _finalize():
            try:
                if not self.root.winfo_exists(): return
                # Access buttons and progress bar via transcription_tab instance
                if hasattr(self, 'transcription_tab'):
                     if hasattr(self.transcription_tab,'start_button') and self.transcription_tab.start_button.winfo_exists():
                         self.transcription_tab.start_button.config(state=tk.NORMAL)
                     if hasattr(self.transcription_tab,'stop_button') and self.transcription_tab.stop_button.winfo_exists():
                         self.transcription_tab.stop_button.config(state=tk.DISABLED)
                     if hasattr(self.transcription_tab, 'progress_bar') and self.transcription_tab.progress_bar.winfo_exists():
                         self.transcription_tab.progress_bar.stop()
                         self.progress_var.set(0) # Reset progress variable

                if interrupted: final_status_key, final_task_key = "status_interrupted", "progress_label_interrupted"
                elif success: final_status_key, final_task_key = "status_completed", "progress_label_completed"
                else: final_status_key, final_task_key = "status_error", "progress_label_error"

                self.status_var.set(self.translate(final_status_key)) # Update shared status var
                self.current_task.set(self.translate(final_task_key)) # Update shared task var

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
            if hasattr(self, 'llm_tab') and self.llm_tab:
                 try: self.llm_tab.on_close()
                 except Exception as e: print(f"Error during LLM tab cleanup: {e}")
            # No specific cleanup needed for transcription_tab_ui, header, status bar
            # Stop Transcriber (if running)
            if hasattr(self.transcriber, 'request_stop'):
                 self.transcriber.request_stop()

            self.root.destroy()

# --- END OF MODIFIED FILE gui.py ---