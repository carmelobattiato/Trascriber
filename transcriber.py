import whisper
import time
import wave
import os
import threading
import tkinter as tk
from tkinter import messagebox
import sys
import torch

class AudioTranscriber:
    def __init__(self, gui_app):
        self.gui = gui_app
        self.stop_requested = False
    
    def get_audio_info(self, file_path):
        try:
            with wave.open(file_path, 'r') as audio:
                duration = audio.getnframes() / audio.getframerate()
                channels = audio.getnchannels()
                rate = audio.getframerate()
                return duration, channels, rate
        except Exception as e:
            self.gui.console_output.insert(tk.END, f"Errore nel leggere le informazioni del file: {str(e)}\n")
            return None
    
    def get_audio_duration(self, file_path):
        try:
            with wave.open(file_path, 'r') as audio:
                return audio.getnframes() / audio.getframerate()
        except Exception as e:
            self.gui.console_output.insert(tk.END, f"Errore nel leggere la durata del file: {str(e)}\n")
            return 0
    
    def estimate_time(self, duration, model_type):
        base_speeds = {
            "tiny": 8,
            "base": 4,
            "small": 2,
            "medium": 0.5,
            "large": 0.2
        }
        speed_factor = base_speeds.get(model_type, 1)
        estimated_time = duration / speed_factor
        return estimated_time
    
    def get_device(self, use_gpu, system_type):
        device = "cpu"
        if use_gpu:
            try:
                if system_type == "mac" and torch.backends.mps.is_available():
                    device = "mps"
                    print("Usando accelerazione Metal (MPS) per Mac")
                elif system_type == "windows":
                    try:
                        import torch_directml
                        device = torch_directml.device()
                        print("Usando accelerazione DirectML per Windows")
                    except ImportError:
                        print("torch_directml non disponibile, usando CPU")
                else:
                    print("GPU richiesta ma nessun backend disponibile, usando CPU")
            except Exception as e:
                print(f"Errore nell'inizializzazione GPU: {str(e)}, usando CPU")
        return device
    
    def transcribe_audio(self, input_file, model_type, language="italian", use_gpu=False, system_type="windows"):
        self.stop_requested = False
        
        device = self.get_device(use_gpu, system_type)
        print(f"Configurazione: Modello {model_type}, Lingua {language}, Dispositivo {device}")
        
        duration = self.get_audio_duration(input_file)
        estimated_time = self.estimate_time(duration, model_type)
        
        self.gui.current_task.set("Analisi del file audio...")
        print(f"Durata dell'audio: {int(duration // 60)} min {int(duration % 60)} sec")
        print(f"Stima del tempo di trascrizione: {int(estimated_time // 60)} min {int(estimated_time % 60)} sec")
        
        start_total_time = time.time()
        self.gui.current_task.set("Caricamento del modello di AI...")
        self.gui.progress_bar.start(10)
        self.gui.status_var.set("Caricamento modello...")
        self.gui.root.update_idletasks()
        
        try:
            model = whisper.load_model(model_type, device=device)
        except Exception as e:
            print(f"Errore nel caricamento del modello su {device}: {str(e)}, riprovo con CPU")
            device = "cpu"
            model = whisper.load_model(model_type, device=device)
        
        if self.stop_requested:
            self.gui.progress_bar.stop()
            return "Processo interrotto"
        
        total_time = time.time() - start_total_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)  
        print(f"Modello caricato in {minutes} minuti e {seconds} secondi.")
        
        self.gui.current_task.set("Trascrizione in corso...")
        self.gui.status_var.set("Trascrizione in corso...")
        start_total_time = time.time()
        print(f"Avvio della trascrizione...")
        
        options = {
            'fp16': False, 
            'language': language,
            'verbose': True
        }
        
        full_text = ""
        
        def on_segment_callback(segment):
            nonlocal full_text
            segment_text = segment["text"]
            full_text += segment_text
            self.gui.root.after(0, lambda: self.gui.result_text.delete(1.0, tk.END))
            self.gui.root.after(0, lambda: self.gui.result_text.insert(tk.END, full_text))
            self.gui.root.after(0, lambda: self.gui.result_text.see(tk.END))
            return not self.stop_requested
        
        result = model.transcribe(input_file, **options)
        
        full_text = ""
        self.gui.result_text.delete(1.0, tk.END)
        for segment in result["segments"]:
            if self.stop_requested:
                self.gui.progress_bar.stop()
                return "Processo interrotto"
            
            segment_text = segment["text"]
            full_text += segment_text
            self.gui.result_text.delete(1.0, tk.END)
            self.gui.result_text.insert(tk.END, full_text)
            self.gui.result_text.see(tk.END)
            self.gui.root.update_idletasks()
        
        #with open("trascrizione.txt", "w", encoding="utf-8") as f:
        #    f.write(result["text"])
            
        total_time = time.time() - start_total_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)   
        print(f"Trascrizione completata in {minutes} minuti e {seconds} secondi.")
        
        self.gui.progress_bar.stop()
        self.gui.status_var.set("Trascrizione completata")
        self.gui.current_task.set("Trascrizione completata con successo")
        
        return result["text"]
    
    def start_transcription_async(self, input_file, model_type, language="italian", use_gpu=False, system_type="windows"):
        def run_transcription():
            try:
                transcription = self.transcribe_audio(input_file, model_type, language, use_gpu, system_type)
                self.gui.result_text.insert(tk.END, transcription)
                self.gui.root.after(0, lambda: messagebox.showinfo("Completato", "Trascrizione completata!"))
            except Exception as e:
                self.gui.console_output.insert(tk.END, f"Errore: {str(e)}\n")
                self.gui.status_var.set("Errore durante la trascrizione")
                self.gui.current_task.set("Si è verificato un errore")
                self.gui.root.after(0, lambda: messagebox.showerror("Errore", str(e)))
            finally:
                self.gui.start_button.config(state=tk.NORMAL)
                self.gui.stop_button.config(state=tk.DISABLED)
                self.gui.progress_bar.stop()
        
        threading.Thread(target=run_transcription, daemon=True).start()
    
    def request_stop(self):
        self.stop_requested = True