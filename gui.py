import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import io
import os
import sys
from tkinter.scrolledtext import ScrolledText
from datetime import timedelta
from transcriber import AudioTranscriber

class ConsoleOutput(io.StringIO):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)
        self.text_widget.update_idletasks()

class ModernTranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AudioScript - Trascrizione Audio Professionale")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        self.transcriber = AudioTranscriber(self)
        self.system_type = "mac" if sys.platform == "darwin" else "windows"
        
        self.setup_ui_styles()
        self.create_widgets()
        
        sys.stdout = ConsoleOutput(self.console_output)
    
    def setup_ui_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.primary_color = "#3498db"
        self.secondary_color = "#2980b9"
        self.bg_color = "#f5f5f5"
        self.text_color = "#2c3e50"
        self.success_color = "#2ecc71"
        self.warning_color = "#e74c3c"
        
        self.root.configure(bg=self.bg_color)
        
        self.style.configure("Card.TFrame", background=self.bg_color, relief="raised", borderwidth=1)
        self.style.configure("Primary.TButton", 
                           background=self.primary_color, 
                           foreground="white", 
                           padding=10, 
                           font=("Segoe UI", 10, "bold"))
        self.style.map("Primary.TButton",
                      background=[("active", self.secondary_color), ("disabled", "#95a5a6")])
        self.style.configure("Action.TButton", 
                           background=self.secondary_color, 
                           foreground="white", 
                           padding=8, 
                           font=("Segoe UI", 9))
        self.style.configure("TLabel", 
                           background=self.bg_color, 
                           foreground=self.text_color, 
                           font=("Segoe UI", 10))
        self.style.configure("Heading.TLabel", 
                           background=self.bg_color, 
                           foreground=self.text_color, 
                           font=("Segoe UI", 14, "bold"))
        self.style.configure("Status.TLabel", 
                           background="#ecf0f1", 
                           foreground=self.text_color, 
                           padding=5, 
                           relief="sunken")
        self.style.configure("TProgressbar", 
                           background=self.primary_color, 
                           troughcolor="#d1d1d1", 
                           thickness=10)
        self.style.configure("TCombobox", 
                           padding=5,
                           font=("Segoe UI", 10))
    
    def create_widgets(self):
        self.file_path = tk.StringVar()
        self.model_var = tk.StringVar(value="large")
        self.language_var = tk.StringVar(value="italiano")
        self.status_var = tk.StringVar(value="Pronto")
        self.progress_var = tk.DoubleVar(value=0)
        self.current_task = tk.StringVar(value="")
        self.model_desc_var = tk.StringVar(value="Massima precisione")
        self.use_gpu_var = tk.BooleanVar(value=False)
        
        main_frame = ttk.Frame(self.root, padding="20", style="Card.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        header_frame = ttk.Frame(main_frame, style="Card.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(header_frame, text="AudioScript", style="Heading.TLabel").pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Trascrizione professionale di file audio", style="TLabel").pack(side=tk.LEFT, padx=20)
        
        file_frame = ttk.LabelFrame(main_frame, text="Seleziona File Audio", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(file_frame, text="File WAV:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.file_path, width=60).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(file_frame, text="Sfoglia...", command=self.select_file, style="Action.TButton").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        options_frame = ttk.LabelFrame(main_frame, text="Opzioni", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(options_frame, text="Modello:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        models = [
            "tiny - Veloce, precisione base",
            "base - Buon compromesso",
            "small - Buona qualità",
            "medium - Alta qualità",
            "large - Massima precisione"
        ]
        
        self.model_combobox = ttk.Combobox(options_frame, textvariable=self.model_var, values=[m.split(" - ")[0] for m in models], state="readonly", width=20)
        self.model_combobox.grid(row=0, column=1, sticky=(tk.W), padx=5, pady=5)
        self.model_combobox.set("large")
        
        ttk.Label(options_frame, textvariable=self.model_desc_var).grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        def update_description(event):
            selected = self.model_combobox.get()
            for model in models:
                if model.startswith(selected):
                    self.model_desc_var.set(model.split(" - ")[1])
                    break
        
        self.model_combobox.bind("<<ComboboxSelected>>", update_description)
        
        ttk.Label(options_frame, text="Lingua:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        languages = ["italiano", "inglese", "francese", "tedesco", "spagnolo", "giapponese", "cinese"]
        self.language_combobox = ttk.Combobox(options_frame, textvariable=self.language_var, 
                                            values=languages, state="readonly", width=20)
        self.language_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(options_frame, text="Accelerazione:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        gpu_check = ttk.Checkbutton(options_frame, text="Usa GPU (se disponibile)", 
                                   variable=self.use_gpu_var)
        gpu_check.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        def show_gpu_tooltip(event):
            tip = tk.Toplevel(self.root)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{event.x_root+15}+{event.y_root+10}")
            msg = ("Seleziona per usare l'accelerazione hardware:\n"
                  "- Mac: Usa Metal Performance Shaders (MPS)\n"
                  "- Windows: Usa DirectML per GPU integrate")
            label = ttk.Label(tip, text=msg, background="#ffffe0", relief="solid", padding=5)
            label.pack()
            tip.after(5000, tip.destroy)
        
        gpu_check.bind("<Enter>", show_gpu_tooltip)
        
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.start_button = ttk.Button(buttons_frame, text="✓ Avvia Trascrizione", 
                                    command=self.start_transcription, style="Primary.TButton")
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(buttons_frame, text="⨯ Interrompi", 
                                   command=self.stop_transcription, style="Action.TButton", state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.copy_button = ttk.Button(buttons_frame, text="📋 Copia negli Appunti", 
                                   command=self.copy_to_clipboard, style="Action.TButton")
        self.copy_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(buttons_frame, text="💾 Salva Trascrizione", 
                                   command=self.save_transcription, style="Action.TButton")
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(progress_frame, textvariable=self.current_task).pack(side=tk.TOP, anchor=tk.W, pady=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                         mode="indeterminate", length=100, style="TProgressbar")
        self.progress_bar.pack(fill=tk.X)
        
        results_notebook = ttk.Notebook(main_frame)
        results_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        transcription_frame = ttk.Frame(results_notebook, padding=10)
        results_notebook.add(transcription_frame, text="Trascrizione")
        
        ttk.Label(transcription_frame, text="Risultato della trascrizione:").pack(anchor=tk.W, pady=(0, 5))
        
        result_frame = ttk.Frame(transcription_frame)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = ScrolledText(result_frame, wrap=tk.WORD, width=80, height=15, 
                                     font=("Segoe UI", 11), background="white", borderwidth=1, relief="solid")
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        console_frame = ttk.Frame(results_notebook, padding=10)
        results_notebook.add(console_frame, text="Console e Log")
        
        ttk.Label(console_frame, text="Output del processo:").pack(anchor=tk.W, pady=(0, 5))
        
        console_scroll_frame = ttk.Frame(console_frame)
        console_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        self.console_output = ScrolledText(console_scroll_frame, wrap=tk.WORD, width=80, height=15, 
                                     background="#f0f0f0", font=("Consolas", 10))
        self.console_output.pack(fill=tk.BOTH, expand=True)
        
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def get_language_code(self, language_name):
        language_map = {
            "italiano": "italian",
            "inglese": "english",
            "francese": "french",
            "tedesco": "german",
            "spagnolo": "spanish",
            "giapponese": "japanese",
            "cinese": "chinese"
        }
        return language_map.get(language_name.lower(), "italian")
    
    def select_file(self):
        file = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if file:
            self.file_path.set(file)
            file_info = self.transcriber.get_audio_info(file)
            if file_info:
                duration, channels, rate = file_info
                duration_str = str(timedelta(seconds=int(duration)))
                self.console_output.insert(tk.END, f"File selezionato: {os.path.basename(file)}\n")
                self.console_output.insert(tk.END, f"Durata: {duration_str}, Canali: {channels}, Sample rate: {rate} Hz\n")
                self.console_output.see(tk.END)
    
    def start_transcription(self):
        input_file = self.file_path.get()
        model_type = self.model_var.get()
        language = self.get_language_code(self.language_var.get())
        use_gpu = self.use_gpu_var.get()
        
        if not input_file:
            messagebox.showerror("Errore", "Seleziona un file WAV!")
            return
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.console_output.delete(1.0, tk.END)
        self.result_text.delete(1.0, tk.END)
        
        self.transcriber.start_transcription_async(input_file, model_type, language, use_gpu, self.system_type)
    
    def stop_transcription(self):
        self.transcriber.request_stop()
        self.console_output.insert(tk.END, "Interruzione richiesta. Attendere il completamento dell'operazione in corso...\n")
        self.console_output.see(tk.END)
        self.status_var.set("Interruzione in corso...")
        self.current_task.set("Interruzione richiesta")
    
    def copy_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result_text.get("1.0", tk.END))
        self.root.update()
        messagebox.showinfo("Copiato", "Trascrizione copiata negli appunti!")
    
    def save_transcription(self):
        text = self.result_text.get("1.0", tk.END)
        if not text.strip():
            messagebox.showwarning("Attenzione", "Non c'è testo da salvare!")
            return
            
        file = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="trascrizione.txt"
        )
        
        if file:
            try:
                with open(file, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo("Salvato", f"File salvato con successo in {file}")
            except Exception as e:
                messagebox.showerror("Errore", f"Errore durante il salvataggio: {str(e)}")