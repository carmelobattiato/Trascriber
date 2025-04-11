# --- START OF MODIFIED FILE gui.py ---

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import io
import os
import sys
from tkinter.scrolledtext import ScrolledText
from datetime import timedelta
from transcriber import AudioTranscriber
from utils import format_duration # Import the utility
# --- NEW: Import the recorder tab ---
from recorder_tab import RecorderTab
import json # Used for potentially loading translations later if needed


class ConsoleOutput(io.StringIO):
    # ... (Keep the ConsoleOutput class as it was in the previous corrected version) ...
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, message):
        # Ensure the widget still exists before writing
        try:
            if self.text_widget.winfo_exists():
                # Schedule the update in the Tkinter main loop
                self.text_widget.after_idle(self._insert_text, message)
        except tk.TclError:
            # Handle cases where the widget might be destroyed during async operations
            print(f"Console Write Error (widget destroyed?): {message.strip()}")
            pass
        except Exception as e:
            # Catch other potential errors during write
             print(f"Console Write Error (General Exception): {e} - Message: {message.strip()}")

        # Always write to the buffer even if GUI update fails
        super().write(message) # Keep writing to the StringIO buffer regardless

    def _insert_text(self, message):
        """Helper method to insert text, called via after_idle."""
        try:
            if self.text_widget.winfo_exists():
                self.text_widget.insert(tk.END, message)
                self.text_widget.see(tk.END)
                # Reducing frequency of update_idletasks might improve performance
                # self.text_widget.update_idletasks()
        except tk.TclError:
             print(f"Console Insert Error (widget destroyed?): {message.strip()}")
        except Exception as e:
             print(f"Console Insert Error (General Exception): {e} - Message: {message.strip()}")

