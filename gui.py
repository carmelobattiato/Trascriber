# --- START OF COMPLETE MODIFIED FILE gui.py ---

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
    """Redirects stdout to a Tkinter ScrolledText widget safely."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, message):
        try:
            # Check if widget exists and is valid before attempting write
            if self.text_widget and isinstance(self.text_widget, tk.Widget) and self.text_widget.winfo_exists():
                self.text_widget.after_idle(self._insert_text, message)
            else:
                # Fallback print if GUI widget is gone
                print(f"Console Write Error (widget gone?): {message.strip()}", file=sys.__stderr__) # Write to stderr
        except tk.TclError:
            # Handle specific Tkinter errors during async operations
            print(f"Console Write Error (TclError): {message.strip()}", file=sys.__stderr__)
        except Exception as e:
             # Catch any other unexpected errors
             print(f"Console Write Error (General Exception): {e} - Message: {message.strip()}", file=sys.__stderr__)
        # Always write to the underlying StringIO buffer
        super().write(message)

    def _insert_text(self, message):
        """Helper method to insert text, called via after_idle."""
        try:
            # Double-check widget existence inside the scheduled call
            if self.text_widget and isinstance(self.text_widget, tk.Widget) and self.text_widget.winfo_exists():
                # Ensure widget is in a normal state to modify
                original_state = self.text_widget.cget('state')
                if original_state == tk.DISABLED:
                    self.text_widget.config(state=tk.NORMAL)
                self.text_widget.insert(tk.END, message)
                self.text_widget.see(tk.END)
                if original_state == tk.DISABLED:
                    self.text_widget.config(state=tk.DISABLED)
            # No fallback print here, as the original write attempted it
        except tk.TclError:
             # Error likely means widget was destroyed between scheduling and execution
             print(f"Console Insert Error (TclError - widget destroyed?): {message.strip()}", file=sys.__stderr__)
        except Exception as e:
             print(f"Console Insert Error (General Exception): {e} - Message: {message.strip()}", file=sys.__stderr__)


class ModernTranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.transcriber = AudioTranscriber(self)
        self.llm_processor = LLMProcessor()
        self.system_type = "mac" if sys.platform == "darwin" else "windows"

        self.setup_translations()
        self.current_language = tk.StringVar(value="English") # Default to English

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

        # --- FIX: Schedule the first UI text update instead of calling directly ---
        # self.update_ui_text() # REMOVED DIRECT CALL
        self.root.after_idle(self.update_ui_text) # Schedule the call

        # Redirect stdout - ensure console widget is available via the transcription tab instance
        # Use after_idle also for stdout redirection to ensure widget is fully ready
        self.root.after_idle(self._setup_stdout_redirect)

        # Handle application closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_stdout_redirect(self):
        """Helper method to redirect stdout after UI is idle."""
        try:
            # Check down the hierarchy: main_app -> transcription_tab -> console_output
            if (hasattr(self, 'transcription_tab') and
                    hasattr(self.transcription_tab, 'console_output') and
                    isinstance(self.transcription_tab.console_output, tk.Widget) and # Check type
                    self.transcription_tab.console_output.winfo_exists()):

                sys.stdout = ConsoleOutput(self.transcription_tab.console_output)
                print(self.translate("welcome_message")) # Print welcome message after redirection
                print(f"Stdout redirected to GUI console.")
            else:
                # If redirection fails, log to standard error to ensure visibility
                print("WARNING: Console output widget not found or not ready for stdout redirection during initial setup.", file=sys.__stderr__)
        except Exception as e:
            print(f"ERROR during stdout redirection setup: {e}", file=sys.__stderr__)


    def setup_translations(self):
        # (Translation dictionary remains the same as the previous full version)
        # --- Includes all keys for base app, recorder, and LLM tabs ---
        llm_translations_it = { "tab_llm": "Elaborazione LLM", "llm_input_label": "Testo di Input:", "llm_load_transcription": "⎗ Carica da Trascrizione", "llm_load_file": "📂 Carica File...", "llm_paste": "📋 Incolla", "llm_config_frame": "Configurazione LLM", "llm_provider_label": "Provider API:", "llm_api_key_label": "Chiave API:", "llm_model_label": "Modello:", "llm_instructions_label": "Istruzioni (Prompt di Sistema):", "llm_instructions_placeholder": "Es: Riassumi il testo seguente in punti chiave.", "llm_process_button": "✨ Elabora con LLM", "llm_output_label": "Risultato LLM:", "llm_copy_output": "📋 Copia Output", "llm_save_output": "💾 Salva Output...", "llm_status_loaded_transcription": "Caricato dalla trascrizione.", "llm_status_loaded_file": "File caricato: {filename}", "llm_status_pasted": "Testo incollato dagli appunti.", "llm_status_processing": "Elaborazione LLM in corso...", "llm_status_completed": "Elaborazione LLM completata.", "llm_status_error": "Errore durante l'elaborazione LLM.", "llm_status_ready": "Pronto per l'elaborazione LLM.", "llm_select_file_title": "Seleziona File di Testo", "llm_save_output_title": "Salva Output LLM", "llm_warn_no_transcription": "Nessun testo di trascrizione disponibile da caricare.", "llm_error_loading_transcription": "Errore nel caricare il testo della trascrizione", "llm_error_reading_file": "Errore nella lettura del file: {error}", "llm_warn_clipboard_empty": "Nessun testo trovato negli appunti.", "llm_error_pasting": "Errore durante l'operazione Incolla", "llm_error_no_provider": "Seleziona un provider API LLM!", "llm_error_no_model": "Seleziona un modello LLM!", "llm_error_no_input": "Inserisci del testo nell'area di Input!", "llm_warn_no_api_key": "La chiave API è vuota. Assicurati che sia impostata tramite variabili d'ambiente o inseriscila qui. Continuare?", "llm_error_unknown": "Si è verificato un errore sconosciuto durante l'elaborazione.", "llm_warn_no_output_to_copy": "Nessun output da copiare.", "llm_warn_no_output_to_save": "Nessun output da salvare.", "llm_info_copied_output": "Output LLM copiato negli appunti!", "llm_info_saved_output": "Output LLM salvato in {file}", "llm_error_copying": "Errore durante la copia dell'output LLM.", "llm_error_saving_output": "Errore durante il salvataggio dell'output LLM: {error}" }
        llm_translations_en = { "tab_llm": "LLM Processing", "llm_input_label": "Input Text:", "llm_load_transcription": "⎗ Load from Transcription", "llm_load_file": "📂 Load File...", "llm_paste": "📋 Paste", "llm_config_frame": "LLM Configuration", "llm_provider_label": "API Provider:", "llm_api_key_label": "API Key:", "llm_model_label": "Model:", "llm_instructions_label": "Instructions (System Prompt):", "llm_instructions_placeholder": "E.g.: Summarize the following text into key bullet points.", "llm_process_button": "✨ Process with LLM", "llm_output_label": "LLM Result:", "llm_copy_output": "📋 Copy Output", "llm_save_output": "💾 Save Output...", "llm_status_loaded_transcription": "Loaded from transcription.", "llm_status_loaded_file": "Loaded file: {filename}", "llm_status_pasted": "Pasted text from clipboard.", "llm_status_processing": "LLM processing...", "llm_status_completed": "LLM processing completed.", "llm_status_error": "Error during LLM processing.", "llm_status_ready": "Ready for LLM processing.", "llm_select_file_title": "Select Text File", "llm_save_output_title": "Save LLM Output", "llm_warn_no_transcription": "No transcription text available to load.", "llm_error_loading_transcription": "Error loading transcription text", "llm_error_reading_file": "Error reading file: {error}", "llm_warn_clipboard_empty": "No text found on clipboard.", "llm_error_pasting": "Error during paste operation", "llm_error_no_provider": "Please select an LLM API provider!", "llm_error_no_model": "Please select an LLM model!", "llm_error_no_input": "Please enter text in the Input area!", "llm_warn_no_api_key": "API Key is empty. Ensure it's set via environment variables or enter it here. Continue?", "llm_error_unknown": "An unknown error occurred during processing.", "llm_warn_no_output_to_copy": "No output to copy.", "llm_warn_no_output_to_save": "No output to save.", "llm_info_copied_output": "LLM output copied to clipboard!", "llm_info_saved_output": "LLM output saved to {file}", "llm_error_copying": "Error copying LLM output.", "llm_error_saving_output": "Error saving LLM output: {error}" }
        llm_translations_fr = { "tab_llm": "Traitement LLM", "llm_input_label": "Texte d'Entrée :", "llm_load_transcription": "⎗ Charger depuis Transcription", "llm_load_file": "📂 Charger Fichier...", "llm_paste": "📋 Coller", "llm_config_frame": "Configuration LLM", "llm_provider_label": "Fournisseur API :", "llm_api_key_label": "Clé API :", "llm_model_label": "Modèle :", "llm_instructions_label": "Instructions (Prompt Système) :", "llm_instructions_placeholder": "Ex : Résumez le texte suivant en points clés.", "llm_process_button": "✨ Traiter avec LLM", "llm_output_label": "Résultat LLM :", "llm_copy_output": "📋 Copier Sortie", "llm_save_output": "💾 Enregistrer Sortie...", "llm_status_loaded_transcription": "Chargé depuis la transcription.", "llm_status_loaded_file": "Fichier chargé : {filename}", "llm_status_pasted": "Texte collé depuis le presse-papiers.", "llm_status_processing": "Traitement LLM en cours...", "llm_status_completed": "Traitement LLM terminé.", "llm_status_error": "Erreur pendant le traitement LLM.", "llm_status_ready": "Prêt pour le traitement LLM.", "llm_select_file_title": "Sélectionner un Fichier Texte", "llm_save_output_title": "Enregistrer la Sortie LLM", "llm_warn_no_transcription": "Aucun texte de transcription disponible à charger.", "llm_error_loading_transcription": "Erreur lors du chargement du texte de transcription", "llm_error_reading_file": "Erreur de lecture du fichier : {error}", "llm_warn_clipboard_empty": "Aucun texte trouvé dans le presse-papiers.", "llm_error_pasting": "Erreur lors de l'opération Coller", "llm_error_no_provider": "Veuillez sélectionner un fournisseur d'API LLM !", "llm_error_no_model": "Veuillez sélectionner un modèle LLM !", "llm_error_no_input": "Veuillez entrer du texte dans la zone d'Entrée !", "llm_warn_no_api_key": "La clé API est vide. Assurez-vous qu'elle est définie via les variables d'environnement ou saisissez-la ici. Continuer ?", "llm_error_unknown": "Une erreur inconnue s'est produite lors du traitement.", "llm_warn_no_output_to_copy": "Aucune sortie à copier.", "llm_warn_no_output_to_save": "Aucune sortie à enregistrer.", "llm_info_copied_output": "Sortie LLM copiée dans le presse-papiers !", "llm_info_saved_output": "Sortie LLM enregistrée dans {file}", "llm_error_copying": "Erreur lors de la copie de la sortie LLM.", "llm_error_saving_output": "Erreur lors de l'enregistrement de la sortie LLM : {error}" }
        llm_translations_zh = { "tab_llm": "LLM 处理", "llm_input_label": "输入文本:", "llm_load_transcription": "⎗ 从转录加载", "llm_load_file": "📂 加载文件...", "llm_paste": "📋 粘贴", "llm_config_frame": "LLM 配置", "llm_provider_label": "API 提供商:", "llm_api_key_label": "API 密钥:", "llm_model_label": "模型:", "llm_instructions_label": "说明 (系统提示):", "llm_instructions_placeholder": "例如：将以下文本总结为关键要点。", "llm_process_button": "✨ 使用 LLM 处理", "llm_output_label": "LLM 结果:", "llm_copy_output": "📋 复制输出", "llm_save_output": "💾 保存输出...", "llm_status_loaded_transcription": "已从转录加载。", "llm_status_loaded_file": "已加载文件: {filename}", "llm_status_pasted": "已从剪贴板粘贴文本。", "llm_status_processing": "LLM 处理中...", "llm_status_completed": "LLM 处理完成。", "llm_status_error": "LLM 处理过程中出错。", "llm_status_ready": "准备进行 LLM 处理。", "llm_select_file_title": "选择文本文件", "llm_save_output_title": "保存 LLM 输出", "llm_warn_no_transcription": "没有可加载的转录文本。", "llm_error_loading_transcription": "加载转录文本时出错", "llm_error_reading_file": "读取文件时出错: {error}", "llm_warn_clipboard_empty": "剪贴板中未找到文本。", "llm_error_pasting": "粘贴操作期间出错", "llm_error_no_provider": "请选择一个 LLM API 提供商！", "llm_error_no_model": "请选择一个 LLM 模型！", "llm_error_no_input": "请在输入区域输入文本！", "llm_warn_no_api_key": "API 密钥为空。请确保通过环境变量设置或在此处输入。继续？", "llm_error_unknown": "处理过程中发生未知错误。", "llm_warn_no_output_to_copy": "没有要复制的输出。", "llm_warn_no_output_to_save": "没有要保存的输出。", "llm_info_copied_output": "LLM 输出已复制到剪贴板！", "llm_info_saved_output": "LLM 输出已保存到 {file}", "llm_error_copying": "复制 LLM 输出时出错。", "llm_error_saving_output": "保存 LLM 输出时出错: {error}" }

        self.translations = {
            "Italiano": {
                "window_title": "AudioScript - Trascrizione & Registrazione & LLM",
                "app_title": "AudioScript",
                "app_subtitle": "Trascrizione, Registrazione e Elaborazione LLM",
                "select_audio_frame": "Seleziona File Audio (WAV/MP3)",
                "wav_file_label": "File Audio:",
                "browse_button": "Sfoglia...",
                "options_frame": "Opzioni Trascrizione",
                "model_label": "Modello (Whisper):", # Clarified
                "language_label": "Lingua (Trascrizione):",
                "acceleration_label": "Accelerazione:",
                "use_gpu_checkbox": "Usa GPU",
                "gpu_tooltip_mac": "Usa Metal (MPS) su Mac",
                "gpu_tooltip_windows": "Usa DirectML su Windows",
                "start_button": "✓ Avvia Trascrizione",
                "stop_button": "⨯ Interrompi",
                "copy_button": "📋 Copia Testo",
                "save_button": "💾 Salva Testo...",
                "progress_label_analyzing": "Analisi...",
                "progress_label_loading_model": "Caricamento modello...",
                "progress_label_transcribing": "Trascrizione...",
                "progress_label_interrupted": "Interrotto",
                "progress_label_completed": "Completato",
                "progress_label_error": "Errore",
                "tab_transcription": "Trascrizione",
                "transcription_result_label": "Risultato Trascrizione:",
                "tab_console": "Console",
                "console_output_label": "Output Processo:",
                "tab_recorder": "Registra / Riproduci",
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
                "error_reading_duration": "Errore lettura durata: {error}",
                "error_gpu_init": "Errore init GPU: {error}, uso CPU",
                "error_model_load": "Errore caric. modello su {device}: {error}",
                "warning_title": "Attenzione",
                "warning_no_text_to_save": "Nessun testo da salvare!",
                "info_title": "Informazione",
                "copied_title": "Copiato",
                "copied_message": "Testo copiato negli appunti!",
                "saved_title": "Salvato",
                "saved_message": "File salvato: {file}",
                "completed_title": "Completato",
                "completed_message": "Trascrizione completata!",
                "selected_file_info": "File: {filename}\nDurata: {duration}, Canali: {channels}, Rate: {rate} Hz\n",
                "estimated_time_info": "Durata audio: {minutes}m {seconds}s\nStima tempo: {est_minutes}m {est_seconds}s\n",
                "model_loaded_info": "Modello caricato ({minutes}m {seconds}s).\n",
                "transcription_started_info": "Avvio trascrizione...\n",
                "transcription_finished_info": "Trascrizione finita ({minutes}m {seconds}s).\n",
                "stop_requested_info": "Interruzione richiesta...\n",
                "using_mps_info": "Uso accelerazione Metal (MPS)",
                "using_dml_info": "Uso accelerazione DirectML",
                "dml_not_available_info": "torch_directml non trovato, uso CPU",
                "gpu_backend_unavailable_info": "Backend GPU non disp., uso CPU",
                "transcriber_config_info": "Config: Modello={model_type}, Lingua={language}, Device={device}\n",
                "model_desc_tiny": "Veloce, precisione base",
                "model_desc_base": "Buon compromesso",
                "model_desc_small": "Buona qualità",
                "model_desc_medium": "Alta qualità",
                "model_desc_large": "Massima precisione",
                "language_select_label": "Lingua UI:",
                "welcome_message": "Benvenuto in AudioScript!",
                "ask_close_title": "Conferma Uscita",
                "ask_close_message": "Sei sicuro di voler uscire?",
                **llm_translations_it # Merge LLM translations
            },
            "English": {
                 "window_title": "AudioScript - Transcription & Recording & LLM",
                 "app_title": "AudioScript",
                 "app_subtitle": "Transcription, Recording & LLM Processing",
                 "select_audio_frame": "Select Audio File (WAV/MP3)",
                 "wav_file_label": "Audio File:",
                 "browse_button": "Browse...",
                 "options_frame": "Transcription Options",
                 "model_label": "Model (Whisper):", # Clarified
                 "language_label": "Language (Transcription):",
                 "acceleration_label": "Acceleration:",
                 "use_gpu_checkbox": "Use GPU",
                 "gpu_tooltip_mac": "Use Metal (MPS) on Mac",
                 "gpu_tooltip_windows": "Use DirectML on Windows",
                 "start_button": "✓ Start Transcription",
                 "stop_button": "⨯ Stop",
                 "copy_button": "📋 Copy Text",
                 "save_button": "💾 Save Text...",
                 "progress_label_analyzing": "Analyzing...",
                 "progress_label_loading_model": "Loading model...",
                 "progress_label_transcribing": "Transcribing...",
                 "progress_label_interrupted": "Interrupted",
                 "progress_label_completed": "Completed",
                 "progress_label_error": "Error",
                 "tab_transcription": "Transcription",
                 "transcription_result_label": "Transcription Result:",
                 "tab_console": "Console",
                 "console_output_label": "Process Output:",
                 "tab_recorder": "Record / Play",
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
                 "error_reading_duration": "Error reading duration: {error}",
                 "error_gpu_init": "GPU init error: {error}, using CPU",
                 "error_model_load": "Error loading model on {device}: {error}",
                 "warning_title": "Warning",
                 "warning_no_text_to_save": "No text to save!",
                 "info_title": "Information",
                 "copied_title": "Copied",
                 "copied_message": "Text copied to clipboard!",
                 "saved_title": "Saved",
                 "saved_message": "File saved: {file}",
                 "completed_title": "Completed",
                 "completed_message": "Transcription finished!",
                 "selected_file_info": "File: {filename}\nDuration: {duration}, Channels: {channels}, Rate: {rate} Hz\n",
                 "estimated_time_info": "Audio duration: {minutes}m {seconds}s\nEst. time: {est_minutes}m {est_seconds}s\n",
                 "model_loaded_info": "Model loaded ({minutes}m {seconds}s).\n",
                 "transcription_started_info": "Starting transcription...\n",
                 "transcription_finished_info": "Transcription finished ({minutes}m {seconds}s).\n",
                 "stop_requested_info": "Stop requested...\n",
                 "using_mps_info": "Using Metal (MPS) acceleration",
                 "using_dml_info": "Using DirectML acceleration",
                 "dml_not_available_info": "torch_directml not found, using CPU",
                 "gpu_backend_unavailable_info": "GPU backend not available, using CPU",
                 "transcriber_config_info": "Config: Model={model_type}, Lang={language}, Device={device}\n",
                 "model_desc_tiny": "Fast, basic accuracy",
                 "model_desc_base": "Good compromise",
                 "model_desc_small": "Good quality",
                 "model_desc_medium": "High quality",
                 "model_desc_large": "Maximum precision",
                 "language_select_label": "UI Language:",
                 "welcome_message": "Welcome to AudioScript!",
                 "ask_close_title": "Confirm Exit",
                 "ask_close_message": "Are you sure you want to exit?",
                **llm_translations_en # Merge LLM translations
            },
             "Francais": {
                 "window_title": "AudioScript - Transcription & Enregistrement & LLM",
                 "app_title": "AudioScript",
                 "app_subtitle": "Transcription, Enregistrement et Traitement LLM",
                 "select_audio_frame": "Sélectionner Fichier Audio (WAV/MP3)",
                 "wav_file_label": "Fichier Audio :",
                 "browse_button": "Parcourir...",
                 "options_frame": "Options Transcription",
                 "model_label": "Modèle (Whisper) :", # Clarified
                 "language_label": "Langue (Transcription) :",
                 "acceleration_label": "Accélération :",
                 "use_gpu_checkbox": "Utiliser GPU",
                 "gpu_tooltip_mac": "Utiliser Metal (MPS) sur Mac",
                 "gpu_tooltip_windows": "Utiliser DirectML sur Windows",
                 "start_button": "✓ Démarrer Transcription",
                 "stop_button": "⨯ Arrêter",
                 "copy_button": "📋 Copier Texte",
                 "save_button": "💾 Enregistrer Texte...",
                 "progress_label_analyzing": "Analyse...",
                 "progress_label_loading_model": "Chargement modèle...",
                 "progress_label_transcribing": "Transcription...",
                 "progress_label_interrupted": "Interrompu",
                 "progress_label_completed": "Terminé",
                 "progress_label_error": "Erreur",
                 "tab_transcription": "Transcription",
                 "transcription_result_label": "Résultat Transcription :",
                 "tab_console": "Console",
                 "console_output_label": "Sortie Processus :",
                 "tab_recorder": "Enregistrer / Lire",
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
                 "error_reading_duration": "Erreur lecture durée : {error}",
                 "error_gpu_init": "Erreur init GPU : {error}, usage CPU",
                 "error_model_load": "Erreur charg. modèle sur {device} : {error}",
                 "warning_title": "Attention",
                 "warning_no_text_to_save": "Aucun texte à enregistrer !",
                 "info_title": "Information",
                 "copied_title": "Copié",
                 "copied_message": "Texte copié dans le presse-papiers !",
                 "saved_title": "Enregistré",
                 "saved_message": "Fichier enregistré : {file}",
                 "completed_title": "Terminé",
                 "completed_message": "Transcription terminée !",
                 "selected_file_info": "Fichier : {filename}\nDurée : {duration}, Canaux : {channels}, Taux : {rate} Hz\n",
                 "estimated_time_info": "Durée audio : {minutes}m {seconds}s\nTemps estimé : {est_minutes}m {est_seconds}s\n",
                 "model_loaded_info": "Modèle chargé ({minutes}m {seconds}s).\n",
                 "transcription_started_info": "Démarrage transcription...\n",
                 "transcription_finished_info": "Transcription finie ({minutes}m {seconds}s).\n",
                 "stop_requested_info": "Arrêt demandé...\n",
                 "using_mps_info": "Utilisation accélération Metal (MPS)",
                 "using_dml_info": "Utilisation accélération DirectML",
                 "dml_not_available_info": "torch_directml non trouvé, usage CPU",
                 "gpu_backend_unavailable_info": "Backend GPU non dispo., usage CPU",
                 "transcriber_config_info": "Config : Modèle={model_type}, Langue={language}, Périph={device}\n",
                 "model_desc_tiny": "Rapide, précision base",
                 "model_desc_base": "Bon compromis",
                 "model_desc_small": "Bonne qualité",
                 "model_desc_medium": "Haute qualité",
                 "model_desc_large": "Précision maximale",
                 "language_select_label": "Langue UI :",
                 "welcome_message": "Bienvenue dans AudioScript !",
                 "ask_close_title": "Confirmer Fermeture",
                 "ask_close_message": "Êtes-vous sûr de vouloir quitter ?",
                **llm_translations_fr # Merge LLM translations
             },
             "中文": {
                 "window_title": "AudioScript - 转录 & 录制 & LLM",
                 "app_title": "AudioScript",
                 "app_subtitle": "转录、录制和 LLM 处理",
                 "select_audio_frame": "选择音频文件 (WAV/MP3)",
                 "wav_file_label": "音频文件:",
                 "browse_button": "浏览...",
                 "options_frame": "转录选项",
                 "model_label": "模型 (Whisper):", # Clarified
                 "language_label": "语言 (转录):",
                 "acceleration_label": "加速:",
                 "use_gpu_checkbox": "使用 GPU",
                 "gpu_tooltip_mac": "在 Mac 上使用 Metal (MPS)",
                 "gpu_tooltip_windows": "在 Windows 上使用 DirectML",
                 "start_button": "✓ 开始转录",
                 "stop_button": "⨯ 停止",
                 "copy_button": "📋 复制文本",
                 "save_button": "💾 保存文本...",
                 "progress_label_analyzing": "分析中...",
                 "progress_label_loading_model": "加载模型...",
                 "progress_label_transcribing": "转录中...",
                 "progress_label_interrupted": "已中断",
                 "progress_label_completed": "完成",
                 "progress_label_error": "错误",
                 "tab_transcription": "转录",
                 "transcription_result_label": "转录结果:",
                 "tab_console": "控制台",
                 "console_output_label": "进程输出:",
                 "tab_recorder": "录制 / 播放",
                 "status_ready": "准备就绪",
                 "status_stopping": "正在停止...",
                 "status_loading_model": "加载模型...",
                 "status_transcribing": "转录中...",
                 "status_completed": "完成",
                 "status_error": "错误",
                 "status_interrupted": "已中断",
                 "error_title": "错误",
                 "error_no_file": "请选择有效的音频文件！",
                 "error_saving": "保存出错：{error}",
                 "error_reading_info": "读取文件信息出错：{error}",
                 "error_reading_duration": "读取时长出错：{error}",
                 "error_gpu_init": "GPU 初始化错误：{error}，使用 CPU",
                 "error_model_load": "在 {device} 加载模型出错：{error}",
                 "warning_title": "警告",
                 "warning_no_text_to_save": "没有要保存的文本！",
                 "info_title": "信息",
                 "copied_title": "已复制",
                 "copied_message": "文本已复制到剪贴板！",
                 "saved_title": "已保存",
                 "saved_message": "文件已保存：{file}",
                 "completed_title": "完成",
                 "completed_message": "转录完成！",
                 "selected_file_info": "文件：{filename}\n时长：{duration}, 声道：{channels}, 采样率：{rate} Hz\n",
                 "estimated_time_info": "音频时长：{minutes}分 {seconds}秒\n预计时间：{est_minutes}分 {est_seconds}秒\n",
                 "model_loaded_info": "模型已加载 ({minutes}分 {seconds}秒)。\n",
                 "transcription_started_info": "开始转录...\n",
                 "transcription_finished_info": "转录完成 ({minutes}分 {seconds}秒)。\n",
                 "stop_requested_info": "已请求停止...\n",
                 "using_mps_info": "使用 Metal (MPS) 加速",
                 "using_dml_info": "使用 DirectML 加速",
                 "dml_not_available_info": "未找到 torch_directml，使用 CPU",
                 "gpu_backend_unavailable_info": "无可用 GPU 后端，使用 CPU",
                 "transcriber_config_info": "配置：模型={model_type}, 语言={language}, 设备={device}\n",
                 "model_desc_tiny": "快速，基本精度",
                 "model_desc_base": "良好折衷",
                 "model_desc_small": "良好质量",
                 "model_desc_medium": "高质量",
                 "model_desc_large": "最高精度",
                 "language_select_label": "界面语言:",
                 "welcome_message": "欢迎使用 AudioScript！",
                 "ask_close_title": "确认退出",
                 "ask_close_message": "确定要退出吗？",
                **llm_translations_zh # Merge LLM translations
             }
        }
        self.model_descriptions = {
            "tiny": "model_desc_tiny", "base": "model_desc_base", "small": "model_desc_small",
            "medium": "model_desc_medium", "large": "model_desc_large",
        }


    def translate(self, key):
        lang_code = self.current_language.get()
        # Fallback chain: Selected Lang -> English -> Placeholder Key
        selected_lang_dict = self.translations.get(lang_code, self.translations['English'])
        return selected_lang_dict.get(key, self.translations['English'].get(key, f"<{key}>"))


    def setup_ui_styles(self):
        # (Styling setup remains the same)
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
        # Store instance reference
        self.transcription_tab = TranscriptionTabUI(self.main_notebook, self)
        self.main_notebook.add(self.transcription_tab.frame, text="") # Text set later

        # Recorder Tab (gets added to notebook)
        # Store instance reference
        self.recorder_tab = RecorderTab(self.main_notebook, self.update_transcription_path)
        self.main_notebook.add(self.recorder_tab.frame, text="") # Text set later

        # LLM Tab (gets added to notebook)
        # Store instance reference
        self.llm_tab = LLMTab(self.main_notebook, self, self.llm_processor)
        self.main_notebook.add(self.llm_tab.frame, text="") # Text set later

        # Status Bar (packs itself at the bottom)
        # Store instance reference
        self.status_bar = StatusBar(self.root, self)


    def update_ui_text(self):
        """Updates UI text by delegating to components."""
        if not hasattr(self, 'main_notebook') or not self.main_notebook.winfo_exists(): return

        # Update window title
        self.root.title(self.translate("window_title"))

        # Update Header
        if hasattr(self, 'header'): self.header.update_ui_text()

        # Update Main Notebook Tab Titles
        try:
            tabs = self.main_notebook.tabs() # Get the list of tab identifiers
            # Tab indices are 0, 1, 2 assuming the order they were added
            if len(tabs) > 0: self.main_notebook.tab(tabs[0], text=self.translate("tab_transcription"))
            if len(tabs) > 1: self.main_notebook.tab(tabs[1], text=self.translate("tab_recorder"))
            if len(tabs) > 2: self.main_notebook.tab(tabs[2], text=self.translate("tab_llm"))
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

        # Update main status bar text only if it's currently "Ready" in any language
        current_status = self.status_var.get()
        is_ready = False
        for code in self.translations:
            # Check against None or empty string as well
            ready_text = self.translations[code].get('status_ready')
            if ready_text and current_status == ready_text:
                is_ready = True
                break
        if is_ready:
             self.status_var.set(self.translate("status_ready")) # Set to the current language's "Ready"


    # --- Methods Accessing Widgets (Now via component instances) ---

    def get_transcription_text(self):
        """Returns the current text from the transcription result widget."""
        try:
            # Access the text widget via the transcription_tab instance
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'result_text') and self.transcription_tab.result_text.winfo_exists():
                return self.transcription_tab.result_text.get("1.0", tk.END).strip()
        except tk.TclError:
            print("Error getting transcription text (widget destroyed?)")
        return ""

    def console_output_insert(self, text):
        """Safely inserts text into the console output widget."""
        try:
             # Access console via transcription_tab instance
             if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'console_output') and isinstance(self.transcription_tab.console_output, tk.Widget) and self.transcription_tab.console_output.winfo_exists():
                 # If stdout is correctly redirected to our ConsoleOutput object, use its write method
                 if isinstance(sys.stdout, ConsoleOutput) and sys.stdout.text_widget == self.transcription_tab.console_output:
                      sys.stdout.write(text) # This will handle after_idle and state checks
                 else:
                      # Fallback: If stdout isn't redirected or redirected elsewhere, insert directly (less safe)
                      console_widget = self.transcription_tab.console_output
                      console_widget.after_idle(lambda w=console_widget, t=text: (
                         w.config(state=tk.NORMAL),
                         w.insert(tk.END, t),
                         w.see(tk.END),
                         w.config(state=tk.DISABLED) # Assuming console might be disabled
                      ))
             else:
                 # Log to actual stderr if GUI console isn't available
                 print(f"GUI Console Log (Widget missing): {text.strip()}", file=sys.__stderr__)
        except Exception as e:
             # Catch-all for unexpected errors during insertion attempt
             print(f"Error inserting to console: {e}\nMessage: {text.strip()}", file=sys.__stderr__)

    def console_output_delete_all(self):
        """Safely deletes all text from the console output widget."""
        try:
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'console_output') and isinstance(self.transcription_tab.console_output, tk.Widget) and self.transcription_tab.console_output.winfo_exists():
                console_widget = self.transcription_tab.console_output
                # Use after_idle to ensure it runs in the main thread
                console_widget.after_idle(lambda w=console_widget: (
                    w.config(state=tk.NORMAL),
                    w.delete(1.0, tk.END),
                    w.config(state=tk.DISABLED) # Re-disable if needed
                ))
        except tk.TclError:
             print("TclError deleting console text (widget likely destroyed).")
        except Exception as e:
             print(f"Error deleting console text: {e}")


    def result_text_set(self, text):
        """Safely sets the text in the result text widget."""
        try:
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'result_text') and isinstance(self.transcription_tab.result_text, tk.Widget) and self.transcription_tab.result_text.winfo_exists():
                 result_widget = self.transcription_tab.result_text
                 result_widget.after_idle(lambda w=result_widget, t=text: (
                     w.config(state=tk.NORMAL), # Ensure widget is editable
                     w.delete(1.0, tk.END),
                     w.insert(tk.END, t),
                     w.see(tk.END)
                     # Keep NORMAL? Or make it DISABLED again? Assume NORMAL for results.
                 ))
        except tk.TclError:
             print("TclError setting result text (widget likely destroyed).")
        except Exception as e:
             print(f"Error setting result text: {e}")


    def result_text_clear(self):
        """Safely clears the result text widget."""
        try:
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'result_text') and isinstance(self.transcription_tab.result_text, tk.Widget) and self.transcription_tab.result_text.winfo_exists():
                 result_widget = self.transcription_tab.result_text
                 result_widget.after_idle(lambda w=result_widget: (
                    w.config(state=tk.NORMAL),
                    w.delete(1.0, tk.END)
                 ))
        except tk.TclError:
             print("TclError clearing result text (widget likely destroyed).")
        except Exception as e:
            print(f"Error clearing result text: {e}")


    # --- Core Logic Methods (Callbacks, Actions) ---
    # These methods now access UI elements via the component instances (e.g., self.transcription_tab.start_button)

    def on_language_select(self, event=None):
        # Bound to the combobox in HeaderFrame.
        # The textvariable `self.current_language` is automatically updated.
        # We just need to trigger the actions associated with the language change.
        # The trace ('write' mode) we set on self.current_language should call self.change_language.
        # If the trace sometimes doesn't fire (unlikely but possible in complex scenarios),
        # you could force it or call change_language directly:
        # self.current_language.set(self.current_language.get()) # Force trace
        pass # Rely on the trace calling change_language

    def change_language(self, *args):
        """Handles language change for the entire application."""
        print(f"Language change detected: {self.current_language.get()}")
        # Update all components' text
        self.update_ui_text()
        # Update model description specifically, as it depends on language
        self.update_model_description()
        print(f"UI updated for language: {self.current_language.get()}")


    def update_model_description(self, event=None):
        # Accesses model_var (main app) and model_desc_var (main app)
        # The label widget itself is in transcription_tab
        try:
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'model_desc_label') and self.transcription_tab.model_desc_label.winfo_exists():
                 selected_model = self.model_var.get()
                 desc_key = self.model_descriptions.get(selected_model, "model_desc_large")
                 self.model_desc_var.set(self.translate(desc_key)) # Update the shared variable
        except tk.TclError:
            print("Error updating model description (widget destroyed?)")
        except Exception as e:
            print(f"Error in update_model_description: {e}")


    def show_gpu_tooltip(self, event):
        # Tooltip logic remains here as it's generic UI behavior
        # Ensure previous tooltip is destroyed
        self._destroy_tooltip()

        # Create new tooltip window
        try:
            self.gpu_tooltip = tk.Toplevel(self.root)
            self.gpu_tooltip.wm_overrideredirect(True)
            # Position near the mouse cursor
            x = self.root.winfo_pointerx() + 15
            y = self.root.winfo_pointery() + 10
            self.gpu_tooltip.wm_geometry(f"+{x}+{y}")

            # Get appropriate message based on OS
            msg = self.translate("gpu_tooltip_mac") if self.system_type == "mac" else self.translate("gpu_tooltip_windows")

            # Create and pack the label inside the tooltip window
            label = ttk.Label(self.gpu_tooltip, text=msg, justify=tk.LEFT, background="#ffffe0", relief="solid", borderwidth=1, padding=5, font=("Segoe UI", 9))
            label.pack(ipadx=1, ipady=1)

            # Schedule tooltip destruction after a delay
            self._tooltip_after_id = self.root.after(5000, self._destroy_tooltip)

            # Bind leave event to the originating widget (GPU checkbutton)
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'gpu_check'):
                # Unbind first to prevent multiple bindings if Enter event fires rapidly
                self.transcription_tab.gpu_check.unbind("<Leave>")
                self.transcription_tab.gpu_check.bind("<Leave>", self._on_leave_tooltip)
        except Exception as e:
            print(f"Error showing GPU tooltip: {e}")
            if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip:
                try:
                    self.gpu_tooltip.destroy()
                except: pass
            self.gpu_tooltip = None


    def _destroy_tooltip(self):
        # Cancel pending destruction timer if it exists
        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id:
            try:
                self.root.after_cancel(self._tooltip_after_id)
            except ValueError: pass # Timer ID might be invalid already
            self._tooltip_after_id = None

        # Destroy the tooltip window if it exists
        if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip and isinstance(self.gpu_tooltip, tk.Toplevel) and self.gpu_tooltip.winfo_exists():
            try:
                self.gpu_tooltip.destroy()
            except tk.TclError: pass # Window might already be gone
        self.gpu_tooltip = None

        # Attempt to unbind the leave event from the checkbutton
        try:
            if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'gpu_check') and isinstance(self.transcription_tab.gpu_check, tk.Widget) and self.transcription_tab.gpu_check.winfo_exists():
                self.transcription_tab.gpu_check.unbind("<Leave>")
        except tk.TclError: pass # Widget might be gone
        except Exception as e: print(f"Error unbinding tooltip leave event: {e}")


    def _on_leave_tooltip(self, event=None):
        # Called when mouse leaves the GPU checkbutton
        self._destroy_tooltip()


    def get_language_code(self, language_name):
        # Logic remains here
        language_map = { "italiano": "italian", "inglese": "english", "francese": "french", "tedesco": "german", "spagnolo": "spanish", "giapponese": "japanese", "cinese": "chinese" }
        return language_map.get(language_name.lower(), "italian") # Default to italian if not found


    def select_file(self):
        # File dialog logic remains here, updates main app's file_path var
        initial_dir = os.path.dirname(self.file_path.get()) if self.file_path.get() else os.path.expanduser("~") # Default to home dir
        file = filedialog.askopenfilename(
            title=self.translate("select_audio_frame"),
            initialdir=initial_dir,
            filetypes=[("Audio files", "*.wav *.mp3 *.flac *.ogg *.m4a"), ("All files", "*.*")] # Expanded types
        )
        if file:
            self.file_path.set(file) # Update the shared variable
            filename = os.path.basename(file)
            # Attempt to get info for WAV, otherwise just log filename
            if file.lower().endswith(".wav"):
                try:
                    file_info = self.transcriber.get_audio_info(file)
                    if file_info:
                        duration, channels, rate = file_info
                        duration_str = format_duration(duration)
                        info_msg = self.translate("selected_file_info").format(
                            filename=filename, duration=duration_str, channels=channels, rate=rate
                        )
                        self.console_output_insert(info_msg)
                    else:
                         self.console_output_insert(f"Could not read WAV info for: {filename}\n")
                except Exception as e:
                     self.console_output_insert(f"Error reading WAV info for {filename}: {e}\n")
            else:
                # For non-wav, duration requires other libs (like audio_handler uses)
                # We can just show the filename here for simplicity
                self.console_output_insert(f"Selected audio file: {filename}\n")


    def update_transcription_path(self, file_path):
         # Logic remains here, updates main app's file_path var and switches tab
         if file_path and os.path.exists(file_path):
             self.file_path.set(file_path)
             self.console_output_insert(f"Audio file path set from recorder: {os.path.basename(file_path)}\n")
             # Switch focus to transcription tab
             if hasattr(self, 'main_notebook'):
                  try:
                      # Find the transcription tab's frame/ID to select it reliably
                      transcription_tab_id = None
                      if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'frame'):
                          transcription_tab_id = self.transcription_tab.frame
                      if transcription_tab_id:
                          self.main_notebook.select(transcription_tab_id)
                      else:
                          self.main_notebook.select(0) # Fallback to index 0
                  except tk.TclError: print("Could not switch to transcription tab (TclError).")
                  except Exception as e: print(f"Could not switch to transcription tab (Error: {e}).")
         else:
             self.console_output_insert(f"Invalid file path received from recorder: {file_path}\n")


    def start_transcription(self):
        # Gets vars from main app, calls transcriber, updates UI state via methods below
        input_file = self.file_path.get(); model_type = self.model_var.get()
        language = self.get_language_code(self.transcription_language_var.get()); use_gpu = self.use_gpu_var.get()

        if not input_file or not os.path.isfile(input_file):
            messagebox.showerror(self.translate("error_title"), self.translate("error_no_file"))
            return

        # --- Update UI State (Access widgets via transcription_tab) ---
        try:
            if hasattr(self, 'transcription_tab'):
                 if hasattr(self.transcription_tab,'start_button') and self.transcription_tab.start_button.winfo_exists():
                     self.transcription_tab.start_button.config(state=tk.DISABLED)
                 if hasattr(self.transcription_tab,'stop_button') and self.transcription_tab.stop_button.winfo_exists():
                     self.transcription_tab.stop_button.config(state=tk.NORMAL)
        except tk.TclError:
             print("Error updating transcription button states (widget destroyed?)")
             return # Don't proceed if UI is broken

        # --- Clear previous results and logs ---
        self.console_output_delete_all()
        self.result_text_clear()

        # --- Start transcription ---
        self.transcriber.start_transcription_async(input_file, model_type, language, use_gpu, self.system_type)


    def stop_transcription(self):
        # Calls transcriber, updates UI state via methods below
        if hasattr(self.transcriber, 'request_stop'):
             self.transcriber.request_stop()
             self.console_output_insert(self.translate("stop_requested_info"))
             # Update status variables immediately
             self.status_var.set(self.translate("status_stopping"))
             self.current_task.set(self.translate("progress_label_interrupted"))

             # --- Update UI State ---
             try:
                 if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab,'stop_button') and self.transcription_tab.stop_button.winfo_exists():
                     # Disable stop button immediately after requesting stop
                     self.transcription_tab.stop_button.config(state=tk.DISABLED)
                 # Start button is re-enabled in finalize_ui_state
             except tk.TclError:
                  print("Error disabling stop button (widget destroyed?)")


    def copy_to_clipboard(self):
        # Gets text via self.get_transcription_text(), interacts with clipboard
        try:
            text_to_copy = self.get_transcription_text() # Use helper method
            if not text_to_copy:
                messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save"))
                return
            # Perform clipboard operations
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            self.root.update() # Necessary on some platforms
            messagebox.showinfo(self.translate("copied_title"), self.translate("copied_message"))
        except tk.TclError as e:
            # Specific TclError might indicate clipboard issues
            messagebox.showerror(self.translate("error_title"), f"Clipboard error: {e}")
        except Exception as e:
            # Catch other potential errors
             messagebox.showerror(self.translate("error_title"), f"Error copying text: {e}")


    def save_transcription(self):
        # Gets text via self.get_transcription_text(), shows file dialog
        text = self.get_transcription_text() # Use helper method
        if not text:
            messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save"))
            return

        # Suggest filename based on input audio file
        original_filename = os.path.basename(self.file_path.get())
        if original_filename:
            suggested_filename = os.path.splitext(original_filename)[0] + "_transcription.txt"
        else:
            suggested_filename = self.translate('tab_transcription').lower().replace(" ", "_") + ".txt"

        # Get save directory based on input file or home directory
        initial_dir = os.path.dirname(self.file_path.get()) if self.file_path.get() else os.path.expanduser("~")

        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            title=self.translate("save_button"), # Use translation for title
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=suggested_filename,
            initialdir=initial_dir
        )

        # Save the file if a path was provided
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo(self.translate("saved_title"), self.translate("saved_message").format(file=file_path))
                self.console_output_insert(f"Transcription saved to: {file_path}\n")
            except Exception as e:
                error_msg = self.translate("error_saving").format(error=str(e))
                messagebox.showerror(self.translate("error_title"), error_msg)
                self.console_output_insert(f"ERROR saving transcription: {error_msg}\n")


    # --- UI State Management Methods ---
    # These methods update shared state vars and progress bar (which is in transcription_tab)

    def update_progress_state(self, task_key=None, status_key=None, progress_mode="start"):
        """Updates the progress bar and status labels via after_idle."""
        task_text = self.translate(task_key) if task_key else self.current_task.get()
        status_text = self.translate(status_key) if status_key else self.status_var.get()

        def _update():
            try:
                if not self.root.winfo_exists(): return # Exit if root window closed

                # Update shared state variables
                self.current_task.set(task_text)
                self.status_var.set(status_text)

                # Access progress bar via transcription_tab instance
                if hasattr(self, 'transcription_tab') and hasattr(self.transcription_tab, 'progress_bar') and isinstance(self.transcription_tab.progress_bar, ttk.Progressbar) and self.transcription_tab.progress_bar.winfo_exists():
                    pb = self.transcription_tab.progress_bar
                    if progress_mode == "start" or progress_mode == "indeterminate":
                        pb.config(mode="indeterminate")
                        pb.start(15) # Interval for indeterminate animation step
                    elif progress_mode == "stop":
                        pb.stop()
                        pb.config(mode="determinate")
                        self.progress_var.set(0) # Reset progress variable
                    elif progress_mode == "determinate":
                         pb.config(mode="determinate")
                         # Optionally set a value: self.progress_var.set(some_value)
                else:
                     print(f"Progress bar widget not available for update (Task: {task_text})", file=sys.__stderr__)

            except tk.TclError:
                 print(f"Status Update Failed (TclError): Task={task_text}, Status={status_text}", file=sys.__stderr__)
            except Exception as e:
                 print(f"Status Update Failed (Error: {e}): Task={task_text}, Status={status_text}", file=sys.__stderr__)

        # Schedule the update in the main Tkinter thread
        if hasattr(self, 'root') and self.root.winfo_exists():
             self.root.after_idle(_update)


    def finalize_ui_state(self, success=True, interrupted=False):
        """Finalizes UI elements after transcription (buttons, progress) via after_idle."""
        def _finalize():
            try:
                if not self.root.winfo_exists(): return # Exit if root window closed

                # Access buttons and progress bar via transcription_tab instance
                if hasattr(self, 'transcription_tab'):
                     # Re-enable start button, disable stop button
                     if hasattr(self.transcription_tab,'start_button') and self.transcription_tab.start_button.winfo_exists():
                         self.transcription_tab.start_button.config(state=tk.NORMAL)
                     if hasattr(self.transcription_tab,'stop_button') and self.transcription_tab.stop_button.winfo_exists():
                         self.transcription_tab.stop_button.config(state=tk.DISABLED)
                     # Stop and reset progress bar
                     if hasattr(self.transcription_tab, 'progress_bar') and isinstance(self.transcription_tab.progress_bar, ttk.Progressbar) and self.transcription_tab.progress_bar.winfo_exists():
                         self.transcription_tab.progress_bar.stop()
                         self.progress_var.set(0) # Reset progress variable

                # Determine final status message keys
                if interrupted:
                    final_status_key, final_task_key = "status_interrupted", "progress_label_interrupted"
                elif success:
                    final_status_key, final_task_key = "status_completed", "progress_label_completed"
                else: # Error case
                    final_status_key, final_task_key = "status_error", "progress_label_error"

                # Update shared status/task variables
                self.status_var.set(self.translate(final_status_key))
                self.current_task.set(self.translate(final_task_key))

            except tk.TclError:
                 print("Failed to finalize UI state (TclError - widget destroyed?).", file=sys.__stderr__)
            except Exception as e:
                 print(f"Failed to finalize UI state (Error: {e}).", file=sys.__stderr__)

        # Schedule the finalization in the main Tkinter thread
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.after_idle(_finalize)


    def on_closing(self):
        """Handle application closing, including tab cleanup."""
        # Ask for confirmation
        if messagebox.askokcancel(self.translate("ask_close_title"), self.translate("ask_close_message")):
            print("Exiting application...")

            # Gracefully stop background processes/threads
            # Stop Transcriber (if running)
            if hasattr(self.transcriber, 'request_stop'):
                 print("Requesting transcription stop...")
                 self.transcriber.request_stop()

            # Cleanup Recorder Tab (stops recording/playback)
            if hasattr(self, 'recorder_tab') and self.recorder_tab:
                 try:
                     print("Cleaning up recorder tab...")
                     self.recorder_tab.on_close()
                 except Exception as e: print(f"Error during recorder tab cleanup: {e}", file=sys.__stderr__)

            # Cleanup LLM Tab (if any background processing needs stopping - currently none)
            if hasattr(self, 'llm_tab') and self.llm_tab:
                 try:
                     print("Cleaning up LLM tab...")
                     self.llm_tab.on_close()
                 except Exception as e: print(f"Error during LLM tab cleanup: {e}", file=sys.__stderr__)

            # Destroy the main window
            print("Destroying root window.")
            self.root.destroy()

# --- END OF COMPLETE MODIFIED FILE gui.py ---