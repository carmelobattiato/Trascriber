# --- START OF FILE audio_handler.py ---

import sounddevice as sd
import numpy as np
import wave
import os
import threading
import queue
from pydub import AudioSegment
import soundfile # Use soundfile for reliable WAV writing
import sys
import math # For calculating duration

# Debug Flag for Audio Handler
DEBUG_AUDIO = False # Set to True for detailed logs

class AudioHandler:
    # Default values, suitable for transcription
    DEFAULT_SAMPLE_RATE = 16000 # Whisper works well with 16kHz
    DEFAULT_CHANNELS = 1      # Mono is typical for transcription
    DEFAULT_SUBTYPE = 'PCM_16' # Common WAV format
    CHUNK_SIZE = 1024

    def __init__(self, status_callback=None, waveform_callback=None,
                 initial_sample_rate=None, initial_channels=None):
        """
        Initializes the AudioHandler.

        Args:
            status_callback: Function for status updates.
            waveform_callback: Not used currently (polling queue).
            initial_sample_rate: Starting sample rate.
            initial_channels: Starting number of channels.
        """
        # Use provided initial values or defaults
        self.sample_rate = initial_sample_rate if initial_sample_rate else self.DEFAULT_SAMPLE_RATE
        self.channels = initial_channels if initial_channels else self.DEFAULT_CHANNELS

        self.recording = False
        self.playing = False
        self.recorded_frames = []
        self.audio_data = None # Holds current audio (recorded or loaded) as float32 numpy array
        self.stream = None
        self.audio_queue = queue.Queue()

        self.status_callback = status_callback
        # self.waveform_callback = waveform_callback # Not used

        self.audio_dir = "Audio"
        os.makedirs(self.audio_dir, exist_ok=True)

        if DEBUG_AUDIO: print(f"AUDIO HANDLER INIT: SR={self.sample_rate}, Ch={self.channels}")


    def set_audio_parameters(self, sample_rate, channels):
        """Sets the audio parameters for the NEXT recording."""
        if self.recording or self.playing:
             print("AUDIO HANDLER WARN: Cannot change parameters while recording or playing.")
             return False
        try:
            self.sample_rate = int(sample_rate)
            self.channels = int(channels)
            if DEBUG_AUDIO: print(f"AUDIO HANDLER: Parameters set - SR={self.sample_rate}, Ch={self.channels}")
            return True
        except ValueError:
             print(f"AUDIO HANDLER ERROR: Invalid sample rate or channels value.")
             # Revert to defaults? Or keep previous? Keep previous for now.
             return False

    def get_current_parameters(self):
        """Returns the currently set sample rate and channels."""
        return self.sample_rate, self.channels

    def _notify_status(self, message):
        # ... (same as before) ...
        if self.status_callback:
            try: self.status_callback(message)
            except Exception as e: print(f"Error in status callback: {e}")

    def _audio_callback(self, indata, frames, time, status):
        # ... (same as before, adds data to queue and recorded_frames) ...
        if status: print(f"Stream status: {status}", file=sys.stderr)
        if self.recording:
            chunk_copy = indata.copy()
            if self.audio_queue: self.audio_queue.put(chunk_copy)
            if hasattr(self, 'recorded_frames') and isinstance(self.recorded_frames, list): self.recorded_frames.append(chunk_copy)

            # --- Optional: Print queue size for debugging buffer issues ---
            # if DEBUG_AUDIO and hasattr(self, '_callback_print_counter') and self._callback_print_counter % 50 == 0:
            #      print(f"AUDIO HANDLER DEBUG: Queue size approx: {self.audio_queue.qsize()}")
            # self._callback_print_counter = getattr(self, '_callback_print_counter', 0) + 1
            # ---------------------------------------------------------------

    def start_recording(self):
        # ... (uses currently set self.sample_rate and self.channels) ...
        if self.recording: return
        if DEBUG_AUDIO: print(f"AUDIO HANDLER: Starting recording - SR={self.sample_rate}, Ch={self.channels}")
        self.recording = True
        while not self.audio_queue.empty():
            try: self.audio_queue.get_nowait()
            except queue.Empty: break
        self.recorded_frames = []
        self.audio_data = None # Clear previous audio

        try:
            # Check if the device supports the requested parameters (optional but good)
            # sd.check_input_settings(samplerate=self.sample_rate, channels=self.channels)

            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback,
                blocksize=self.CHUNK_SIZE,
                dtype='float32' # Explicitly request float32
            )
            self.stream.start()
            self._notify_status("Recording...")
            if DEBUG_AUDIO: print("AUDIO HANDLER: Stream started.")
        except sd.PortAudioError as pae:
             # Specific PortAudio errors often indicate parameter issues
             self.recording = False
             error_msg = f"PortAudio Error starting recording ({self.sample_rate}Hz/{self.channels}ch): {pae}"
             self._notify_status(error_msg)
             print(f"AUDIO HANDLER ERROR: {error_msg}")
             self.stream = None
             # Optionally try reverting to defaults?
        except Exception as e:
            self.recording = False
            error_msg = f"Error starting recording ({self.sample_rate}Hz/{self.channels}ch): {e}"
            self._notify_status(error_msg)
            print(f"AUDIO HANDLER ERROR: {error_msg}")
            self.stream = None

    def stop_recording(self):
        # ... (same logic as before to process self.recorded_frames) ...
        if not self.recording: return
        if DEBUG_AUDIO: print("AUDIO HANDLER: Stopping recording...")
        self.recording = False

        if self.stream:
            try: self.stream.stop(); self.stream.close()
            except Exception as e: print(f"AUDIO HANDLER ERROR: stopping/closing stream: {e}")
            finally: self.stream = None
        else:
            if DEBUG_AUDIO:
                print("AUDIO HANDLER: No active stream found to stop.")

        if hasattr(self, 'recorded_frames') and self.recorded_frames:
             try:
                 # Ensure concatenation happens correctly
                 if self.recorded_frames: # Double check it's not empty
                    self.audio_data = np.concatenate(self.recorded_frames, axis=0).astype(np.float32) # Ensure float32
                    self.recorded_frames = []
                    if DEBUG_AUDIO: print(f"AUDIO HANDLER: Concatenated frames. Total samples: {len(self.audio_data)}, dtype: {self.audio_data.dtype}")
                    self._notify_status("Recording finished. Ready to save/play.")
                    return self.audio_data
                 else: raise ValueError("recorded_frames became empty before concatenation")
             except ValueError as e: print(f"AUDIO HANDLER ERROR: concatenating frames: {e}"); self._notify_status("Error processing recording."); self.audio_data = None; return None
             except Exception as e: print(f"AUDIO HANDLER ERROR: processing recorded data: {e}"); self._notify_status("Error processing recording."); self.audio_data = None; return None
        else:
             print("AUDIO HANDLER WARNING: No locally stored frames found after stopping."); self._notify_status("Recording stopped (no processed data)."); self.audio_data = None; return None


    def save_audio(self, filename, file_format="wav"):
        # ... (uses self.sample_rate and self.channels for saving) ...
        if self.audio_data is None or len(self.audio_data) == 0:
            self._notify_status("No audio data to save."); print("Save error: No audio data available.")
            return None, "No audio data available."
        base, _ = os.path.splitext(filename)
        filepath = os.path.join(self.audio_dir, f"{base}.{file_format.lower()}")
        if DEBUG_AUDIO: print(f"AUDIO HANDLER: Saving to {filepath} (SR={self.sample_rate}, Ch={self.channels}, Format={file_format})")
        try:
            # Ensure data is float32 for consistency
            audio_to_save = self.audio_data.astype(np.float32)
            audio_to_save = np.clip(audio_to_save, -1.0, 1.0)
            # Get current channels for saving
            current_channels = audio_to_save.shape[1] if audio_to_save.ndim > 1 else 1

            if file_format.lower() == "wav":
                # Use soundfile with specific subtype if desired
                soundfile.write(filepath, audio_to_save, self.sample_rate, subtype=self.DEFAULT_SUBTYPE)
                msg = f"Saved WAV: {os.path.basename(filepath)}"
            elif file_format.lower() == "mp3":
                # Convert float32 [-1, 1] to int16 for pydub
                audio_int16 = (audio_to_save * 32767).astype(np.int16)
                audio_segment = AudioSegment(
                    audio_int16.tobytes(),
                    frame_rate=self.sample_rate,
                    sample_width=audio_int16.dtype.itemsize, # Should be 2
                    channels=current_channels # Use actual channels from data
                )
                audio_segment.export(filepath, format="mp3")
                msg = f"Saved MP3: {os.path.basename(filepath)}"
            else:
                error_msg = f"Unsupported file format: {file_format}"; self._notify_status(error_msg); print(error_msg); return None, error_msg

            self._notify_status(msg); print(f"AUDIO HANDLER: {msg}")
            return filepath, None
        except FileNotFoundError as e: error_msg = f"Error saving {file_format}: {e}. Is FFmpeg installed/PATH correct for MP3?"; self._notify_status(f"Error saving {file_format}: Check FFmpeg/Permissions."); print(error_msg); return None, error_msg
        except Exception as e: error_msg = f"Error saving audio file '{filepath}': {e}"; self._notify_status(f"Error saving {file_format}."); print(error_msg); import traceback; traceback.print_exc(); return None, error_msg

    def start_playback(self):
        """Plays the currently loaded/recorded self.audio_data"""
        # ... (uses self.sample_rate for playback) ...
        if self.playing: return
        if self.audio_data is None or len(self.audio_data) == 0:
            self._notify_status("No audio data to play."); print("Playback error: No audio data.")
            return
        if DEBUG_AUDIO: print(f"AUDIO HANDLER: Starting playback - Samples={len(self.audio_data)}, SR={self.sample_rate}, dtype={self.audio_data.dtype}")
        self.playing = True
        try:
            self._notify_status("Playing...")
            # Ensure data is float32 for sounddevice playback
            playback_data = self.audio_data.astype(np.float32)
            sd.play(playback_data, self.sample_rate, blocking=True)
            self.playing = False # Reset after blocking call
            self._notify_status("Playback finished.")
            if DEBUG_AUDIO: print("AUDIO HANDLER: Playback finished.")
        except Exception as e:
            self.playing = False; error_msg = f"Error during playback: {e}"; self._notify_status(error_msg); print(f"AUDIO HANDLER ERROR: {error_msg}")
        finally: self.playing = False # Ensure reset

    def stop_playback(self):
        # ... (same as before) ...
        if not self.playing: return
        if DEBUG_AUDIO: print("AUDIO HANDLER: Stopping playback...")
        sd.stop()
        self.playing = False
        self._notify_status("Playback stopped.")
        if DEBUG_AUDIO: print("AUDIO HANDLER: Playback stopped via sd.stop().")

    def load_audio(self, filepath):
        """Loads an audio file into self.audio_data."""
        if self.recording or self.playing:
            msg = "Cannot load audio while recording or playing."
            self._notify_status(msg); print(f"AUDIO HANDLER WARN: {msg}")
            return False, msg

        if DEBUG_AUDIO: print(f"AUDIO HANDLER: Attempting to load audio from {filepath}")
        try:
            # Use soundfile for robust loading and resampling if needed
            data, sr = soundfile.read(filepath, dtype='float32', always_2d=False) # Load as float32

            # Store loaded data and parameters
            self.audio_data = data
            self.sample_rate = sr
            # Infer channels from loaded data shape
            self.channels = data.shape[1] if data.ndim > 1 else 1

            # Clear recording frames as we loaded new data
            self.recorded_frames = []
            # Clear queue
            while not self.audio_queue.empty():
                try: self.audio_queue.get_nowait()
                except queue.Empty: break

            msg = f"Loaded: {os.path.basename(filepath)} ({self.get_audio_duration_str()})"
            self._notify_status(msg)
            if DEBUG_AUDIO: print(f"AUDIO HANDLER: Loaded {len(data)} samples, SR={sr}, Ch={self.channels}, dtype={data.dtype}")
            return True, None # Success

        except Exception as e:
            error_msg = f"Error loading audio file '{filepath}': {e}"
            self._notify_status("Error loading file."); print(f"AUDIO HANDLER ERROR: {error_msg}")
            import traceback; traceback.print_exc()
            self.audio_data = None # Clear data on error
            return False, error_msg


    def get_audio_duration(self):
        """Returns the duration of the current audio_data in seconds."""
        if self.audio_data is not None and self.sample_rate > 0:
            num_samples = len(self.audio_data)
            return num_samples / self.sample_rate
        return 0.0

    def get_audio_duration_str(self):
        """Returns the duration as a formatted string MM:SS.ms"""
        duration_sec = self.get_audio_duration()
        if duration_sec <= 0:
            return "00:00.0"
        total_seconds = duration_sec
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds - math.floor(total_seconds)) * 10) # One decimal place for ms
        return f"{minutes:02}:{seconds:02}.{milliseconds}"


    def get_audio_data_queue(self): return self.audio_queue
    def has_recorded_data(self): return self.audio_data is not None and len(self.audio_data) > 0

# --- END OF FILE audio_handler.py ---