class ModernTranscriptionApp:
    def __init__(self, root):
        # ... (Keep the __init__ method mostly the same as the previous version) ...
        self.root = root
        self.transcriber = AudioTranscriber(self)
        self.system_type = "mac" if sys.platform == "darwin" else "windows"

        self.setup_translations()
        self.current_language = tk.StringVar(value="it") # Default language code

        # Initialize variables that depend on translation AFTER translations are set up
        self.status_var = tk.StringVar(value=self.translate("status_ready"))
        self.current_task = tk.StringVar(value="")
        self.model_desc_var = tk.StringVar(value=self.translate("model_desc_large")) # Initial default

        self.setup_ui_styles()
        self.create_widgets() # Create all widgets first

        # Set up the trace *after* widgets are created
        self.current_language.trace_add("write", self.change_language)

        self.update_ui_text() # Set initial text based on default language

        # Redirect stdout only after console widget exists
        if hasattr(self, 'console_output') and self.console_output:
             try:
                  if self.console_output.winfo_exists():
                      sys.stdout = ConsoleOutput(self.console_output)
                      print(self.translate("welcome_message")) # Initial message
                  else:
                       print("WARNING: Console output widget destroyed before stdout redirection.")
             except tk.TclError:
                  print("WARNING: Console output widget not ready for stdout redirection (TclError).")
        else:
             print("WARNING: Console output widget not found, stdout not redirected.")

        # Handle application closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)


    def setup_translations(self):
        # ... (Keep the setup_translations method the same as the previous version) ...
        self.translations = {
            "Italiano": {
                "window_title": "AudioScript - Trascrizione e Registrazione Audio", # Updated Title
                "app_title": "AudioScript",
                "app_subtitle": "Trascrizione e Registrazione Audio", # Updated Subtitle
                "select_audio_frame": "Seleziona File Audio",
                "wav_file_label": "File WAV:",
                "browse_button": "Sfoglia...",
                "options_frame": "Opzioni Trascrizione", # Clarified Frame Title
                "model_label": "Modello:",
                "language_label": "Lingua (Trascrizione):",
                "acceleration_label": "Accelerazione:",
                "use_gpu_checkbox": "Usa GPU (se disponibile)",
                "gpu_tooltip_mac": "Seleziona per usare l'accelerazione hardware:\n- Mac: Usa Metal Performance Shaders (MPS)",
                "gpu_tooltip_windows": "Seleziona per usare l'accelerazione hardware:\n- Windows: Usa DirectML per GPU integrate",
                "start_button": "✓ Avvia Trascrizione",
                "stop_button": "⨯ Interrompi Trascrizione", # Clarified Button
                "copy_button": "📋 Copia Testo", # Clarified Button
                "save_button": "💾 Salva Testo", # Clarified Button
                "progress_label_analyzing": "Analisi del file audio...",
                "progress_label_loading_model": "Caricamento del modello di AI...",
                "progress_label_transcribing": "Trascrizione in corso...",
                "progress_label_interrupted": "Processo interrotto",
                "progress_label_completed": "Trascrizione completata con successo",
                "progress_label_error": "Si è verificato un errore",
                "tab_transcription": "Trascrizione",
                "transcription_result_label": "Risultato della trascrizione:",
                "tab_console": "Console e Log",
                "console_output_label": "Output del processo:",
                "tab_recorder": "Registra & Riproduci", # NEW TAB TITLE
                "status_ready": "Pronto",
                "status_stopping": "Interruzione in corso...",
                "status_loading_model": "Caricamento modello...",
                "status_transcribing": "Trascrizione in corso...",
                "status_completed": "Trascrizione completata",
                "status_error": "Errore durante la trascrizione",
                "status_interrupted": "Interrotto dall'utente",
                "error_title": "Errore",
                "error_no_file": "Seleziona un file WAV valido!", # Clarified error
                "error_saving": "Errore durante il salvataggio: {error}",
                "error_reading_info": "Errore nel leggere le informazioni del file: {error}",
                "error_reading_duration": "Errore nel leggere la durata del file: {error}",
                "error_gpu_init": "Errore nell'inizializzazione GPU: {error}, usando CPU",
                "error_model_load": "Errore nel caricamento del modello su {device}: {error}, riprovo con CPU",
                "warning_title": "Attenzione",
                "warning_no_text_to_save": "Non c'è testo da salvare!",
                "info_title": "Informazione",
                "copied_title": "Copiato",
                "copied_message": "Testo copiato negli appunti!", # Clarified message
                "saved_title": "Salvato",
                "saved_message": "File salvato con successo in {file}",
                "completed_title": "Completato",
                "completed_message": "Trascrizione completata!",
                "selected_file_info": "File selezionato: {filename}\nDurata: {duration}, Canali: {channels}, Sample rate: {rate} Hz\n",
                "estimated_time_info": "Durata dell'audio: {minutes} min {seconds} sec\nStima del tempo di trascrizione: {est_minutes} min {est_seconds} sec\n",
                "model_loaded_info": "Modello caricato in {minutes} minuti e {seconds} secondi.\n",
                "transcription_started_info": "Avvio della trascrizione...\n",
                "transcription_finished_info": "Trascrizione completata in {minutes} minuti e {seconds} secondi.\n",
                "stop_requested_info": "Interruzione richiesta. Attendere il completamento dell'operazione in corso...\n",
                "using_mps_info": "Usando accelerazione Metal (MPS) per Mac",
                "using_dml_info": "Usando accelerazione DirectML per Windows",
                "dml_not_available_info": "torch_directml non disponibile, usando CPU",
                "gpu_backend_unavailable_info": "GPU richiesta ma nessun backend disponibile, usando CPU",
                "transcriber_config_info": "Configurazione: Modello {model_type}, Lingua {language}, Dispositivo {device}\n",
                "model_desc_tiny": "Veloce, precisione base",
                "model_desc_base": "Buon compromesso",
                "model_desc_small": "Buona qualità",
                "model_desc_medium": "Alta qualità",
                "model_desc_large": "Massima precisione",
                "language_select_label": "Lingua Interfaccia:",
                "welcome_message": "Benvenuto in AudioScript!",
                "ask_close_title": "Conferma Uscita",
                "ask_close_message": "Sei sicuro di voler uscire?",
            },
            "English": {
                "window_title": "AudioScript - Audio Transcription & Recording", # Updated Title
                "app_title": "AudioScript",
                "app_subtitle": "Audio Transcription & Recording", # Updated Subtitle
                "select_audio_frame": "Select Audio File",
                "wav_file_label": "WAV File:",
                "browse_button": "Browse...",
                "options_frame": "Transcription Options", # Clarified Frame Title
                "model_label": "Model:",
                "language_label": "Language (Transcription):",
                "acceleration_label": "Acceleration:",
                "use_gpu_checkbox": "Use GPU (if available)",
                "gpu_tooltip_mac": "Select to use hardware acceleration:\n- Mac: Use Metal Performance Shaders (MPS)",
                "gpu_tooltip_windows": "Select to use hardware acceleration:\n- Windows: Use DirectML for integrated GPUs",
                "start_button": "✓ Start Transcription",
                "stop_button": "⨯ Stop Transcription", # Clarified Button
                "copy_button": "📋 Copy Text", # Clarified Button
                "save_button": "💾 Save Text", # Clarified Button
                "progress_label_analyzing": "Analyzing audio file...",
                "progress_label_loading_model": "Loading AI model...",
                "progress_label_transcribing": "Transcription in progress...",
                "progress_label_interrupted": "Process interrupted",
                "progress_label_completed": "Transcription completed successfully",
                "progress_label_error": "An error occurred",
                "tab_transcription": "Transcription",
                "transcription_result_label": "Transcription result:",
                "tab_console": "Console & Logs",
                "console_output_label": "Process output:",
                "tab_recorder": "Record & Play", # NEW TAB TITLE
                "status_ready": "Ready",
                "status_stopping": "Stopping...",
                "status_loading_model": "Loading model...",
                "status_transcribing": "Transcribing...",
                "status_completed": "Transcription completed",
                "status_error": "Error during transcription",
                "status_interrupted": "Interrupted by user",
                "error_title": "Error",
                "error_no_file": "Please select a valid WAV file!", # Clarified error
                "error_saving": "Error while saving: {error}",
                "error_reading_info": "Error reading file information: {error}",
                "error_reading_duration": "Error reading file duration: {error}",
                "error_gpu_init": "Error initializing GPU: {error}, using CPU",
                "error_model_load": "Error loading model on {device}: {error}, retrying with CPU",
                "warning_title": "Warning",
                "warning_no_text_to_save": "There is no text to save!",
                "info_title": "Information",
                "copied_title": "Copied",
                "copied_message": "Text copied to clipboard!", # Clarified message
                "saved_title": "Saved",
                "saved_message": "File saved successfully to {file}",
                "completed_title": "Completed",
                "completed_message": "Transcription finished!",
                "selected_file_info": "Selected file: {filename}\nDuration: {duration}, Channels: {channels}, Sample rate: {rate} Hz\n",
                "estimated_time_info": "Audio duration: {minutes} min {seconds} sec\nEstimated transcription time: {est_minutes} min {est_seconds} sec\n",
                "model_loaded_info": "Model loaded in {minutes} minutes and {seconds} seconds.\n",
                "transcription_started_info": "Starting transcription...\n",
                "transcription_finished_info": "Transcription completed in {minutes} minutes and {seconds} seconds.\n",
                "stop_requested_info": "Stop requested. Waiting for the current operation to complete...\n",
                "using_mps_info": "Using Metal (MPS) acceleration for Mac",
                "using_dml_info": "Using DirectML acceleration for Windows",
                "dml_not_available_info": "torch_directml not available, using CPU",
                "gpu_backend_unavailable_info": "GPU requested but no backend available, using CPU",
                "transcriber_config_info": "Configuration: Model {model_type}, Language {language}, Device {device}\n",
                "model_desc_tiny": "Fast, basic accuracy",
                "model_desc_base": "Good compromise",
                "model_desc_small": "Good quality",
                "model_desc_medium": "High quality",
                "model_desc_large": "Maximum precision",
                "language_select_label": "Interface Language:",
                "welcome_message": "Welcome to AudioScript!",
                "ask_close_title": "Confirm Exit",
                "ask_close_message": "Are you sure you want to exit?",
            },
             # --- Add French and Chinese translations similarly, including "tab_recorder" ---
             "Francais": {
                "window_title": "AudioScript - Transcription & Enregistrement Audio",
                "app_title": "AudioScript",
                "app_subtitle": "Transcription & Enregistrement Audio",
                "select_audio_frame": "Sélectionner le Fichier Audio",
                "wav_file_label": "Fichier WAV :",
                "browse_button": "Parcourir...",
                "options_frame": "Options de Transcription",
                "model_label": "Modèle :",
                "language_label": "Langue (Transcription) :",
                "acceleration_label": "Accélération :",
                "use_gpu_checkbox": "Utiliser le GPU (si disponible)",
                "gpu_tooltip_mac": "Sélectionnez pour utiliser l'accélération matérielle :\n- Mac : Utiliser Metal Performance Shaders (MPS)",
                "gpu_tooltip_windows": "Sélectionnez pour utiliser l'accélération matérielle :\n- Windows : Utiliser DirectML pour les GPU intégrés",
                "start_button": "✓ Démarrer la Transcription",
                "stop_button": "⨯ Arrêter la Transcription",
                "copy_button": "📋 Copier le Texte",
                "save_button": "💾 Enregistrer le Texte",
                "progress_label_analyzing": "Analyse du fichier audio...",
                "progress_label_loading_model": "Chargement du modèle d'IA...",
                "progress_label_transcribing": "Transcription en cours...",
                "progress_label_interrupted": "Processus interrompu",
                "progress_label_completed": "Transcription terminée avec succès",
                "progress_label_error": "Une erreur s'est produite",
                "tab_transcription": "Transcription",
                "transcription_result_label": "Résultat de la transcription :",
                "tab_console": "Console & Logs",
                "console_output_label": "Sortie du processus :",
                "tab_recorder": "Enregistrer & Lire", # NEW TAB TITLE
                "status_ready": "Prêt",
                "status_stopping": "Arrêt en cours...",
                "status_loading_model": "Chargement du modèle...",
                "status_transcribing": "Transcription...",
                "status_completed": "Transcription terminée",
                "status_error": "Erreur pendant la transcription",
                "status_interrupted": "Interrompu par l'utilisateur",
                "error_title": "Erreur",
                "error_no_file": "Veuillez sélectionner un fichier WAV valide !",
                "error_saving": "Erreur lors de l'enregistrement : {error}",
                "error_reading_info": "Erreur lors de la lecture des informations du fichier : {error}",
                "error_reading_duration": "Erreur lors de la lecture de la durée du fichier : {error}",
                "error_gpu_init": "Erreur d'initialisation du GPU : {error}, utilisation du CPU",
                "error_model_load": "Erreur de chargement du modèle sur {device} : {error}, nouvel essai avec le CPU",
                "warning_title": "Attention",
                "warning_no_text_to_save": "Il n'y a pas de texte à enregistrer !",
                "info_title": "Information",
                "copied_title": "Copié",
                "copied_message": "Texte copié dans le presse-papiers !",
                "saved_title": "Enregistré",
                "saved_message": "Fichier enregistré avec succès dans {file}",
                "completed_title": "Terminé",
                "completed_message": "Transcription terminée !",
                "selected_file_info": "Fichier sélectionné : {filename}\nDurée : {duration}, Canaux : {channels}, Taux d'échantillonnage : {rate} Hz\n",
                "estimated_time_info": "Durée de l'audio : {minutes} min {seconds} sec\nTemps de transcription estimé : {est_minutes} min {est_seconds} sec\n",
                "model_loaded_info": "Modèle chargé en {minutes} minutes et {seconds} secondes.\n",
                "transcription_started_info": "Démarrage de la transcription...\n",
                "transcription_finished_info": "Transcription terminée en {minutes} minutes et {seconds} secondes.\n",
                "stop_requested_info": "Arrêt demandé. Attente de la fin de l'opération en cours...\n",
                "using_mps_info": "Utilisation de l'accélération Metal (MPS) pour Mac",
                "using_dml_info": "Utilisation de l'accélération DirectML pour Windows",
                "dml_not_available_info": "torch_directml non disponible, utilisation du CPU",
                "gpu_backend_unavailable_info": "GPU demandé mais aucun backend disponible, utilisation du CPU",
                "transcriber_config_info": "Configuration : Modèle {model_type}, Langue {language}, Périphérique {device}\n",
                "model_desc_tiny": "Rapide, précision de base",
                "model_desc_base": "Bon compromis",
                "model_desc_small": "Bonne qualité",
                "model_desc_medium": "Haute qualité",
                "model_desc_large": "Précision maximale",
                "language_select_label": "Langue de l'interface :",
                "welcome_message": "Bienvenue dans AudioScript !",
                "ask_close_title": "Confirmer la fermeture",
                "ask_close_message": "Êtes-vous sûr de vouloir quitter ?",
             },
             "中文": {
                "window_title": "AudioScript - 音频转录与录制",
                "app_title": "AudioScript",
                "app_subtitle": "音频转录与录制",
                "select_audio_frame": "选择音频文件",
                "wav_file_label": "WAV 文件:",
                "browse_button": "浏览...",
                "options_frame": "转录选项",
                "model_label": "模型:",
                "language_label": "语言 (转录):",
                "acceleration_label": "加速:",
                "use_gpu_checkbox": "使用 GPU (如果可用)",
                "gpu_tooltip_mac": "选择以使用硬件加速:\n- Mac: 使用 Metal Performance Shaders (MPS)",
                "gpu_tooltip_windows": "选择以使用硬件加速:\n- Windows: 使用 DirectML (集成 GPU)",
                "start_button": "✓ 开始转录",
                "stop_button": "⨯ 停止转录",
                "copy_button": "📋 复制文本",
                "save_button": "💾 保存文本",
                "progress_label_analyzing": "正在分析音频文件...",
                "progress_label_loading_model": "正在加载 AI 模型...",
                "progress_label_transcribing": "转录进行中...",
                "progress_label_interrupted": "进程已中断",
                "progress_label_completed": "转录成功完成",
                "progress_label_error": "发生错误",
                "tab_transcription": "转录",
                "transcription_result_label": "转录结果:",
                "tab_console": "控制台和日志",
                "console_output_label": "进程输出:",
                "tab_recorder": "录制 & 播放", # NEW TAB TITLE
                "status_ready": "准备就绪",
                "status_stopping": "正在停止...",
                "status_loading_model": "正在加载模型...",
                "status_transcribing": "正在转录...",
                "status_completed": "转录完成",
                "status_error": "转录过程中出错",
                "status_interrupted": "用户已中断",
                "error_title": "错误",
                "error_no_file": "请选择一个有效的 WAV 文件!",
                "error_saving": "保存时出错: {error}",
                "error_reading_info": "读取文件信息时出错: {error}",
                "error_reading_duration": "读取文件持续时间时出错: {error}",
                "error_gpu_init": "初始化 GPU 时出错: {error}, 使用 CPU",
                "error_model_load": "在 {device} 上加载模型时出错: {error}, 使用 CPU 重试",
                "warning_title": "警告",
                "warning_no_text_to_save": "没有要保存的文本!",
                "info_title": "信息",
                "copied_title": "已复制",
                "copied_message": "文本已复制到剪贴板!",
                "saved_title": "已保存",
                "saved_message": "文件成功保存到 {file}",
                "completed_title": "已完成",
                "completed_message": "转录完成!",
                "selected_file_info": "选定文件: {filename}\n持续时间: {duration}, 声道: {channels}, 采样率: {rate} Hz\n",
                "estimated_time_info": "音频时长: {minutes} 分 {seconds} 秒\n预计转录时间: {est_minutes} 分 {est_seconds} 秒\n",
                "model_loaded_info": "模型加载耗时 {minutes} 分 {seconds} 秒。\n",
                "transcription_started_info": "开始转录...\n",
                "transcription_finished_info": "转录完成耗时 {minutes} 分 {seconds} 秒。\n",
                "stop_requested_info": "已请求停止。请等待当前操作完成...\n",
                "using_mps_info": "正在为 Mac 使用 Metal (MPS) 加速",
                "using_dml_info": "正在为 Windows 使用 DirectML 加速",
                "dml_not_available_info": "torch_directml 不可用，使用 CPU",
                "gpu_backend_unavailable_info": "请求了 GPU 但无可用后端，使用 CPU",
                "transcriber_config_info": "配置: 模型 {model_type}, 语言 {language}, 设备 {device}\n",
                "model_desc_tiny": "快速，基本精度",
                "model_desc_base": "良好折衷",
                "model_desc_small": "良好质量",
                "model_desc_medium": "高质量",
                "model_desc_large": "最高精度",
                "language_select_label": "界面语言:",
                "welcome_message": "欢迎使用 AudioScript！",
                "ask_close_title": "确认退出",
                "ask_close_message": "确定要退出吗？",
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
        # Fallback to English if the key or language is missing
        return self.translations.get(lang_code, self.translations['English']).get(key, self.translations['English'].get(key, f"<{key}>"))


    def setup_ui_styles(self):
        # ... (setup_ui_styles method remains the same) ...
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except tk.TclError:
             available_themes = self.style.theme_names()
             print(f"Theme 'clam' not found. Available themes: {available_themes}")
             if available_themes:
                 self.style.theme_use(available_themes[0])

        self.primary_color = "#3498db"
        self.secondary_color = "#2980b9"
        self.bg_color = "#f5f5f5"
        self.text_color = "#2c3e50"
        self.success_color = "#2ecc71"
        self.warning_color = "#e74c3c"

        self.root.configure(bg=self.bg_color)

        default_font = ("Segoe UI", 10)
        bold_font = ("Segoe UI", 10, "bold")
        heading_font = ("Segoe UI", 14, "bold")
        console_font = ("Consolas", 10)

        self.style.configure("Card.TFrame", background=self.bg_color, relief="raised", borderwidth=1)
        self.style.configure("Primary.TButton", background=self.primary_color, foreground="white", padding=10, font=bold_font)
        self.style.map("Primary.TButton", background=[("active", self.secondary_color), ("disabled", "#95a5a6")])
        self.style.configure("Action.TButton", background=self.secondary_color, foreground="white", padding=8, font=("Segoe UI", 9))
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=default_font)
        self.style.configure("Heading.TLabel", background=self.bg_color, foreground=self.text_color, font=heading_font)
        self.style.configure("Status.TLabel", background="#ecf0f1", foreground=self.text_color, padding=5, relief="sunken", font=default_font)
        self.style.configure("TProgressbar", background=self.primary_color, troughcolor="#d1d1d1", thickness=10)
        self.style.configure("TCombobox", padding=5, font=default_font)
        self.style.configure("TLabelframe.Label", font=bold_font, foreground=self.text_color, background=self.bg_color)
        self.style.configure("TRadiobutton", background=self.bg_color, font=default_font)
        # Ensure Notebook tab font is reasonable
        self.style.configure("TNotebook.Tab", font=default_font, padding=[5, 2])


    def create_widgets(self):
        # --- Variables ---
        self.file_path = tk.StringVar() # Path for transcription file
        self.model_var = tk.StringVar(value="large")
        self.transcription_language_var = tk.StringVar(value="italiano") # For whisper
        # Status/Progress vars initialized in __init__ using translate

        self.progress_var = tk.DoubleVar(value=0)
        self.use_gpu_var = tk.BooleanVar(value=False)

        # --- Main Layout (using pack for header and main content notebook) ---
        # Header Frame (remains packed at top)
        self.header_frame = ttk.Frame(self.root, style="Card.TFrame", padding=(20, 10, 20, 10))
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        self.header_frame.columnconfigure(1, weight=1) # Allow subtitle to take space

        self.app_title_label = ttk.Label(self.header_frame, text="", style="Heading.TLabel")
        self.app_title_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.app_subtitle_label = ttk.Label(self.header_frame, text="", style="TLabel")
        self.app_subtitle_label.grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Language Selection Frame (aligned right in header)
        lang_select_frame = ttk.Frame(self.header_frame, style="Card.TFrame")
        lang_select_frame.grid(row=0, column=2, sticky="e")
        self.lang_select_label = ttk.Label(lang_select_frame, text="")
        self.lang_select_label.pack(side=tk.LEFT, padx=(0, 5))
        self.lang_options = {"English": "English", "Italiano": "Italiano", "Français": "Français", "中文": "中文"}
        self.language_selector = ttk.Combobox(lang_select_frame, textvariable=self.current_language,
                                              values=list(self.lang_options.keys()), state="readonly", width=10)
        # Set English as default language
        self.current_language.set("English")  # Set English code as default
        initial_lang_name = "English"    # Set English display name as default
        self.language_selector.set(initial_lang_name)
        self.language_selector.bind("<<ComboboxSelected>>", self.on_language_select)
        self.language_selector.pack(side=tk.LEFT)


        # --- Main Content Notebook ---
        self.main_notebook = ttk.Notebook(self.root, padding=(20, 10, 20, 10))
        self.main_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # --- Create Transcription Tab Frame ---
        transcription_tab_frame = ttk.Frame(self.main_notebook, padding="10")
        # Add transcription tab FIRST
        self.main_notebook.add(transcription_tab_frame, text="") # Text set in update_ui_text
        # Configure grid for transcription tab content
        transcription_tab_frame.columnconfigure(0, weight=1)
        transcription_tab_frame.rowconfigure(4, weight=1) # Make results notebook expand


        # --- Widgets for Transcription Tab (now inside transcription_tab_frame) ---
        # File Selection
        self.file_frame = ttk.LabelFrame(transcription_tab_frame, text="", padding=10)
        self.file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.file_frame.columnconfigure(1, weight=1) # Make entry expand

        self.wav_file_label = ttk.Label(self.file_frame, text="")
        self.wav_file_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path, width=60)
        self.file_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.browse_button = ttk.Button(self.file_frame, text="", command=self.select_file, style="Action.TButton")
        self.browse_button.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # Options
        self.options_frame = ttk.LabelFrame(transcription_tab_frame, text="", padding=10)
        self.options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.options_frame.columnconfigure(2, weight=1) # Description takes remaining space

        self.model_label = ttk.Label(self.options_frame, text="")
        self.model_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        models = ["tiny", "base", "small", "medium", "large"]
        self.model_combobox = ttk.Combobox(self.options_frame, textvariable=self.model_var, values=models, state="readonly", width=15)
        self.model_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.model_combobox.set("large")
        self.model_desc_label = ttk.Label(self.options_frame, textvariable=self.model_desc_var, anchor="w")
        self.model_desc_label.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
        self.model_combobox.bind("<<ComboboxSelected>>", self.update_model_description)

        self.transcription_language_label = ttk.Label(self.options_frame, text="")
        self.transcription_language_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.transcription_languages = ["italiano", "inglese", "francese", "tedesco", "spagnolo", "giapponese", "cinese"]
        self.language_combobox = ttk.Combobox(self.options_frame, textvariable=self.transcription_language_var,
                                            values=self.transcription_languages, state="readonly", width=15)
        self.language_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.language_combobox.set("italiano")

        self.acceleration_label = ttk.Label(self.options_frame, text="")
        self.acceleration_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.gpu_check = ttk.Checkbutton(self.options_frame, text="", variable=self.use_gpu_var)
        self.gpu_check.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        self.gpu_check.bind("<Enter>", self.show_gpu_tooltip)
        self.gpu_tooltip = None

        # Buttons
        buttons_frame = ttk.Frame(transcription_tab_frame)
        buttons_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))

        self.start_button = ttk.Button(buttons_frame, text="", command=self.start_transcription, style="Primary.TButton")
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.stop_button = ttk.Button(buttons_frame, text="", command=self.stop_transcription, style="Action.TButton", state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)

        action_buttons_right = ttk.Frame(buttons_frame)
        action_buttons_right.pack(side=tk.RIGHT)
        self.save_button = ttk.Button(action_buttons_right, text="", command=self.save_transcription, style="Action.TButton")
        self.save_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.copy_button = ttk.Button(action_buttons_right, text="", command=self.copy_to_clipboard, style="Action.TButton")
        self.copy_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Progress
        progress_frame = ttk.Frame(transcription_tab_frame)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        progress_frame.columnconfigure(0, weight=1)

        self.current_task_label = ttk.Label(progress_frame, textvariable=self.current_task, anchor="w")
        self.current_task_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                         mode="indeterminate", length=100, style="TProgressbar")
        self.progress_bar.grid(row=1, column=0, sticky="ew")


        # Results Notebook (Transcription Text / Console)
        self.results_notebook = ttk.Notebook(transcription_tab_frame)
        self.results_notebook.grid(row=4, column=0, sticky="nsew", pady=(0, 5)) # Reduced bottom padding

        # -- Transcription Result Tab --
        transcription_result_frame = ttk.Frame(self.results_notebook, padding=10)
        transcription_result_frame.pack(fill=tk.BOTH, expand=True)
        transcription_result_frame.columnconfigure(0, weight=1)
        transcription_result_frame.rowconfigure(1, weight=1)
        self.results_notebook.add(transcription_result_frame, text="") # Text set in update_ui_text

        self.transcription_result_label = ttk.Label(transcription_result_frame, text="")
        self.transcription_result_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        result_text_frame = ttk.Frame(transcription_result_frame, borderwidth=1, relief="sunken")
        result_text_frame.grid(row=1, column=0, sticky="nsew")
        result_text_frame.rowconfigure(0, weight=1)
        result_text_frame.columnconfigure(0, weight=1)
        self.result_text = ScrolledText(result_text_frame, wrap=tk.WORD, width=80, height=10, # Adjusted height
                                     font=("Segoe UI", 11), background="white", foreground=self.text_color,
                                     borderwidth=0, relief="flat")
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # -- Console Tab --
        console_frame = ttk.Frame(self.results_notebook, padding=10)
        console_frame.pack(fill=tk.BOTH, expand=True)
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(1, weight=1)
        self.results_notebook.add(console_frame, text="") # Text set in update_ui_text

        self.console_output_label = ttk.Label(console_frame, text="")
        self.console_output_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        console_text_frame = ttk.Frame(console_frame, borderwidth=1, relief="sunken")
        console_text_frame.grid(row=1, column=0, sticky="nsew")
        console_text_frame.rowconfigure(0, weight=1)
        console_text_frame.columnconfigure(0, weight=1)
        self.console_output = ScrolledText(console_text_frame, wrap=tk.WORD, width=80, height=10, # Adjusted height
                                     background="#f0f0f0", foreground="#333",
                                     font=("Consolas", 10),
                                     borderwidth=0, relief="flat")
        self.console_output.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        # --- Create and Add Recorder Tab ---
        # Pass the main notebook and the callback function
        self.recorder_tab = RecorderTab(self.main_notebook, self.update_transcription_path)
        # --- FIX: Explicitly add the recorder tab's frame to the main notebook ---
        # The recorder_tab object holds the frame in self.recorder_tab.frame
        # The text will be set later by update_ui_text
        self.main_notebook.add(self.recorder_tab.frame, text="")


        # --- Status Bar (remains packed at bottom) ---
        self.status_frame = ttk.Frame(self.root, style="Status.TFrame", borderwidth=1, relief='groove')
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)


    def update_ui_text(self):
        """Updates all UI elements with text based on the current language."""
        # ... (Keep the rest of update_ui_text the same as the previous version) ...
        # Check if widgets have been created before trying to configure them
        if not hasattr(self, 'main_notebook') or not self.main_notebook.winfo_exists():
            return

        lang = self.current_language.get()
        self.root.title(self.translate("window_title"))

        # Header
        self.app_title_label.config(text=self.translate("app_title"))
        self.app_subtitle_label.config(text=self.translate("app_subtitle"))
        self.lang_select_label.config(text=self.translate("language_select_label"))

        # --- Update Main Notebook Tab Titles ---
        try:
            tab_count = len(self.main_notebook.tabs())
            # Index 0: Transcription Tab Frame
            if tab_count > 0:
                self.main_notebook.tab(0, text=self.translate("tab_transcription"))
            # Index 1: Recorder Tab Frame (added in create_widgets)
            if tab_count > 1:
                 self.main_notebook.tab(1, text=self.translate("tab_recorder"))

        except tk.TclError as e:
            print(f"Error updating main notebook tabs: {e}")


        # --- Update Transcription Tab Widgets ---
        if hasattr(self, 'file_frame'):
            self.file_frame.config(text=self.translate("select_audio_frame"))
            self.wav_file_label.config(text=self.translate("wav_file_label"))
            self.browse_button.config(text=self.translate("browse_button"))

        if hasattr(self, 'options_frame'):
            self.options_frame.config(text=self.translate("options_frame"))
            self.model_label.config(text=self.translate("model_label"))
            self.transcription_language_label.config(text=self.translate("language_label"))
            self.acceleration_label.config(text=self.translate("acceleration_label"))
            self.gpu_check.config(text=self.translate("use_gpu_checkbox"))
            self.update_model_description()

        if hasattr(self, 'start_button'):
            self.start_button.config(text=self.translate("start_button"))
            self.stop_button.config(text=self.translate("stop_button"))
            self.copy_button.config(text=self.translate("copy_button"))
            self.save_button.config(text=self.translate("save_button"))

        # Update results notebook (nested inside transcription tab) tab texts
        if hasattr(self, 'results_notebook'):
             try:
                 # Only update if tabs exist
                 if len(self.results_notebook.tabs()) >= 2:
                    self.results_notebook.tab(0, text=self.translate("tab_transcription")) # Text Result
                    self.results_notebook.tab(1, text=self.translate("tab_console"))      # Console
             except tk.TclError as e:
                 print(f"Error updating results notebook tabs: {e}")

        if hasattr(self, 'transcription_result_label'):
            self.transcription_result_label.config(text=self.translate("transcription_result_label"))
        if hasattr(self, 'console_output_label'):
            self.console_output_label.config(text=self.translate("console_output_label"))

        # Update status bar text
        is_ready = False
        for code in self.translations:
            # Check against None or empty string as well
            current_status = self.status_var.get()
            if current_status and current_status == self.translations[code].get('status_ready'):
                is_ready = True
                break
        if is_ready:
             self.status_var.set(self.translate("status_ready"))


    # --- Other methods (on_language_select, change_language, etc.) ---
    # ... (Keep all other methods like on_language_select, change_language, update_model_description, ...)
    # ... (show_gpu_tooltip, _destroy_tooltip, _on_leave_tooltip, get_language_code, select_file, ...)
    # ... (update_transcription_path, start_transcription, stop_transcription, copy_to_clipboard, save_transcription, ...)
    # ... (console_output_insert, console_output_delete_all, result_text_set, result_text_clear, ...)
    # ... (update_progress_state, finalize_ui_state, on_closing) the same as the previous version ...
    def on_language_select(self, event=None):
        selected_display_name = self.language_selector.get()
        new_lang_code = self.lang_options.get(selected_display_name, "English")
        self.current_language.set(new_lang_code)

    def change_language(self, *args):
        self.update_ui_text()

    def update_model_description(self, event=None):
        if hasattr(self, 'model_combobox'):
             selected_model = self.model_combobox.get()
             desc_key = self.model_descriptions.get(selected_model, "model_desc_large")
             self.model_desc_var.set(self.translate(desc_key))

    def show_gpu_tooltip(self, event):
        if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip and self.gpu_tooltip.winfo_exists():
            self.gpu_tooltip.destroy()
        self.gpu_tooltip = None

        self.gpu_tooltip = tk.Toplevel(self.root)
        self.gpu_tooltip.wm_overrideredirect(True)
        x = event.x_root + 15
        y = event.y_root + 10
        self.gpu_tooltip.wm_geometry(f"+{x}+{y}")

        if self.system_type == "mac":
            msg = self.translate("gpu_tooltip_mac")
        else:
             msg = self.translate("gpu_tooltip_windows")

        label = ttk.Label(self.gpu_tooltip, text=msg, justify=tk.LEFT,
                          background="#ffffe0", relief="solid", borderwidth=1, padding=5,
                          font=("Segoe UI", 9))
        label.pack(ipadx=1, ipady=1)

        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id: # Cancel previous timer if exists
             self.root.after_cancel(self._tooltip_after_id)

        self._tooltip_after_id = self.root.after(5000, self._destroy_tooltip)

        # Ensure binding only happens once or rebind correctly
        if hasattr(self, 'gpu_check'):
             self.gpu_check.unbind("<Leave>") # Remove previous binding first
             self.gpu_check.bind("<Leave>", self._on_leave_tooltip)

    def _destroy_tooltip(self):
        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id:
            try:
                self.root.after_cancel(self._tooltip_after_id)
            except ValueError: # Handle case where ID might be invalid already
                pass
            self._tooltip_after_id = None
        if hasattr(self, 'gpu_tooltip') and self.gpu_tooltip and self.gpu_tooltip.winfo_exists():
            self.gpu_tooltip.destroy()
        self.gpu_tooltip = None
        if hasattr(self, 'gpu_check'):
            try:
                 if self.gpu_check.winfo_exists():
                     self.gpu_check.unbind("<Leave>")
            except tk.TclError:
                 pass

    def _on_leave_tooltip(self, event=None):
        self._destroy_tooltip()

    def get_language_code(self, language_name):
        language_map = {
            "italiano": "italian", "inglese": "english", "francese": "french",
            "tedesco": "german", "spagnolo": "spanish", "giapponese": "japanese",
            "cinese": "chinese"
        }
        return language_map.get(language_name.lower(), "italian")

    def select_file(self):
        initial_dir = os.path.dirname(self.file_path.get()) if self.file_path.get() else "/"
        file = filedialog.askopenfilename(
            title=self.translate("select_audio_frame"),
            initialdir=initial_dir,
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if file:
            self.file_path.set(file)
            file_info = self.transcriber.get_audio_info(file)
            if file_info:
                duration, channels, rate = file_info
                duration_str = format_duration(duration)
                filename = os.path.basename(file)
                info_msg = self.translate("selected_file_info").format(
                    filename=filename, duration=duration_str, channels=channels, rate=rate
                )
                self.console_output_insert(info_msg)
            else:
                 self.console_output_insert(f"Could not read info for: {os.path.basename(file)}\n")

    def update_transcription_path(self, file_path):
        if file_path and os.path.exists(file_path):
            self.file_path.set(file_path)
            print(f"Transcription file path set to: {file_path}")
            if hasattr(self, 'main_notebook'):
                 try:
                     # Find index dynamically (more robust but slightly slower)
                     tab_id_transcription = None
                     for i, tab_id in enumerate(self.main_notebook.tabs()):
                         # We need a way to identify the transcription tab's frame.
                         # Assuming transcription_tab_frame is stored as self.transcription_tab_frame
                         if hasattr(self, 'transcription_tab_frame') and tab_id == str(self.transcription_tab_frame):
                             tab_id_transcription = i
                             break
                     if tab_id_transcription is not None:
                          self.main_notebook.select(tab_id_transcription)
                     else: # Fallback to index 0 if dynamic lookup fails
                          print("Could not dynamically find transcription tab, selecting index 0.")
                          self.main_notebook.select(0)

                 except tk.TclError:
                      print("Could not switch to transcription tab (TclError).")
                 except Exception as e:
                     print(f"Could not switch to transcription tab (Error: {e}).")

        else:
             print(f"Invalid file path received from recorder: {file_path}")

    def start_transcription(self):
        input_file = self.file_path.get()
        model_type = self.model_var.get()
        language = self.get_language_code(self.transcription_language_var.get())
        use_gpu = self.use_gpu_var.get()

        if not input_file or not os.path.isfile(input_file):
            messagebox.showerror(self.translate("error_title"), self.translate("error_no_file"))
            return

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.console_output_delete_all()
        self.result_text_clear()

        self.transcriber.start_transcription_async(input_file, model_type, language, use_gpu, self.system_type)

    def stop_transcription(self):
        if hasattr(self.transcriber, 'request_stop'):
             self.transcriber.request_stop()
             self.console_output_insert(self.translate("stop_requested_info"))
             self.status_var.set(self.translate("status_stopping"))
             self.current_task.set(self.translate("progress_label_interrupted"))
             if hasattr(self, 'stop_button') and self.stop_button.winfo_exists():
                 self.stop_button.config(state=tk.DISABLED)

    def copy_to_clipboard(self):
        try:
            text_to_copy = self.result_text.get("1.0", tk.END).strip()
            if not text_to_copy:
                 messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save"))
                 return

            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            self.root.update()
            messagebox.showinfo(self.translate("copied_title"), self.translate("copied_message"))
        except tk.TclError:
             messagebox.showerror(self.translate("error_title"), "Error copying text.")

    def save_transcription(self):
        text = self.result_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save"))
            return

        original_filename = os.path.basename(self.file_path.get())
        suggested_filename = os.path.splitext(original_filename)[0] + "_transcription.txt" if original_filename else self.translate('tab_transcription').lower() + ".txt"

        file = filedialog.asksaveasfilename(
            title=self.translate("save_button"),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=suggested_filename,
            initialdir=os.path.dirname(self.file_path.get()) if self.file_path.get() else "/"
        )

        if file:
            try:
                with open(file, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo(self.translate("saved_title"), self.translate("saved_message").format(file=file))
            except Exception as e:
                messagebox.showerror(self.translate("error_title"), self.translate("error_saving").format(error=str(e)))

    def console_output_insert(self, text):
        try:
             if hasattr(self, 'console_output') and self.console_output.winfo_exists():
                 if isinstance(sys.stdout, ConsoleOutput):
                     sys.stdout.write(text)
                 else:
                     self.console_output.after_idle(lambda t=text: (
                         self.console_output.insert(tk.END, t),
                         self.console_output.see(tk.END)
                     ))
             else:
                 print(f"GUI Console Log: {text.strip()}")
        except Exception as e:
             print(f"Error inserting to console: {e}\nMessage: {text.strip()}")

    def console_output_delete_all(self):
        try:
            if hasattr(self, 'console_output') and self.console_output.winfo_exists():
                self.console_output.after_idle(lambda: self.console_output.delete(1.0, tk.END))
        except tk.TclError:
             pass

    def result_text_set(self, text):
        try:
            if hasattr(self, 'result_text') and self.result_text.winfo_exists():
                 self.result_text.after_idle(lambda t=text: (
                     self.result_text.delete(1.0, tk.END),
                     self.result_text.insert(tk.END, t),
                     self.result_text.see(tk.END)
                 ))
        except tk.TclError:
             pass

    def result_text_clear(self):
         try:
            if hasattr(self, 'result_text') and self.result_text.winfo_exists():
                 self.result_text.after_idle(lambda: self.result_text.delete(1.0, tk.END))
         except tk.TclError:
             pass

    def update_progress_state(self, task_key=None, status_key=None, progress_mode="start"):
        task_text = self.translate(task_key) if task_key else self.current_task.get()
        status_text = self.translate(status_key) if status_key else self.status_var.get()

        def _update():
            try:
                if not self.root.winfo_exists(): return
                self.current_task.set(task_text)
                self.status_var.set(status_text)
                if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                    if progress_mode == "start" or progress_mode == "indeterminate":
                        self.progress_bar.config(mode="indeterminate")
                        self.progress_bar.start(10)
                    elif progress_mode == "stop":
                        self.progress_bar.stop()
                        self.progress_bar.config(mode="determinate")
                        self.progress_var.set(0)
                    elif progress_mode == "determinate":
                         self.progress_bar.config(mode="determinate")
            except tk.TclError:
                 print(f"Status Update Failed (TclError): Task={task_text}, Status={status_text}")
            except Exception as e:
                 print(f"Status Update Failed (Other Error): {e} - Task={task_text}, Status={status_text}")

        self.root.after_idle(_update)

    def finalize_ui_state(self, success=True, interrupted=False):
        def _finalize():
            try:
                if not self.root.winfo_exists(): return
                if hasattr(self, 'start_button') and self.start_button.winfo_exists():
                    self.start_button.config(state=tk.NORMAL)
                if hasattr(self, 'stop_button') and self.stop_button.winfo_exists():
                    self.stop_button.config(state=tk.DISABLED)
                if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                     self.progress_bar.stop()
                     self.progress_var.set(0)

                if interrupted:
                    final_status_key = "status_interrupted"
                    final_task_key = "progress_label_interrupted"
                elif success:
                    final_status_key = "status_completed"
                    final_task_key = "progress_label_completed"
                else:
                    final_status_key = "status_error"
                    final_task_key = "progress_label_error"

                self.status_var.set(self.translate(final_status_key))
                self.current_task.set(self.translate(final_task_key))

            except tk.TclError:
                 print("Failed to finalize UI state (TclError).")
            except Exception as e:
                 print(f"Failed to finalize UI state (Other Error): {e}")

        self.root.after_idle(_finalize)

    def on_closing(self):
        """Handle application closing."""
        if messagebox.askokcancel(self.translate("ask_close_title"), self.translate("ask_close_message")):
            print("Exiting application...")
            if hasattr(self, 'recorder_tab') and self.recorder_tab:
                 try:
                     self.recorder_tab.on_close()
                 except Exception as e:
                      print(f"Error during recorder tab cleanup: {e}")

            if hasattr(self.transcriber, 'request_stop'):
                 self.transcriber.request_stop()

            self.root.destroy()


# --- END OF MODIFIED FILE gui.py ---