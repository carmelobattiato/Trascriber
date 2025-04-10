import whisper
import time
import wave
import os
import threading
import tkinter as tk
from tkinter import messagebox
import sys
import torch
# Conditional import for DirectML on Windows
if sys.platform == "win32":
    try:
        import torch_directml
    except ImportError:
        torch_directml = None # Flag that it's not available
else:
    torch_directml = None


class AudioTranscriber:
    def __init__(self, gui_app):
        self.gui = gui_app
        self.stop_requested = False

    # Helper to safely print to GUI console
    def _print(self, message):
        self.gui.console_output_insert(message)

    # Helper to safely update GUI progress/status
    def _update_progress(self, task_key, status_key, progress_mode="start"):
         self.gui.update_progress_state(task_key, status_key, progress_mode)

    # Helper to safely finalize GUI state
    def _finalize_ui(self, success=True, interrupted=False):
        self.gui.finalize_ui_state(success=success, interrupted=interrupted)

    # Helper to show error message box safely
    def _show_error(self, error_key, **kwargs):
         title = self.gui.translate("error_title")
         message = self.gui.translate(error_key).format(**kwargs)
         self.gui.root.after(0, lambda: messagebox.showerror(title, message))

    # Helper to show info message box safely
    def _show_info(self, info_key, **kwargs):
        title = self.gui.translate("info_title")
        message = self.gui.translate(info_key).format(**kwargs)
        self.gui.root.after(0, lambda: messagebox.showinfo(title, message))


    def get_audio_info(self, file_path):
        try:
            with wave.open(file_path, 'r') as audio:
                frames = audio.getnframes()
                rate = audio.getframerate()
                duration = frames / float(rate) if rate > 0 else 0
                channels = audio.getnchannels()
                return duration, channels, rate
        except wave.Error as e:
            self._print(self.gui.translate("error_reading_info").format(error=str(e)) + "\n")
            self._show_error("error_reading_info", error=str(e))
            return None
        except Exception as e:
            self._print(self.gui.translate("error_reading_info").format(error=str(e)) + "\n")
            self._show_error("error_reading_info", error=str(e))
            return None

    def get_audio_duration(self, file_path):
        info = self.get_audio_info(file_path)
        return info[0] if info else 0


    def estimate_time(self, duration, model_type):
        # Rough estimation factors (Transcription time / Audio time)
        # Lower value means faster transcription relative to audio length
        # These are very approximate and CPU/GPU dependent
        speed_factors = {
            "tiny": 0.05,   # ~20x faster than real time
            "base": 0.1,    # ~10x faster
            "small": 0.2,   # ~5x faster
            "medium": 0.5,  # ~2x faster
            "large": 1.0    # ~Real time (can be slower on CPU)
        }
        factor = speed_factors.get(model_type, 1.5) # Default guess if model unknown
        estimated_time = duration * factor
        return estimated_time

    def get_device(self, use_gpu, system_type):
        device = "cpu" # Default
        if use_gpu:
            try:
                if system_type == "mac" and torch.backends.mps.is_available() and torch.backends.mps.is_built():
                    device = "mps"
                    self._print(self.gui.translate("using_mps_info") + "\n")
                elif system_type == "windows" and torch_directml:
                    try:
                        # Check if DirectML device is available and working
                        dml_device = torch_directml.device()
                        # Simple test tensor operation
                        test_tensor = torch.tensor([1.0, 2.0]).to(dml_device)
                        if test_tensor.device.type == 'privateuseone': # DirectML uses 'privateuseone'
                             device = dml_device
                             self._print(self.gui.translate("using_dml_info") + "\n")
                        else:
                            raise RuntimeError("DirectML device check failed.")
                    except Exception as dml_error:
                        self._print(f"{self.gui.translate('using_dml_info')} "
                                    f"{self.gui.translate('error_title')}: {dml_error}, "
                                    f"{self.gui.translate('gpu_backend_unavailable_info')}\n")
                        device = "cpu" # Fallback to CPU
                elif torch.cuda.is_available(): # Check for standard CUDA as fallback
                    device = "cuda"
                    self._print("Using CUDA acceleration.\n") # Add translation if needed
                else:
                    self._print(self.gui.translate("gpu_backend_unavailable_info") + "\n")
            except Exception as e:
                self._print(self.gui.translate("error_gpu_init").format(error=str(e)) + "\n")
                # Don't show messagebox here, just log and fallback
        return device

    def transcribe_audio(self, input_file, model_type, language="italian", use_gpu=False, system_type="windows"):
        self.stop_requested = False
        transcription_result = ""
        success = False
        interrupted = False

        try:
            device = self.get_device(use_gpu, system_type)
            self._print(self.gui.translate("transcriber_config_info").format(
                model_type=model_type, language=language, device=str(device) # Use str(device) for DML object
            ))

            duration = self.get_audio_duration(input_file)
            if duration == 0: # Likely error reading duration
                 raise ValueError("Invalid audio file or zero duration.")

            estimated_time = self.estimate_time(duration, model_type)

            self._update_progress("progress_label_analyzing", "status_loading_model", progress_mode="indeterminate")
            self._print(self.gui.translate("estimated_time_info").format(
                minutes=int(duration // 60), seconds=int(duration % 60),
                est_minutes=int(estimated_time // 60), est_seconds=int(estimated_time % 60)
            ))

            start_load_time = time.time()

            try:
                model = whisper.load_model(model_type, device=device)
            except Exception as e:
                self._print(self.gui.translate("error_model_load").format(device=str(device), error=str(e)) + "\n")
                if device != "cpu": # Only retry if it wasn't CPU already
                    device = "cpu"
                    self._print(f"Retrying with CPU...\n")
                    model = whisper.load_model(model_type, device=device)
                else:
                    raise # Re-raise if loading failed even on CPU

            if self.stop_requested:
                interrupted = True
                transcription_result = self.gui.translate("progress_label_interrupted")
                return transcription_result, success, interrupted

            load_time = time.time() - start_load_time
            self._print(self.gui.translate("model_loaded_info").format(
                minutes=int(load_time // 60), seconds=int(load_time % 60)
            ))

            self._update_progress("progress_label_transcribing", "status_transcribing", progress_mode="indeterminate")
            start_transcribe_time = time.time()
            self._print(self.gui.translate("transcription_started_info"))

            # --- Transcription with progress/stop check ---
            # Note: Whisper's default transcribe doesn't have a built-in callback per segment *during* processing easily accessible
            # without modifying internal library code or using lower-level APIs.
            # We'll update the text *after* the transcription completes for simplicity,
            # but check for stop_requested before starting and potentially after.

            options = {
                'language': language,
                'fp16': False, # FP16 often causes issues with CPU/MPS/DirectML, keep False for broader compatibility
                # 'verbose': True # Whisper's verbose prints to console, not our GUI widget directly
            }

            result = model.transcribe(input_file, **options)

            # Check if stopped *after* the call returns (won't interrupt mid-process)
            if self.stop_requested:
                 interrupted = True
                 transcription_result = self.gui.translate("progress_label_interrupted")
                 self._print("\n" + transcription_result + "\n")
                 return transcription_result, success, interrupted

            transcription_result = result["text"]
            # Update the result text area safely
            self.gui.result_text_set(transcription_result)

            success = True
            transcribe_time = time.time() - start_transcribe_time
            self._print(self.gui.translate("transcription_finished_info").format(
                minutes=int(transcribe_time // 60), seconds=int(transcribe_time % 60)
            ))

        except Exception as e:
            import traceback
            self._print(f"\n{self.gui.translate('error_title')}:\n{traceback.format_exc()}\n")
            self._show_error("status_error", error=str(e)) # Show error in message box
            transcription_result = f"{self.gui.translate('error_title')}: {e}"
            success = False

        finally:
            # Stop progress bar handled by _finalize_ui
            pass # Final UI update happens in the calling thread function

        return transcription_result, success, interrupted


    def start_transcription_async(self, input_file, model_type, language="italian", use_gpu=False, system_type="windows"):
        def run_transcription():
            transcription, success, interrupted = self.transcribe_audio(input_file, model_type, language, use_gpu, system_type)

            # Finalize UI state after transcription attempt
            self._finalize_ui(success=success, interrupted=interrupted)

            if success and not interrupted:
                # Show completion message only on success without interruption
                 self._show_info("completed_message")
            elif interrupted:
                # Status already set to interrupted, maybe add a console message
                self._print(self.gui.translate("status_interrupted") + "\n")
            # Error case: message box already shown in transcribe_audio

        # Ensure the thread is started correctly
        thread = threading.Thread(target=run_transcription, daemon=True)
        thread.start()

    def request_stop(self):
        self.stop_requested = True