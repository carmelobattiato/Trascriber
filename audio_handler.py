# --- START OF FILE audio_handler.py ---

import sounddevice as sd
import numpy as np
import wave
import os
import threading
import queue
from pydub import AudioSegment
import soundfile # Use soundfile for reliable WAV writing

class AudioHandler:
    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_CHANNELS = 1
    # Using a chunk size compatible with typical audio processing
    # Smaller chunk size leads to more frequent updates but higher overhead
    CHUNK_SIZE = 1024

    def __init__(self, status_callback=None, waveform_callback=None):
        """
        Initializes the AudioHandler.

        Args:
            status_callback: A function to call with status updates (e.g., "Recording...").
            waveform_callback: A function to call with new audio chunks for waveform display.
        """
        self.sample_rate = self.DEFAULT_SAMPLE_RATE
        self.channels = self.DEFAULT_CHANNELS
        self.recording = False
        self.playing = False
        self.recorded_frames = []
        self.stream = None
        self.audio_data = None # Holds the complete recorded or loaded audio data as numpy array
        self.audio_queue = queue.Queue() # Queue for thread-safe communication of audio chunks

        # Callbacks for GUI updates
        self.status_callback = status_callback
        self.waveform_callback = waveform_callback

        # Ensure Audio output directory exists
        self.audio_dir = "Audio"
        os.makedirs(self.audio_dir, exist_ok=True)

    def _notify_status(self, message):
        """Safely notify the GUI about status changes."""
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                print(f"Error in status callback: {e}")

    def _notify_waveform(self, data_chunk):
        """Safely send audio data chunks to the GUI for waveform update."""
        if self.waveform_callback:
             try:
                 # Put data into the queue for the main thread to process
                 self.audio_queue.put(data_chunk.copy())
             except Exception as e:
                 print(f"Error in waveform callback queueing: {e}")


    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(f"Stream status: {status}", file=sys.stderr) # Log stream errors
        if self.recording:
            # Append raw data; conversion happens when stopping
            self.recorded_frames.append(indata.copy())
            # Notify GUI about the new chunk for waveform
            self._notify_waveform(indata)

    def start_recording(self):
        if self.recording:
            print("Already recording.")
            return

        print(f"Starting recording: SR={self.sample_rate}, Channels={self.channels}")
        self.recording = True
        self.recorded_frames = [] # Clear previous recording
        self.audio_data = None    # Clear previous complete data

        try:
             # Check available devices (optional, good for debugging)
             # print(sd.query_devices())

            # Use a non-blocking stream with a callback
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback,
                blocksize=self.CHUNK_SIZE # Process audio in manageable chunks
                # dtype='float32' # Default for sounddevice
            )
            self.stream.start()
            self._notify_status("Recording...")
            print("Stream started.")
        except Exception as e:
            self.recording = False
            self._notify_status(f"Error starting recording: {e}")
            print(f"Error starting recording stream: {e}")
            self.stream = None # Ensure stream is None if failed


    def stop_recording(self):
        if not self.recording:
            print("Not recording.")
            return

        print("Stopping recording...")
        self.recording = False

        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                print("Stream stopped and closed.")
            except Exception as e:
                 print(f"Error stopping/closing stream: {e}")
            finally:
                 self.stream = None
        else:
             print("No active stream found to stop.")


        if self.recorded_frames:
            try:
                # Concatenate all recorded frames (list of numpy arrays)
                self.audio_data = np.concatenate(self.recorded_frames, axis=0)
                self.recorded_frames = [] # Clear chunk buffer
                print(f"Recording stopped. Total samples: {len(self.audio_data)}")
                self._notify_status("Recording finished. Ready to save.")
                # Provide the full waveform data once recording stops
                self._notify_waveform(self.audio_data)
                return self.audio_data
            except ValueError as e:
                 # Handle case where recorded_frames might be empty or have shape issues
                 print(f"Error concatenating frames: {e}")
                 self._notify_status("Error processing recording.")
                 self.audio_data = None
                 return None
            except Exception as e:
                 print(f"Unexpected error processing recorded data: {e}")
                 self._notify_status("Error processing recording.")
                 self.audio_data = None
                 return None

        else:
            print("No frames recorded.")
            self._notify_status("Recording stopped (no data).")
            self.audio_data = None
            return None


    def save_audio(self, filename, file_format="wav"):
        """Saves the recorded audio data to a file."""
        if self.audio_data is None or len(self.audio_data) == 0:
            self._notify_status("No audio data to save.")
            print("Save error: No audio data available.")
            return None, "No audio data available."

        # Ensure filename has the correct extension
        base, _ = os.path.splitext(filename)
        filepath = os.path.join(self.audio_dir, f"{base}.{file_format.lower()}")
        print(f"Attempting to save audio to: {filepath} in format: {file_format}")

        try:
            # Ensure data is in a suitable format (float32 is good for soundfile)
            # If data is not float32, convert it (though sounddevice usually provides float32)
            if self.audio_data.dtype != np.float32:
                # Attempt conversion, normalize if necessary (e.g., if coming from int16)
                 if np.issubdtype(self.audio_data.dtype, np.integer):
                     max_val = np.iinfo(self.audio_data.dtype).max
                     audio_to_save = self.audio_data.astype(np.float32) / max_val
                 else: # Attempt direct conversion for other float types
                     audio_to_save = self.audio_data.astype(np.float32)

                 print(f"Converted audio data from {self.audio_data.dtype} to {audio_to_save.dtype}")
            else:
                 audio_to_save = self.audio_data

            # Clamp values just in case, although normalization should handle it
            audio_to_save = np.clip(audio_to_save, -1.0, 1.0)


            if file_format.lower() == "wav":
                # Using soundfile for robust WAV writing
                soundfile.write(filepath, audio_to_save, self.sample_rate, subtype='PCM_16') # Common WAV format
                # wave module alternative (more manual):
                # wf = wave.open(filepath, 'wb')
                # wf.setnchannels(self.channels)
                # wf.setsampwidth(2)  # 2 bytes for 16-bit audio
                # wf.setframerate(self.sample_rate)
                # # Convert float32 to int16
                # audio_int16 = (audio_to_save * 32767).astype(np.int16)
                # wf.writeframes(audio_int16.tobytes())
                # wf.close()
                self._notify_status(f"Saved as WAV: {os.path.basename(filepath)}")
                print(f"Successfully saved WAV: {filepath}")
                return filepath, None # Return path and no error

            elif file_format.lower() == "mp3":
                # Using pydub for MP3 conversion (requires ffmpeg)
                # Convert numpy array to pydub AudioSegment
                # Ensure data is scaled correctly for int16 if needed by pydub
                # pydub works well with int16 representation
                audio_int16 = (audio_to_save * 32767).astype(np.int16)
                audio_segment = AudioSegment(
                    audio_int16.tobytes(),
                    frame_rate=self.sample_rate,
                    sample_width=audio_int16.dtype.itemsize, # Should be 2 for int16
                    channels=self.channels
                )
                # Export as MP3
                audio_segment.export(filepath, format="mp3")
                self._notify_status(f"Saved as MP3: {os.path.basename(filepath)}")
                print(f"Successfully saved MP3: {filepath}")
                return filepath, None # Return path and no error

            else:
                error_msg = f"Unsupported file format: {file_format}"
                self._notify_status(error_msg)
                print(error_msg)
                return None, error_msg

        except FileNotFoundError as e:
             # Specifically catch if ffmpeg is likely missing for MP3
             error_msg = f"Error saving {file_format}: {e}. Is FFmpeg installed and in PATH (for MP3)?"
             self._notify_status(f"Error saving {file_format}: Check FFmpeg/Permissions.")
             print(error_msg)
             return None, error_msg
        except Exception as e:
             error_msg = f"Error saving audio file '{filepath}': {e}"
             self._notify_status(f"Error saving {file_format}.")
             print(error_msg)
             import traceback
             traceback.print_exc()
             return None, error_msg

    def start_playback(self, audio_data=None):
        """Plays the provided audio data or the last recorded audio."""
        if self.playing:
            print("Already playing.")
            return
        if audio_data is None:
            audio_data = self.audio_data

        if audio_data is None or len(audio_data) == 0:
            self._notify_status("No audio data to play.")
            print("Playback error: No audio data.")
            return

        print(f"Starting playback: Samples={len(audio_data)}, SR={self.sample_rate}")
        self.playing = True

        try:
            self._notify_status("Playing...")
            # Play in a blocking way for simplicity here
            # For non-blocking playback with waveform, a callback approach is needed
            sd.play(audio_data, self.sample_rate, blocking=True)
            # Once sd.play finishes (blocking=True):
            self.playing = False
            self._notify_status("Playback finished.")
            print("Playback finished.")

        except Exception as e:
            self.playing = False
            self._notify_status(f"Error during playback: {e}")
            print(f"Error during playback: {e}")
        finally:
            # Ensure 'playing' state is reset if an error occurs during play
            self.playing = False
            # Ensure final status update occurs
            if self.status_callback and not self.recording: # Avoid overwriting recording status
                 # Use a slight delay to ensure it's the last status update
                 threading.Timer(0.1, self._notify_status, ["Playback finished or stopped."]).start()


    def stop_playback(self):
        """Stops the currently playing audio."""
        if not self.playing:
            # print("Not playing.")
            return
        print("Stopping playback...")
        sd.stop() # Stop any active playback
        self.playing = False
        self._notify_status("Playback stopped.")
        print("Playback stopped via sd.stop().")

    def get_audio_data_queue(self):
        """Returns the queue containing audio chunks."""
        return self.audio_queue

    def has_recorded_data(self):
        """Checks if there is recorded data available."""
        return self.audio_data is not None and len(self.audio_data) > 0

# --- END OF FILE audio_handler.py ---