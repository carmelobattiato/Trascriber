import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import io
import os
import sys
from tkinter.scrolledtext import ScrolledText
from datetime import timedelta
from transcriber import AudioTranscriber
import json # Used for potentially loading translations later if needed

class ConsoleOutput(io.StringIO):
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


class ModernTranscriptionApp:
    def __init__(self, root):
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

        # --- FIX 1: Set up the trace *after* widgets are created ---
        self.current_language.trace_add("write", self.change_language)

        self.update_ui_text() # Set initial text based on default language

        # Redirect stdout only after console widget exists
        # Ensure console_output exists before redirecting stdout
        if hasattr(self, 'console_output') and self.console_output:
             sys.stdout = ConsoleOutput(self.console_output)
             print(self.translate("welcome_message")) # Initial message
        else:
             print("WARNING: Console output widget not found, stdout not redirected.")


    def setup_translations(self):
        self.translations = {
            "it": {
                "window_title": "AudioScript - Trascrizione Audio Professionale",
                "app_title": "AudioScript",
                "app_subtitle": "Trascrizione professionale di file audio",
                "select_audio_frame": "Seleziona File Audio",
                "wav_file_label": "File WAV:",
                "browse_button": "Sfoglia...",
                "options_frame": "Opzioni",
                "model_label": "Modello:",
                "language_label": "Lingua (Trascrizione):",
                "acceleration_label": "Accelerazione:",
                "use_gpu_checkbox": "Usa GPU (se disponibile)",
                "gpu_tooltip_mac": "Seleziona per usare l'accelerazione hardware:\n- Mac: Usa Metal Performance Shaders (MPS)",
                "gpu_tooltip_windows": "Seleziona per usare l'accelerazione hardware:\n- Windows: Usa DirectML per GPU integrate",
                "start_button": "✓ Avvia Trascrizione",
                "stop_button": "⨯ Interrompi",
                "copy_button": "📋 Copia negli Appunti",
                "save_button": "💾 Salva Trascrizione",
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
                "status_ready": "Pronto",
                "status_stopping": "Interruzione in corso...",
                "status_loading_model": "Caricamento modello...",
                "status_transcribing": "Trascrizione in corso...",
                "status_completed": "Trascrizione completata",
                "status_error": "Errore durante la trascrizione",
                "status_interrupted": "Interrotto dall'utente",
                "error_title": "Errore",
                "error_no_file": "Seleziona un file WAV!",
                "error_saving": "Errore durante il salvataggio: {error}",
                "error_reading_info": "Errore nel leggere le informazioni del file: {error}",
                "error_reading_duration": "Errore nel leggere la durata del file: {error}",
                "error_gpu_init": "Errore nell'inizializzazione GPU: {error}, usando CPU",
                "error_model_load": "Errore nel caricamento del modello su {device}: {error}, riprovo con CPU",
                "warning_title": "Attenzione",
                "warning_no_text_to_save": "Non c'è testo da salvare!",
                "info_title": "Informazione",
                "copied_title": "Copiato",
                "copied_message": "Trascrizione copiata negli appunti!",
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
            },
            "en": {
                "window_title": "AudioScript - Professional Audio Transcription",
                "app_title": "AudioScript",
                "app_subtitle": "Professional transcription of audio files",
                "select_audio_frame": "Select Audio File",
                "wav_file_label": "WAV File:",
                "browse_button": "Browse...",
                "options_frame": "Options",
                "model_label": "Model:",
                "language_label": "Language (Transcription):",
                "acceleration_label": "Acceleration:",
                "use_gpu_checkbox": "Use GPU (if available)",
                "gpu_tooltip_mac": "Select to use hardware acceleration:\n- Mac: Use Metal Performance Shaders (MPS)",
                "gpu_tooltip_windows": "Select to use hardware acceleration:\n- Windows: Use DirectML for integrated GPUs",
                "start_button": "✓ Start Transcription",
                "stop_button": "⨯ Stop",
                "copy_button": "📋 Copy to Clipboard",
                "save_button": "💾 Save Transcription",
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
                "status_ready": "Ready",
                "status_stopping": "Stopping...",
                "status_loading_model": "Loading model...",
                "status_transcribing": "Transcribing...",
                "status_completed": "Transcription completed",
                "status_error": "Error during transcription",
                "status_interrupted": "Interrupted by user",
                "error_title": "Error",
                "error_no_file": "Please select a WAV file!",
                "error_saving": "Error while saving: {error}",
                "error_reading_info": "Error reading file information: {error}",
                "error_reading_duration": "Error reading file duration: {error}",
                "error_gpu_init": "Error initializing GPU: {error}, using CPU",
                "error_model_load": "Error loading model on {device}: {error}, retrying with CPU",
                "warning_title": "Warning",
                "warning_no_text_to_save": "There is no text to save!",
                "info_title": "Information",
                "copied_title": "Copied",
                "copied_message": "Transcription copied to clipboard!",
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
            },
            "fr": {
                "window_title": "AudioScript - Transcription Audio Professionnelle",
                "app_title": "AudioScript",
                "app_subtitle": "Transcription professionnelle de fichiers audio",
                "select_audio_frame": "Sélectionner le Fichier Audio",
                "wav_file_label": "Fichier WAV :",
                "browse_button": "Parcourir...",
                "options_frame": "Options",
                "model_label": "Modèle :",
                "language_label": "Langue (Transcription) :",
                "acceleration_label": "Accélération :",
                "use_gpu_checkbox": "Utiliser le GPU (si disponible)",
                "gpu_tooltip_mac": "Sélectionnez pour utiliser l'accélération matérielle :\n- Mac : Utiliser Metal Performance Shaders (MPS)",
                "gpu_tooltip_windows": "Sélectionnez pour utiliser l'accélération matérielle :\n- Windows : Utiliser DirectML pour les GPU intégrés",
                "start_button": "✓ Démarrer la Transcription",
                "stop_button": "⨯ Arrêter",
                "copy_button": "📋 Copier dans le Presse-papiers",
                "save_button": "💾 Enregistrer la Transcription",
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
                "status_ready": "Prêt",
                "status_stopping": "Arrêt en cours...",
                "status_loading_model": "Chargement du modèle...",
                "status_transcribing": "Transcription...",
                "status_completed": "Transcription terminée",
                "status_error": "Erreur pendant la transcription",
                "status_interrupted": "Interrompu par l'utilisateur",
                "error_title": "Erreur",
                "error_no_file": "Veuillez sélectionner un fichier WAV !",
                "error_saving": "Erreur lors de l'enregistrement : {error}",
                "error_reading_info": "Erreur lors de la lecture des informations du fichier : {error}",
                "error_reading_duration": "Erreur lors de la lecture de la durée du fichier : {error}",
                "error_gpu_init": "Erreur d'initialisation du GPU : {error}, utilisation du CPU",
                "error_model_load": "Erreur de chargement du modèle sur {device} : {error}, nouvel essai avec le CPU",
                "warning_title": "Attention",
                "warning_no_text_to_save": "Il n'y a pas de texte à enregistrer !",
                "info_title": "Information",
                "copied_title": "Copié",
                "copied_message": "Transcription copiée dans le presse-papiers !",
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
            },
            "zh": {
                "window_title": "AudioScript - 专业音频转录",
                "app_title": "AudioScript",
                "app_subtitle": "专业转录音频文件",
                "select_audio_frame": "选择音频文件",
                "wav_file_label": "WAV 文件:",
                "browse_button": "浏览...",
                "options_frame": "选项",
                "model_label": "模型:",
                "language_label": "语言 (转录):",
                "acceleration_label": "加速:",
                "use_gpu_checkbox": "使用 GPU (如果可用)",
                "gpu_tooltip_mac": "选择以使用硬件加速:\n- Mac: 使用 Metal Performance Shaders (MPS)",
                "gpu_tooltip_windows": "选择以使用硬件加速:\n- Windows: 使用 DirectML (集成 GPU)",
                "start_button": "✓ 开始转录",
                "stop_button": "⨯ 停止",
                "copy_button": "📋 复制到剪贴板",
                "save_button": "💾 保存转录",
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
                "status_ready": "准备就绪",
                "status_stopping": "正在停止...",
                "status_loading_model": "正在加载模型...",
                "status_transcribing": "正在转录...",
                "status_completed": "转录完成",
                "status_error": "转录过程中出错",
                "status_interrupted": "用户已中断",
                "error_title": "错误",
                "error_no_file": "请选择一个 WAV 文件!",
                "error_saving": "保存时出错: {error}",
                "error_reading_info": "读取文件信息时出错: {error}",
                "error_reading_duration": "读取文件持续时间时出错: {error}",
                "error_gpu_init": "初始化 GPU 时出错: {error}, 使用 CPU",
                "error_model_load": "在 {device} 上加载模型时出错: {error}, 使用 CPU 重试",
                "warning_title": "警告",
                "warning_no_text_to_save": "没有要保存的文本!",
                "info_title": "信息",
                "copied_title": "已复制",
                "copied_message": "转录已复制到剪贴板!",
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
        lang_code = self.current_language.get()
        # Fallback to English if the key or language is missing
        return self.translations.get(lang_code, self.translations['en']).get(key, self.translations['en'].get(key, f"<{key}>"))

    def setup_ui_styles(self):
        self.style = ttk.Style()
        try:
            # 'clam' theme is generally available and looks decent
            self.style.theme_use('clam')
        except tk.TclError:
            # Fallback if 'clam' isn't available (less likely but possible)
             available_themes = self.style.theme_names()
             print(f"Theme 'clam' not found. Available themes: {available_themes}")
             if available_themes:
                 self.style.theme_use(available_themes[0]) # Use the first available theme
             # else: styles might look very basic


        self.primary_color = "#3498db"
        self.secondary_color = "#2980b9"
        self.bg_color = "#f5f5f5"
        self.text_color = "#2c3e50"
        self.success_color = "#2ecc71"
        self.warning_color = "#e74c3c"

        self.root.configure(bg=self.bg_color)

        # Define font tuples - consider adding fallback fonts, especially for CJK
        default_font = ("Segoe UI", 10)
        bold_font = ("Segoe UI", 10, "bold")
        heading_font = ("Segoe UI", 14, "bold")
        console_font = ("Consolas", 10) # Consolas is good for monospaced/code


        self.style.configure("Card.TFrame", background=self.bg_color, relief="raised", borderwidth=1)
        self.style.configure("Primary.TButton",
                           background=self.primary_color,
                           foreground="white",
                           padding=10,
                           font=bold_font)
        self.style.map("Primary.TButton",
                      background=[("active", self.secondary_color), ("disabled", "#95a5a6")])
        self.style.configure("Action.TButton",
                           background=self.secondary_color,
                           foreground="white",
                           padding=8,
                           font=("Segoe UI", 9)) # Slightly smaller font for action buttons
        self.style.configure("TLabel",
                           background=self.bg_color,
                           foreground=self.text_color,
                           font=default_font)
        self.style.configure("Heading.TLabel",
                           background=self.bg_color,
                           foreground=self.text_color,
                           font=heading_font)
        self.style.configure("Status.TLabel",
                           background="#ecf0f1",
                           foreground=self.text_color,
                           padding=5,
                           relief="sunken",
                           font=default_font)
        self.style.configure("TProgressbar",
                           background=self.primary_color,
                           troughcolor="#d1d1d1",
                           thickness=10)
        self.style.configure("TCombobox",
                           padding=5,
                           font=default_font)
        # Ensure ScrolledText widgets use appropriate fonts (set directly on the widget)

    def create_widgets(self):
        # --- Variables ---
        self.file_path = tk.StringVar()
        self.model_var = tk.StringVar(value="large")
        self.transcription_language_var = tk.StringVar(value="italiano") # For whisper
        # Status/Progress vars initialized in __init__ using translate

        self.progress_var = tk.DoubleVar(value=0)
        self.use_gpu_var = tk.BooleanVar(value=False)

        # --- Main Layout ---
        self.main_frame = ttk.Frame(self.root, padding="20", style="Card.TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.main_frame.columnconfigure(0, weight=1) # Make content expand horizontally

        # --- Header ---
        self.header_frame = ttk.Frame(self.main_frame, style="Card.TFrame")
        # Use grid for better control within header
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.header_frame.columnconfigure(1, weight=1) # Allow subtitle to take space


        self.app_title_label = ttk.Label(self.header_frame, text="", style="Heading.TLabel") # Text set in update_ui_text
        self.app_title_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.app_subtitle_label = ttk.Label(self.header_frame, text="", style="TLabel") # Text set in update_ui_text
        self.app_subtitle_label.grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Language Selection Frame (aligned right)
        lang_select_frame = ttk.Frame(self.header_frame, style="Card.TFrame")
        lang_select_frame.grid(row=0, column=2, sticky="e")
        self.lang_select_label = ttk.Label(lang_select_frame, text="") # Text set in update_ui_text
        self.lang_select_label.pack(side=tk.LEFT, padx=(0, 5))
        # Define language options mapping display name to code
        self.lang_options = {"Italiano": "it", "English": "en", "Français": "fr", "中文": "zh"}
        self.language_selector = ttk.Combobox(lang_select_frame, textvariable=self.current_language,
                                              values=list(self.lang_options.keys()), state="readonly", width=10)
        # Set combobox to display name based on initial current_language var
        initial_lang_name = [name for name, code in self.lang_options.items() if code == self.current_language.get()][0]
        self.language_selector.set(initial_lang_name)
        # Bind selection event AFTER setting initial value and defining callback
        self.language_selector.bind("<<ComboboxSelected>>", self.on_language_select)
        self.language_selector.pack(side=tk.LEFT)

        # --- File Selection ---
        self.file_frame = ttk.LabelFrame(self.main_frame, text="", padding=10) # Text set in update_ui_text
        self.file_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.file_frame.columnconfigure(1, weight=1) # Make entry expand

        self.wav_file_label = ttk.Label(self.file_frame, text="") # Text set in update_ui_text
        self.wav_file_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path, width=60)
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.browse_button = ttk.Button(self.file_frame, text="", command=self.select_file, style="Action.TButton") # Text set in update_ui_text
        self.browse_button.grid(row=0, column=2, sticky=tk.E, padx=5, pady=5)

        # --- Options ---
        self.options_frame = ttk.LabelFrame(self.main_frame, text="", padding=10) # Text set in update_ui_text
        self.options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self.options_frame.columnconfigure(1, weight=0) # Adjust weights as needed
        self.options_frame.columnconfigure(2, weight=1) # Description takes remaining space


        # Model
        self.model_label = ttk.Label(self.options_frame, text="") # Text set in update_ui_text
        self.model_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        models = ["tiny", "base", "small", "medium", "large"] # Keep internal values consistent
        self.model_combobox = ttk.Combobox(self.options_frame, textvariable=self.model_var, values=models, state="readonly", width=15)
        self.model_combobox.grid(row=0, column=1, sticky=(tk.W), padx=5, pady=5)
        self.model_combobox.set("large") # Default internal value
        self.model_desc_label = ttk.Label(self.options_frame, textvariable=self.model_desc_var, anchor="w") # Uses tk var updated separately
        self.model_desc_label.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
        self.model_combobox.bind("<<ComboboxSelected>>", self.update_model_description)
        # self.update_model_description() # Called by update_ui_text initially

        # Transcription Language
        self.transcription_language_label = ttk.Label(self.options_frame, text="") # Text set in update_ui_text
        self.transcription_language_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        # Define languages for transcription - use the same names consistently
        self.transcription_languages = ["italiano", "inglese", "francese", "tedesco", "spagnolo", "giapponese", "cinese"]
        self.language_combobox = ttk.Combobox(self.options_frame, textvariable=self.transcription_language_var,
                                            values=self.transcription_languages, state="readonly", width=15)
        self.language_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.language_combobox.set("italiano") # Default transcription language

        # Acceleration
        self.acceleration_label = ttk.Label(self.options_frame, text="") # Text set in update_ui_text
        self.acceleration_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.gpu_check = ttk.Checkbutton(self.options_frame, text="", variable=self.use_gpu_var) # Text set in update_ui_text
        self.gpu_check.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5) # Span checkbox text
        self.gpu_check.bind("<Enter>", self.show_gpu_tooltip)
        self.gpu_tooltip = None # To store the tooltip window reference

        # --- Buttons ---
        buttons_frame = ttk.Frame(self.main_frame) # No Card style needed here
        buttons_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))

        self.start_button = ttk.Button(buttons_frame, text="", command=self.start_transcription, style="Primary.TButton") # Text set in update_ui_text
        self.start_button.pack(side=tk.LEFT, padx=5, pady=5) # Add pady

        self.stop_button = ttk.Button(buttons_frame, text="", command=self.stop_transcription, style="Action.TButton", state=tk.DISABLED) # Text set in update_ui_text
        self.stop_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Align copy/save buttons to the right
        action_buttons_right = ttk.Frame(buttons_frame)
        action_buttons_right.pack(side=tk.RIGHT)

        self.save_button = ttk.Button(action_buttons_right, text="", command=self.save_transcription, style="Action.TButton") # Text set in update_ui_text
        self.save_button.pack(side=tk.RIGHT, padx=5, pady=5)
        self.copy_button = ttk.Button(action_buttons_right, text="", command=self.copy_to_clipboard, style="Action.TButton") # Text set in update_ui_text
        self.copy_button.pack(side=tk.RIGHT, padx=5, pady=5)


        # --- Progress ---
        progress_frame = ttk.Frame(self.main_frame)
        progress_frame.grid(row=4, column=0, sticky="ew", pady=(0, 15))
        progress_frame.columnconfigure(0, weight=1)

        self.current_task_label = ttk.Label(progress_frame, textvariable=self.current_task, anchor="w") # Uses tk var
        self.current_task_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                         mode="indeterminate", length=100, style="TProgressbar")
        self.progress_bar.grid(row=1, column=0, sticky="ew")


        # --- Results Notebook ---
        self.results_notebook = ttk.Notebook(self.main_frame)
        self.results_notebook.grid(row=5, column=0, sticky="nsew", pady=(0, 15))
        self.main_frame.rowconfigure(5, weight=1) # Allow notebook to expand vertically


        # Transcription Tab
        transcription_frame = ttk.Frame(self.results_notebook, padding=10)
        transcription_frame.pack(fill=tk.BOTH, expand=True) # Use pack inside notebook frame
        transcription_frame.columnconfigure(0, weight=1)
        transcription_frame.rowconfigure(1, weight=1)
        # --- FIX 2: Remove the invalid 'key' argument ---
        self.results_notebook.add(transcription_frame, text="") # Text set in update_ui_text


        self.transcription_result_label = ttk.Label(transcription_frame, text="") # Text set in update_ui_text
        self.transcription_result_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Frame to hold scrolled text and allow padding/border
        result_text_frame = ttk.Frame(transcription_frame, borderwidth=1, relief="sunken")
        result_text_frame.grid(row=1, column=0, sticky="nsew")
        result_text_frame.rowconfigure(0, weight=1)
        result_text_frame.columnconfigure(0, weight=1)

        self.result_text = ScrolledText(result_text_frame, wrap=tk.WORD, width=80, height=15,
                                     font=("Segoe UI", 11), background="white", foreground=self.text_color,
                                     borderwidth=0, relief="flat") # Border handled by frame
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)


        # Console Tab
        console_frame = ttk.Frame(self.results_notebook, padding=10)
        console_frame.pack(fill=tk.BOTH, expand=True) # Use pack inside notebook frame
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(1, weight=1)
        # --- FIX 2: Remove the invalid 'key' argument ---
        self.results_notebook.add(console_frame, text="") # Text set in update_ui_text


        self.console_output_label = ttk.Label(console_frame, text="") # Text set in update_ui_text
        self.console_output_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        console_text_frame = ttk.Frame(console_frame, borderwidth=1, relief="sunken")
        console_text_frame.grid(row=1, column=0, sticky="nsew")
        console_text_frame.rowconfigure(0, weight=1)
        console_text_frame.columnconfigure(0, weight=1)

        self.console_output = ScrolledText(console_text_frame, wrap=tk.WORD, width=80, height=15,
                                     background="#f0f0f0", foreground="#333", # Darker grey text
                                     font=("Consolas", 10),
                                     borderwidth=0, relief="flat") # Border handled by frame
        self.console_output.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)


        # --- Status Bar ---
        # Use grid for the main frame content now
        # self.status_frame = ttk.Frame(self.root) -- Status bar outside main_frame
        # self.status_frame.grid(row=1, column=0, sticky="ew") # Adjust row if main_frame is row 0

        # Pack status bar at the bottom of the root window
        self.status_frame = ttk.Frame(self.root, style="Status.TFrame", borderwidth=1, relief='groove') # Add some style
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)


        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var, style="Status.TLabel", anchor="w") # Uses tk var
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)

    def update_ui_text(self):
        """Updates all UI elements with text based on the current language."""
        # Check if widgets have been created before trying to configure them
        if not hasattr(self, 'main_frame') or not self.main_frame.winfo_exists():
            # print("Widgets not ready for UI text update.")
            return # Should not happen if called correctly after create_widgets

        lang = self.current_language.get()
        self.root.title(self.translate("window_title"))

        self.app_title_label.config(text=self.translate("app_title"))
        self.app_subtitle_label.config(text=self.translate("app_subtitle"))
        self.lang_select_label.config(text=self.translate("language_select_label"))

        # Ensure file_frame exists before configuring
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
            self.update_model_description() # Update description in new language

        if hasattr(self, 'start_button'):
            self.start_button.config(text=self.translate("start_button"))
            self.stop_button.config(text=self.translate("stop_button"))
            self.copy_button.config(text=self.translate("copy_button"))
            self.save_button.config(text=self.translate("save_button"))

        # Update notebook tab texts using indices
        if hasattr(self, 'results_notebook'):
             try:
                 # Only update if tabs exist
                 if len(self.results_notebook.tabs()) >= 2:
                    self.results_notebook.tab(0, text=self.translate("tab_transcription"))
                    self.results_notebook.tab(1, text=self.translate("tab_console"))
             except tk.TclError as e:
                 # This might happen if the notebook somehow doesn't exist yet or tabs aren't ready
                 print(f"Error updating notebook tabs: {e}")

        if hasattr(self, 'transcription_result_label'):
            self.transcription_result_label.config(text=self.translate("transcription_result_label"))
        if hasattr(self, 'console_output_label'):
            self.console_output_label.config(text=self.translate("console_output_label"))

        # Update status bar text if it's currently showing a 'Ready' state in any language
        # (More robust check against different language 'Ready' strings)
        is_ready = False
        for code in self.translations:
            if self.status_var.get() == self.translations[code]['status_ready']:
                is_ready = True
                break
        if is_ready:
             self.status_var.set(self.translate("status_ready"))


    def on_language_select(self, event=None):
        """Callback when the language Combobox selection changes."""
        selected_display_name = self.language_selector.get()
        # Use self.lang_options defined in create_widgets
        new_lang_code = self.lang_options.get(selected_display_name, "en") # Default to English if lookup fails
        # Setting the variable will trigger the trace, which calls change_language -> update_ui_text
        self.current_language.set(new_lang_code)

    def change_language(self, *args):
        """Handles the language change triggered by the variable trace."""
        # print(f"Language changed to: {self.current_language.get()}. Updating UI text.") # Debug print
        self.update_ui_text()

    def update_model_description(self, event=None):
        # Ensure model_combobox exists
        if hasattr(self, 'model_combobox'):
             selected_model = self.model_combobox.get()
             desc_key = self.model_descriptions.get(selected_model, "model_desc_large") # Default desc key
             self.model_desc_var.set(self.translate(desc_key))

    def show_gpu_tooltip(self, event):
        # Destroy previous tooltip if it exists
        if self.gpu_tooltip and self.gpu_tooltip.winfo_exists():
            self.gpu_tooltip.destroy()
        self.gpu_tooltip = None

        # Create a new tooltip window
        self.gpu_tooltip = tk.Toplevel(self.root)
        self.gpu_tooltip.wm_overrideredirect(True)
        # Position tooltip near the cursor
        x = event.x_root + 15
        y = event.y_root + 10
        self.gpu_tooltip.wm_geometry(f"+{x}+{y}")

        # Determine the message based on the OS
        if self.system_type == "mac":
            msg = self.translate("gpu_tooltip_mac")
        else: # Assume Windows or other (defaults to Windows message)
             msg = self.translate("gpu_tooltip_windows")

        # Create and pack the label inside the tooltip
        label = ttk.Label(self.gpu_tooltip, text=msg, justify=tk.LEFT,
                          background="#ffffe0", relief="solid", borderwidth=1, padding=5,
                          font=("Segoe UI", 9)) # Use a standard font size
        label.pack(ipadx=1, ipady=1)

        # Schedule the tooltip to disappear after 5 seconds
        self._tooltip_after_id = self.root.after(5000, self._destroy_tooltip)

        # Bind mouse leaving the widget to destroy tooltip immediately
        self.gpu_check.bind("<Leave>", self._on_leave_tooltip)

    def _destroy_tooltip(self):
        """Safely destroys the tooltip window and cancels the timer."""
        if hasattr(self, '_tooltip_after_id') and self._tooltip_after_id:
            self.root.after_cancel(self._tooltip_after_id)
            self._tooltip_after_id = None
        if self.gpu_tooltip and self.gpu_tooltip.winfo_exists():
            self.gpu_tooltip.destroy()
        self.gpu_tooltip = None
         # Unbind the leave event if the tooltip is destroyed
        if hasattr(self, 'gpu_check'):
            try: # Check if widget still exists
                 if self.gpu_check.winfo_exists():
                     self.gpu_check.unbind("<Leave>")
            except tk.TclError:
                 pass # Widget likely destroyed

    def _on_leave_tooltip(self, event=None):
        """Called when the mouse leaves the widget triggering the tooltip."""
        self._destroy_tooltip()


    def get_language_code(self, language_name):
        # This maps display names (used in combobox) to whisper language codes
        # Ensure keys match the values in self.transcription_languages
        language_map = {
            "italiano": "italian", "inglese": "english", "francese": "french",
            "tedesco": "german", "spagnolo": "spanish", "giapponese": "japanese",
            "cinese": "chinese"
        }
        # Default to italian if mapping not found or language_name is unexpected
        return language_map.get(language_name.lower(), "italian")

    def select_file(self):
        # Use initialdir and title for better user experience
        initial_dir = os.path.dirname(self.file_path.get()) if self.file_path.get() else "/"
        file = filedialog.askopenfilename(
            title=self.translate("select_audio_frame"), # Use translated title
            initialdir=initial_dir,
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")] # Allow all for flexibility? Or restrict?
        )
        if file:
            self.file_path.set(file)
            # Attempt to get audio info and display it
            file_info = self.transcriber.get_audio_info(file)
            if file_info:
                duration, channels, rate = file_info
                # Use the utility function for formatting duration
                from utils import format_duration
                duration_str = format_duration(duration)
                filename = os.path.basename(file)
                info_msg = self.translate("selected_file_info").format(
                    filename=filename, duration=duration_str, channels=channels, rate=rate
                )
                self.console_output_insert(info_msg)
            else:
                 # Info couldn't be read, transcriber likely logged error
                 self.console_output_insert(f"Could not read info for: {os.path.basename(file)}\n")


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
        self.result_text_clear() # Use safe clear method

        # Pass the current UI language to the transcriber if needed for its messages
        # (Currently handled by GUI calling translate, but could be passed if transcriber generated UI messages directly)
        self.transcriber.start_transcription_async(input_file, model_type, language, use_gpu, self.system_type)

    def stop_transcription(self):
        if hasattr(self.transcriber, 'request_stop'):
             self.transcriber.request_stop()
             self.console_output_insert(self.translate("stop_requested_info"))
             self.status_var.set(self.translate("status_stopping"))
             self.current_task.set(self.translate("progress_label_interrupted"))
             # Disable stop button immediately to prevent multiple clicks
             self.stop_button.config(state=tk.DISABLED)

    def copy_to_clipboard(self):
        try:
            text_to_copy = self.result_text.get("1.0", tk.END).strip()
            if not text_to_copy:
                 messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save"))
                 return

            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            self.root.update() # Needed for clipboard on some systems
            messagebox.showinfo(self.translate("copied_title"), self.translate("copied_message"))
        except tk.TclError:
             # This might happen if the text widget was destroyed unexpectedly
             messagebox.showerror(self.translate("error_title"), "Error copying text.")


    def save_transcription(self):
        text = self.result_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning(self.translate("warning_title"), self.translate("warning_no_text_to_save"))
            return

        # Suggest a filename based on the original audio file
        original_filename = os.path.basename(self.file_path.get())
        suggested_filename = os.path.splitext(original_filename)[0] + "_transcription.txt" if original_filename else self.translate('tab_transcription').lower() + ".txt"


        file = filedialog.asksaveasfilename(
            title=self.translate("save_button"), # Use translated title
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

    # --- Safe GUI Update Helper Methods ---

    def _safe_widget_call(self, widget, method, *args, **kwargs):
        """Generic helper to call a widget method safely using after_idle."""
        if hasattr(self, widget_name) and getattr(self, widget_name):
            widget = getattr(self, widget_name)
            if widget.winfo_exists():
                 self.root.after_idle(lambda w=widget, m=method, a=args, k=kwargs: getattr(w, m)(*a, **k))
            # else:
                 # print(f"Warning: Widget '{widget_name}' does not exist for method '{method}'.") # Debug
        # else:
             # print(f"Warning: Attribute '{widget_name}' not found.") # Debug


    def console_output_insert(self, text):
        """Safely inserts text into the console output widget using after_idle."""
        try:
             if hasattr(self, 'console_output') and self.console_output.winfo_exists():
                 # Use the ConsoleOutput's write method which handles scheduling via after_idle
                 if isinstance(sys.stdout, ConsoleOutput):
                     sys.stdout.write(text)
                 else: # Fallback if stdout redirection failed
                     self.console_output.after_idle(lambda t=text: (
                         self.console_output.insert(tk.END, t),
                         self.console_output.see(tk.END)
                     ))
             else: # Log to standard print if GUI console isn't available
                 print(f"GUI Console Log: {text.strip()}")
        except Exception as e:
             print(f"Error inserting to console: {e}\nMessage: {text.strip()}")


    def console_output_delete_all(self):
        """Safely deletes all text from the console output widget using after_idle."""
        try:
            if hasattr(self, 'console_output') and self.console_output.winfo_exists():
                self.console_output.after_idle(lambda: self.console_output.delete(1.0, tk.END))
        except tk.TclError:
             pass # Ignore if widget doesn't exist when callback runs

    def result_text_set(self, text):
        """Safely sets the text of the result widget using after_idle."""
        try:
            if hasattr(self, 'result_text') and self.result_text.winfo_exists():
                 self.result_text.after_idle(lambda t=text: (
                     self.result_text.delete(1.0, tk.END),
                     self.result_text.insert(tk.END, t),
                     self.result_text.see(tk.END)
                 ))
        except tk.TclError:
             pass # Ignore if widget doesn't exist

    def result_text_clear(self):
         """Safely clears the result text widget."""
         try:
            if hasattr(self, 'result_text') and self.result_text.winfo_exists():
                 self.result_text.after_idle(lambda: self.result_text.delete(1.0, tk.END))
         except tk.TclError:
             pass

    def update_progress_state(self, task_key=None, status_key=None, progress_mode="start"):
        """Safely updates status, current task, and progress bar state using after_idle."""
        task_text = self.translate(task_key) if task_key else self.current_task.get() # Keep existing if None
        status_text = self.translate(status_key) if status_key else self.status_var.get() # Keep existing if None

        def _update():
            try:
                # Check root window exists
                if not self.root.winfo_exists(): return

                # Update StringVars directly
                self.current_task.set(task_text)
                self.status_var.set(status_text)

                # Update Progressbar state
                if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                    if progress_mode == "start" or progress_mode == "indeterminate":
                        self.progress_bar.config(mode="indeterminate")
                        self.progress_bar.start(10)
                    elif progress_mode == "stop":
                        self.progress_bar.stop()
                        self.progress_bar.config(mode="determinate") # Switch back for potential future use
                        self.progress_var.set(0) # Reset visual progress
                    elif progress_mode == "determinate":
                         self.progress_bar.config(mode="determinate")
                    # Add handling for setting specific progress value if needed later
                    # elif progress_mode == "set_value" and 'value' in kwargs:
                    #     self.progress_bar.config(mode="determinate")
                    #     self.progress_var.set(kwargs['value'])

            except tk.TclError:
                 print(f"Status Update Failed (TclError): Task={task_text}, Status={status_text}") # Debug
            except Exception as e:
                 print(f"Status Update Failed (Other Error): {e} - Task={task_text}, Status={status_text}") # Debug


        # Schedule the update
        self.root.after_idle(_update)


    def finalize_ui_state(self, success=True, interrupted=False):
        """Safely resets buttons and progress bar after transcription ends using after_idle."""
        def _finalize():
            try:
                 # Check root window exists
                if not self.root.winfo_exists(): return

                # Update button states
                if hasattr(self, 'start_button') and self.start_button.winfo_exists():
                    self.start_button.config(state=tk.NORMAL)
                if hasattr(self, 'stop_button') and self.stop_button.winfo_exists():
                    self.stop_button.config(state=tk.DISABLED)

                # Stop progress bar and set final status/task message
                if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                     self.progress_bar.stop()
                     self.progress_var.set(0)

                if interrupted:
                    final_status_key = "status_interrupted"
                    final_task_key = "progress_label_interrupted"
                elif success:
                    final_status_key = "status_completed"
                    final_task_key = "progress_label_completed"
                else: # Error case
                    final_status_key = "status_error"
                    final_task_key = "progress_label_error"

                self.status_var.set(self.translate(final_status_key))
                self.current_task.set(self.translate(final_task_key))

            except tk.TclError:
                 print("Failed to finalize UI state (TclError).") # Debug
            except Exception as e:
                 print(f"Failed to finalize UI state (Other Error): {e}") # Debug

        # Schedule the finalization
        self.root.after_idle(_finalize)