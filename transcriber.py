# --- START OF CORRECTED transcriber.py ---

import whisper
import time
import wave
import os
import threading
import tkinter as tk # Import base tk for type hinting if needed
from tkinter import messagebox
import sys
import torch
import typing # **** FIX: Import the typing module ****

# Conditional import for DirectML on Windows
if sys.platform == "win32":
    try:
        import torch_directml
    except ImportError:
        torch_directml = None # Flag that it's not available
else:
    torch_directml = None

# Forward declaration for type hinting the gui_app parameter
if typing.TYPE_CHECKING:
    # This avoids circular import issues during runtime but allows type checkers (like mypy)
    # and IDEs to understand the type of 'gui_app'.
    from gui import ModernTranscriptionApp


class AudioTranscriber:
    # Specify the type hint for gui_app using the forward reference
    def __init__(self, gui_app: 'ModernTranscriptionApp'):
        """Initializes the transcriber backend."""
        self.gui = gui_app # Reference to the main application instance
        self.stop_requested = False

    # Helper to safely print to GUI console via the main app
    def _print(self, message: str):
        """Safely prints a message to the GUI console via the main app."""
        # Delegates the call to the main app's method
        # The main app's method then delegates to the specific UI component's method
        if hasattr(self.gui, '_print'):
            self.gui._print(message)
        else:
            # Fallback if main app somehow doesn't have _print (shouldn't happen)
            print(f"Fallback print (gui._print missing): {message}", file=sys.__stderr__)

    # Helper to safely update GUI progress/status via the main app
    def _update_progress(self, task_key: str, status_key: str, progress_mode: str = "start"):
        """Safely updates the GUI progress state via the main app."""
        if hasattr(self.gui, '_update_progress'):
            self.gui._update_progress(task_key, status_key, progress_mode)

    # Helper to safely finalize GUI state via the main app
    def _finalize_ui(self, success: bool = True, interrupted: bool = False):
        """Safely finalizes the GUI state via the main app."""
        if hasattr(self.gui, '_finalize_ui'):
            self.gui._finalize_ui(success=success, interrupted=interrupted)

    # Helper to show error message box safely via the main app
    def _show_error(self, error_key: str, **kwargs):
        """Shows an error messagebox via the main app."""
        if hasattr(self.gui, '_show_error'):
            self.gui._show_error(error_key, **kwargs)

    # Helper to show info message box safely via the main app
    def _show_info(self, info_key: str, **kwargs):
        """Shows an info messagebox via the main app."""
        if hasattr(self.gui, '_show_info'):
            self.gui._show_info(info_key, **kwargs)

    def get_audio_info(self, file_path: str) -> typing.Optional[tuple[float, int, int]]:
        """Reads basic info (duration, channels, rate) from a WAV file."""
        try:
            with wave.open(file_path, 'r') as audio:
                frames = audio.getnframes()
                rate = audio.getframerate()
                duration = frames / float(rate) if rate > 0 else 0.0
                channels = audio.getnchannels()
                return duration, channels, rate
        except wave.Error as e:
            error_msg = f"Wave Error reading info for {os.path.basename(file_path)}: {e}"
            self._print(f"{error_msg}\n")
            self._show_error("error_reading_info", error=str(e))
            return None
        except Exception as e:
            error_msg = f"General Error reading info for {os.path.basename(file_path)}: {e}"
            self._print(f"{error_msg}\n")
            self._show_error("error_reading_info", error=str(e))
            return None

    def get_audio_duration(self, file_path: str) -> float:
        """Gets the audio duration from a WAV file."""
        info = self.get_audio_info(file_path)
        return info[0] if info else 0.0

    def estimate_time(self, duration: float, model_type: str) -> float:
        """Estimates transcription time based on duration and model."""
        speed_factors = {"tiny": 0.05, "base": 0.1, "small": 0.2, "medium": 0.5, "large": 1.0}
        factor = speed_factors.get(model_type, 1.5)
        estimated_time = duration * factor
        return estimated_time

    def get_device(self, use_gpu: bool, system_type: str) -> typing.Union[str, object]: # Use Union for type hint
        """Determines the compute device (CPU, CUDA, MPS, DML)."""
        device: typing.Union[str, object] = "cpu" # Default device
        if use_gpu:
            try:
                if system_type == "mac" and torch.backends.mps.is_available() and torch.backends.mps.is_built():
                    device = "mps"; self._print(self.gui.translate("using_mps_info") + "\n")
                elif system_type == "windows" and torch_directml:
                    try:
                        dml_device = torch_directml.device()
                        test_tensor = torch.tensor([1.0, 2.0]).to(dml_device)
                        if test_tensor.device.type == 'privateuseone':
                             device = dml_device; self._print(self.gui.translate("using_dml_info") + "\n")
                        else: raise RuntimeError("DirectML device check failed.")
                    except Exception as dml_error:
                        self._print(f"{self.gui.translate('using_dml_info')} {self.gui.translate('error_title')}: {dml_error}, {self.gui.translate('gpu_backend_unavailable_info')}\n")
                        device = "cpu"
                elif torch.cuda.is_available():
                    device = "cuda"; self._print("Using CUDA acceleration.\n")
                else:
                    self._print(self.gui.translate("gpu_backend_unavailable_info") + "\n"); device = "cpu"
            except Exception as e:
                self._print(self.gui.translate("error_gpu_init").format(error=str(e)) + "\n"); device = "cpu"
        else: self._print("GPU not requested, using CPU.\n")
        return device

    def transcribe_audio(self, input_file: str, model_type: str, language: str, use_gpu: bool, system_type: str) -> tuple[str, bool, bool]:
        """Performs the audio transcription process."""
        self.stop_requested = False; transcription_result = ""; success = False; interrupted = False
        try:
            device = self.get_device(use_gpu, system_type)
            device_str = str(device) if not isinstance(device, str) else device # For logging
            self._print(self.gui.translate("transcriber_config_info").format(model_type=model_type, language=language, device=device_str))

            duration = self.get_audio_duration(input_file)
            if duration <= 0: self._print("Error: Invalid audio file or zero duration detected.\n"); raise ValueError("Invalid audio file or zero duration.")
            estimated_time = self.estimate_time(duration, model_type)
            self._update_progress("progress_label_analyzing", "status_loading_model", progress_mode="indeterminate")
            self._print(self.gui.translate("estimated_time_info").format(minutes=int(duration // 60), seconds=int(duration % 60), est_minutes=int(estimated_time // 60), est_seconds=int(estimated_time % 60)))

            start_load_time = time.time(); model = None
            try: model = whisper.load_model(model_type, device=device)
            except Exception as e:
                self._print(self.gui.translate("error_model_load").format(device=device_str, error=str(e)) + "\n")
                if device_str != "cpu":
                    self._print("Retrying model load with CPU...\n"); device = "cpu"; device_str = "cpu"
                    model = whisper.load_model(model_type, device=device)
                else: raise
            if self.stop_requested: interrupted = True; transcription_result = self.gui.translate("progress_label_interrupted"); return transcription_result, success, interrupted
            load_time = time.time() - start_load_time
            self._print(self.gui.translate("model_loaded_info").format(minutes=int(load_time // 60), seconds=int(load_time % 60)))

            self._update_progress("progress_label_transcribing", "status_transcribing", progress_mode="indeterminate")
            start_transcribe_time = time.time(); self._print(self.gui.translate("transcription_started_info"))
            options = {'language': language, 'fp16': False, 'verbose': None}
            result = model.transcribe(input_file, **options)

            if self.stop_requested: interrupted = True; transcription_result = self.gui.translate("progress_label_interrupted"); self._print("\n" + transcription_result + "\n"); return transcription_result, success, interrupted
            transcription_result = result["text"].strip() if result else ""
            self.gui.result_text_set(transcription_result) # Call main app method
            success = True
            transcribe_time = time.time() - start_transcribe_time
            self._print(self.gui.translate("transcription_finished_info").format(minutes=int(transcribe_time // 60), seconds=int(transcribe_time % 60)))
        except Exception as e:
            import traceback; detailed_error = traceback.format_exc()
            self._print(f"\n--- TRANSCRIPTION ERROR ---\n{detailed_error}\n--------------------------\n")
            self._show_error("status_error", error=str(e))
            transcription_result = f"{self.gui.translate('error_title')}: {e}"; success = False
        return transcription_result, success, interrupted

    def start_transcription_async(self, input_file: str, model_type: str, language: str, use_gpu: bool, system_type: str):
        """Starts the transcription process in a separate thread."""
        def run_transcription():
            transcription, success, interrupted = self.transcribe_audio(input_file, model_type, language, use_gpu, system_type)
            # Finalize UI via main app's method (which delegates)
            self._finalize_ui(success=success, interrupted=interrupted)
            # Show popups/messages via main app's method
            if success and not interrupted: self._show_info("completed_message")
            elif interrupted: self._print(self.gui.translate("status_interrupted") + "\n")
            # Error popup is shown inside transcribe_audio's except block
        thread = threading.Thread(target=run_transcription, daemon=True); thread.start()

    def request_stop(self):
        """Sets the flag to request transcription stop."""
        self._print("Stop requested. Finishing current segment...\n")
        self.stop_requested = True

# --- END OF CORRECTED transcriber.py ---