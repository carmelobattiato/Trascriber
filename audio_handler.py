# --- START OF FILE audio_handler.py ---

import sounddevice as sd
import numpy as np
import wave
import os
import threading
import queue
from pydub import AudioSegment
import soundfile # Use soundfile for reliable WAV writing
import sys # Import sys

# Debug Flag for Audio Handler
DEBUG_AUDIO = True

class AudioHandler:
    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_CHANNELS = 1
    CHUNK_SIZE = 1024

    def __init__(self, status_callback=None, waveform_callback=None):
        # ... (init attributes same as before) ...
        self.sample_rate = self.DEFAULT_SAMPLE_RATE
        self.channels = self.DEFAULT_CHANNELS
        self.recording = False
        self.playing = False
        self.recorded_frames = [] # Keep using this for now to store full recording
        self.audio_data = None
        self.stream = None
        self.audio_queue = queue.Queue()

        self.status_callback = status_callback
        # waveform_callback is not used when polling queue
        # self.waveform_callback = waveform_callback

        self.audio_dir = "Audio"
        os.makedirs(self.audio_dir, exist_ok=True)

    def _notify_status(self, message):
        # ... (same as before) ...
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                print(f"Error in status callback: {e}")

    # Removed _notify_waveform as we poll the queue

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(f"Stream status: {status}", file=sys.stderr)
        if self.recording:
            # Copy data for both queue and local storage (if used)
            chunk_copy = indata.copy()

            # --- Add to queue for real-time display ---
            if self.audio_queue: # Check if queue exists
                self.audio_queue.put(chunk_copy)
                # --- DEBUG PRINT: Confirm data is being added to queue ---
                if DEBUG_AUDIO:
                     if not hasattr(self, '_callback_print_counter'): self._callback_print_counter = 0
                     if self._callback_print_counter % 20 == 0: # Print every ~20 chunks
                          print(f"AUDIO HANDLER: Queueing chunk - shape={chunk_copy.shape}, dtype={chunk_copy.dtype}, frames={frames}")
                     self._callback_print_counter += 1
                # ----------------------------------------------------------

            # --- Add to local list for full recording storage ---
            # Ensure self.recorded_frames exists and append
            if hasattr(self, 'recorded_frames') and isinstance(self.recorded_frames, list):
                 self.recorded_frames.append(chunk_copy)
            else:
                 # This case shouldn't happen if initialized correctly, but handle defensively
                 print("AUDIO HANDLER WARNING: recorded_frames list not found or invalid in callback.")


    def start_recording(self):
        # ... (mostly same as before) ...
        if self.recording: return
        if DEBUG_AUDIO: print(f"AUDIO HANDLER: Starting recording - SR={self.sample_rate}, Ch={self.channels}")
        self.recording = True
        # Clear queue from previous runs
        while not self.audio_queue.empty():
            try: self.audio_queue.get_nowait()
            except queue.Empty: break
        self.recorded_frames = [] # Reset local frame list
        self.audio_data = None

        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback,
                blocksize=self.CHUNK_SIZE
            )
            self.stream.start()
            self._notify_status("Recording...")
            if DEBUG_AUDIO: print("AUDIO HANDLER: Stream started.")
        except Exception as e:
            self.recording = False
            error_msg = f"Error starting recording: {e}"
            self._notify_status(error_msg)
            print(f"AUDIO HANDLER ERROR: {error_msg}")
            self.stream = None

    def stop_recording(self):
        # ... (logic remains same, depends on self.recorded_frames) ...
        if not self.recording: return
        if DEBUG_AUDIO: print("AUDIO HANDLER: Stopping recording...")
        self.recording = False # Set flag first

        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                if DEBUG_AUDIO: print("AUDIO HANDLER: Stream stopped and closed.")
            except Exception as e: print(f"AUDIO HANDLER ERROR: stopping/closing stream: {e}")
            finally: self.stream = None
        else:
            # --- FIX: Corrected Syntax ---
            if DEBUG_AUDIO:
                 print("AUDIO HANDLER: No active stream found to stop.")
            # -----------------------------

        if hasattr(self, 'recorded_frames') and self.recorded_frames:
             try:
                 self.audio_data = np.concatenate(self.recorded_frames, axis=0)
                 self.recorded_frames = [] # Clear buffer
                 if DEBUG_AUDIO: print(f"AUDIO HANDLER: Recording stopped. Concatenated frames. Total samples: {len(self.audio_data)}")
                 self._notify_status("Recording finished. Ready to save.")
                 return self.audio_data
             except ValueError as e:
                 print(f"AUDIO HANDLER ERROR: concatenating frames: {e}")
                 self._notify_status("Error processing recording.")
                 self.audio_data = None; return None
             except Exception as e:
                 print(f"AUDIO HANDLER ERROR: processing recorded data: {e}")
                 self._notify_status("Error processing recording.")
                 self.audio_data = None; return None
        else:
             print("AUDIO HANDLER WARNING: No locally stored frames found after stopping. Was data collected?")
             self._notify_status("Recording stopped (no processed data).")
             self.audio_data = None; return None

    def save_audio(self, filename, file_format="wav"):
        # ... (same as before) ...
        if self.audio_data is None or len(self.audio_data) == 0:
            self._notify_status("No audio data to save."); print("Save error: No audio data available.")
            return None, "No audio data available."
        base, _ = os.path.splitext(filename)
        filepath = os.path.join(self.audio_dir, f"{base}.{file_format.lower()}")
        if DEBUG_AUDIO: print(f"AUDIO HANDLER: Attempting save to {filepath} (format: {file_format})")
        try:
            if self.audio_data.dtype != np.float32: audio_to_save = self.audio_data.astype(np.float32)
            else: audio_to_save = self.audio_data
            audio_to_save = np.clip(audio_to_save, -1.0, 1.0)

            if file_format.lower() == "wav":
                soundfile.write(filepath, audio_to_save, self.sample_rate, subtype='PCM_16')
                msg = f"Saved WAV: {os.path.basename(filepath)}"
            elif file_format.lower() == "mp3":
                audio_int16 = (audio_to_save * 32767).astype(np.int16)
                audio_segment = AudioSegment(audio_int16.tobytes(), frame_rate=self.sample_rate, sample_width=audio_int16.dtype.itemsize, channels=self.channels)
                audio_segment.export(filepath, format="mp3")
                msg = f"Saved MP3: {os.path.basename(filepath)}"
            else:
                error_msg = f"Unsupported file format: {file_format}"
                self._notify_status(error_msg); print(error_msg)
                return None, error_msg

            self._notify_status(msg); print(f"AUDIO HANDLER: {msg}")
            return filepath, None
        except FileNotFoundError as e:
             error_msg = f"Error saving {file_format}: {e}. Is FFmpeg installed/PATH correct for MP3?"
             self._notify_status(f"Error saving {file_format}: Check FFmpeg/Permissions."); print(error_msg)
             return None, error_msg
        except Exception as e:
             error_msg = f"Error saving audio file '{filepath}': {e}"
             self._notify_status(f"Error saving {file_format}."); print(error_msg)
             import traceback; traceback.print_exc()
             return None, error_msg

    def start_playback(self, audio_data=None):
        # ... (same as before) ...
        if self.playing: return
        playback_data = audio_data if audio_data is not None else self.audio_data
        if playback_data is None or len(playback_data) == 0:
            self._notify_status("No audio data to play."); print("Playback error: No audio data.")
            return
        if DEBUG_AUDIO: print(f"AUDIO HANDLER: Starting playback - Samples={len(playback_data)}, SR={self.sample_rate}")
        self.playing = True
        try:
            self._notify_status("Playing...")
            sd.play(playback_data, self.sample_rate, blocking=True)
            self.playing = False
            self._notify_status("Playback finished.")
            if DEBUG_AUDIO: print("AUDIO HANDLER: Playback finished.")
        except Exception as e:
            self.playing = False
            error_msg = f"Error during playback: {e}"
            self._notify_status(error_msg); print(f"AUDIO HANDLER ERROR: {error_msg}")
        finally:
            self.playing = False

    def stop_playback(self):
        # ... (same as before) ...
        if not self.playing: return
        if DEBUG_AUDIO: print("AUDIO HANDLER: Stopping playback...")
        sd.stop()
        self.playing = False
        self._notify_status("Playback stopped.")
        if DEBUG_AUDIO: print("AUDIO HANDLER: Playback stopped via sd.stop().")

    def get_audio_data_queue(self):
        return self.audio_queue

    def has_recorded_data(self):
        return self.audio_data is not None and len(self.audio_data) > 0

# --- END OF FILE audio_handler.py ---