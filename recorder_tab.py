# --- START OF MODIFIED FILE recorder_tab.py ---

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog # Added filedialog
import numpy as np
# No Matplotlib needed
import threading
import queue
import os
import sys
import time
import math # For duration formatting

from audio_handler import AudioHandler

# --- DEBUG FLAG ---
DEBUG_CANVAS = False # Set True for detailed logs

class RecorderTab:
    MAX_WAVEFORM_SECONDS = 10
    CANVAS_UPDATE_INTERVAL = 35 # ms
    MAX_DATA_BUFFER_SECONDS = 11

    # Colors
    BG_COLOR = '#f0f0f0'; CANVAS_BG_COLOR = '#ffffff'; WAVEFORM_COLOR = 'cornflowerblue'
    CENTER_LINE_COLOR = 'red'; SILENCE_LINE_COLOR = '#aaaaaa'

    # Audio Parameter Options
    SAMPLE_RATES = [8000, 16000, 22050, 44100, 48000] # Common rates
    CHANNELS_MAP = {"Mono": 1, "Stereo": 2}

    def __init__(self, parent, update_transcription_path_callback):
        self.parent = parent
        self.update_transcription_path_callback = update_transcription_path_callback
        self.is_recording = False
        self.is_playing = False
        self.save_format = tk.StringVar(value="wav")
        self.status_text = tk.StringVar(value="Ready")
        self.last_saved_filepath = None
        self.waveform_data = np.array([], dtype=np.float32)
        self._max_buffer_samples = 0
        self._check_audio_queue_id = None
        self._update_canvas_id = None
        self._current_playback_time = 0.0
        self._recording_start_time = 0.0
        self._timer_id = None # For time display update

        # --- NEW: Tkinter Variables for Audio Settings ---
        self.selected_sample_rate = tk.IntVar(value=AudioHandler.DEFAULT_SAMPLE_RATE)
        self.selected_channels_str = tk.StringVar(value="Mono") # Display string

        # Initialize AudioHandler with defaults
        self.audio_handler = AudioHandler(
            status_callback=self.update_status,
            initial_sample_rate=self.selected_sample_rate.get(),
            initial_channels=self.CHANNELS_MAP[self.selected_channels_str.get()]
        )
        self.audio_queue = self.audio_handler.get_audio_data_queue()
        # Update internal params based on handler's actual params
        self._update_buffer_params()

        # --- UI Setup ---
        self.frame = ttk.Frame(parent, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1) # Make canvas row expand (now row 2)

        # --- Controls Frame ---
        controls_frame = ttk.Frame(self.frame)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        # Add more columns for new controls
        controls_frame.columnconfigure(5, weight=1) # Status label expansion

        # Row 0: Buttons, Format, Status
        self.record_button = ttk.Button(controls_frame, text="● Record", command=self._toggle_record, style="Primary.TButton", width=12)
        self.record_button.grid(row=0, column=0, padx=(0,5), pady=2)
        self.play_button = ttk.Button(controls_frame, text="▶ Play", command=self._toggle_play, style="Action.TButton", width=12)
        self.play_button.grid(row=0, column=1, padx=5, pady=2)
        self.play_button.config(state=tk.DISABLED)
        self.load_button = ttk.Button(controls_frame, text="Load Audio", command=self._load_audio_file, style="Action.TButton", width=12) # NEW
        self.load_button.grid(row=0, column=2, padx=5, pady=2) # NEW

        format_frame = ttk.LabelFrame(controls_frame, text="Save Fmt", padding=(5, 2)) # Smaller label/padding
        format_frame.grid(row=0, column=3, padx=10, pady=2, sticky='w')
        ttk.Radiobutton(format_frame, text="WAV", variable=self.save_format, value="wav").pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(format_frame, text="MP3", variable=self.save_format, value="mp3").pack(side=tk.LEFT, padx=2)

        self.status_label = ttk.Label(controls_frame, textvariable=self.status_text, anchor=tk.E, style="Status.TLabel")
        self.status_label.grid(row=0, column=5, padx=5, pady=2, sticky='ew')


        # --- NEW: Options Frame ---
        options_frame = ttk.LabelFrame(self.frame, text="Audio Options", padding=(10, 5))
        options_frame.grid(row=1, column=0, sticky="ew", pady=(5, 10))

        ttk.Label(options_frame, text="Sample Rate (Hz):").pack(side=tk.LEFT, padx=(0, 5))
        self.sr_combo = ttk.Combobox(options_frame, textvariable=self.selected_sample_rate, values=self.SAMPLE_RATES, width=8, state='readonly')
        self.sr_combo.pack(side=tk.LEFT, padx=5)
        self.sr_combo.bind("<<ComboboxSelected>>", self._on_settings_changed)

        ttk.Label(options_frame, text="Channels:").pack(side=tk.LEFT, padx=(15, 5))
        self.ch_combo = ttk.Combobox(options_frame, textvariable=self.selected_channels_str, values=list(self.CHANNELS_MAP.keys()), width=7, state='readonly')
        self.ch_combo.pack(side=tk.LEFT, padx=5)
        self.ch_combo.bind("<<ComboboxSelected>>", self._on_settings_changed)

        # --- NEW: Time Display Label ---
        self.time_label = ttk.Label(options_frame, text="Time: 00:00.0", font=("Segoe UI", 10, "bold"))
        self.time_label.pack(side=tk.RIGHT, padx=(10, 0))


        # --- Waveform Canvas Frame ---
        canvas_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        canvas_frame.grid(row=2, column=0, sticky="nsew") # Now row 2
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.waveform_canvas = tk.Canvas(canvas_frame, bg=self.CANVAS_BG_COLOR, highlightthickness=0)
        self.waveform_canvas.grid(row=0, column=0, sticky="nsew")
        self.waveform_canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas_width = 0; self.canvas_height = 0
        self._static_elements_drawn = False

        if self.waveform_canvas:
            if DEBUG_CANVAS: print("CANVAS INIT: Canvas created.")
            self.frame.update_idletasks()
            self._on_canvas_resize()
            self.clear_plot()
            self._schedule_queue_check()
        else:
             if DEBUG_CANVAS: print("CANVAS INIT ERROR: Failed to create canvas.")

    def _update_buffer_params(self):
        """Update buffer sizes based on current sample rate."""
        self.sample_rate = self.audio_handler.sample_rate
        self._max_buffer_samples = int(self.MAX_DATA_BUFFER_SECONDS * self.sample_rate)
        self._max_samples_to_display = int(self.MAX_WAVEFORM_SECONDS * self.sample_rate)
        if DEBUG_CANVAS: print(f"PARAMS UPDATE: SR={self.sample_rate}, MaxBuf={self._max_buffer_samples}, MaxDisp={self._max_samples_to_display}")


    def _schedule_queue_check(self):
        # ... (same as before) ...
        if self._check_audio_queue_id:
            try:
                self.frame.after_cancel(self._check_audio_queue_id)
            except ValueError:
                pass # Ignore error if ID is already invalid
        if hasattr(self, 'frame') and self.frame.winfo_exists(): self._check_audio_queue_id = self.frame.after(self.CANVAS_UPDATE_INTERVAL // 2, self._check_audio_queue)

    def update_status(self, message):
        # ... (same as before) ...
        try:
            if hasattr(self, 'frame') and self.frame.winfo_exists(): self.frame.after_idle(lambda m=message: self.status_text.set(m))
        except Exception as e: print(f"Error updating status label: {e}")

    # --- Canvas Drawing Logic ---
    def _on_canvas_resize(self, event=None):
        # ... (same as before) ...
        new_width = self.waveform_canvas.winfo_width(); new_height = self.waveform_canvas.winfo_height()
        if new_width > 1 and new_height > 1 and (abs(new_width - self.canvas_width) > 5 or abs(new_height - self.canvas_height) > 5 or not self._static_elements_drawn):
            self.canvas_width = new_width; self.canvas_height = new_height
            if DEBUG_CANVAS: print(f"CANVAS RESIZE: New dimensions W={self.canvas_width}, H={self.canvas_height}")
            self._draw_static_canvas_elements()
            if not self.is_recording and not self.is_playing:
                 display_data = self.waveform_data[-self._max_samples_to_display:] if len(self.waveform_data) >= self._max_samples_to_display else self.waveform_data
                 self._draw_waveform_on_canvas(display_data)

    def _draw_static_canvas_elements(self):
        # ... (same as before) ...
        if not (self.waveform_canvas and self.canvas_width > 0 and self.canvas_height > 0): return
        self.waveform_canvas.delete("static_line")
        y_center = self.canvas_height / 2
        self.waveform_canvas.create_line(0, y_center, self.canvas_width, y_center, fill=self.SILENCE_LINE_COLOR, width=1, tags="static_line")
        x_center = self.canvas_width / 2
        self.waveform_canvas.create_line(x_center, 0, x_center, self.canvas_height, fill=self.CENTER_LINE_COLOR, width=1.5, tags="static_line")
        self._static_elements_drawn = True
        # if DEBUG_CANVAS: print("CANVAS DRAW: Static elements drawn.") # Too noisy

    def _draw_waveform_on_canvas(self, data_to_draw):
        # ... (same vectorized logic as before) ...
        if not (self.waveform_canvas and self.canvas_width > 0 and self.canvas_height > 0): return
        self.waveform_canvas.delete("waveform")
        num_samples = len(data_to_draw)
        if num_samples < 2: return

        y_center = self.canvas_height / 2; y_scaling = self.canvas_height / 2 * 0.95
        step = max(1, int(num_samples / self.canvas_width + 0.5)) if self.canvas_width > 0 else 1
        indices = np.arange(0, num_samples, step)
        x_coords = (indices / (num_samples - 1)) * self.canvas_width if num_samples > 1 else np.full(len(indices), self.canvas_width / 2)
        y_coords = y_center - (data_to_draw[indices] * y_scaling)
        coords = np.empty(len(indices) * 2, dtype=np.float64); coords[0::2] = x_coords; coords[1::2] = y_coords

        if len(coords) >= 4:
            # if DEBUG_CANVAS and time.monotonic() % 2 < 0.05: print(f"CANVAS DRAW WAVE: Coords example (first 10): {coords[:10]}")
            self.waveform_canvas.create_line(coords.tolist(), fill=self.WAVEFORM_COLOR, width=1, tags="waveform")


    # --- Settings Change Handler ---
    def _on_settings_changed(self, event=None):
        """Called when sample rate or channels are changed."""
        if self.is_recording or self.is_playing:
             messagebox.showwarning("Busy", "Cannot change audio settings while recording or playing.")
             # Revert UI to match handler's current settings
             sr, ch = self.audio_handler.get_current_parameters()
             self.selected_sample_rate.set(sr)
             ch_str = "Stereo" if ch == 2 else "Mono"
             self.selected_channels_str.set(ch_str)
             return

        try:
             new_sr = self.selected_sample_rate.get()
             new_ch = self.CHANNELS_MAP[self.selected_channels_str.get()]
             if DEBUG_CANVAS: print(f"SETTINGS CHANGED: User selected SR={new_sr}, Ch={new_ch}")
             # Update the audio handler
             success = self.audio_handler.set_audio_parameters(new_sr, new_ch)
             if success:
                 # Update internal buffer params based on new settings
                 self._update_buffer_params()
                 self.update_status(f"Settings: {new_sr} Hz, {self.selected_channels_str.get()}")
             else:
                 # Handler failed, revert UI (shouldn't happen with validation)
                 sr, ch = self.audio_handler.get_current_parameters()
                 self.selected_sample_rate.set(sr)
                 ch_str = "Stereo" if ch == 2 else "Mono"
                 self.selected_channels_str.set(ch_str)
                 messagebox.showerror("Error", "Failed to apply audio settings.")
        except Exception as e:
             print(f"Error handling settings change: {e}")
             messagebox.showerror("Error", f"Invalid audio settings selected: {e}")


    # --- Recording / Playback / Load Logic ---

    def _toggle_record(self):
        # ... (same logic, but uses handler's current params) ...
        if not self.waveform_canvas: messagebox.showerror("Canvas Error", "Cannot record: canvas error."); return
        if self.is_recording:
            if DEBUG_CANVAS: print("TOGGLE RECORD: Stopping...")
            self.is_recording = False; self.stop_canvas_update_loop(); self.stop_timer() # Stop timer too
            self.record_button.config(text="● Record", state=tk.DISABLED); self.play_button.config(state=tk.DISABLED); self.load_button.config(state=tk.DISABLED); self.sr_combo.config(state='readonly'); self.ch_combo.config(state='readonly')
            self.update_status("Processing...")
            def stop_thread():
                 if DEBUG_CANVAS: print("STOP THREAD: Calling handler stop_recording...")
                 recorded_data = self.audio_handler.stop_recording()
                 if DEBUG_CANVAS: print(f"STOP THREAD: Handler finished. Data len: {len(recorded_data) if recorded_data is not None else 'None'}")
                 if hasattr(self, 'frame') and self.frame.winfo_exists(): self.frame.after_idle(self._handle_recording_stopped, recorded_data)
                 else: print("STOP THREAD: Recorder frame destroyed.")
            threading.Thread(target=stop_thread, daemon=True).start()
        else:
            # --- Apply selected settings BEFORE starting ---
            sr = self.selected_sample_rate.get()
            ch = self.CHANNELS_MAP[self.selected_channels_str.get()]
            if not self.audio_handler.set_audio_parameters(sr, ch):
                 messagebox.showerror("Settings Error", "Failed to apply selected audio settings before recording.")
                 return
            self._update_buffer_params() # Ensure buffers match new rate
            # ------------------------------------------------

            if DEBUG_CANVAS: print("TOGGLE RECORD: Starting...")
            self.is_recording = True; self.waveform_data = np.array([], dtype=np.float32)
            self.clear_plot()
            self.record_button.config(text="■ Stop Recording"); self.play_button.config(state=tk.DISABLED); self.load_button.config(state=tk.DISABLED); self.sr_combo.config(state='disabled'); self.ch_combo.config(state='disabled')
            self.last_saved_filepath = None
            self.audio_handler.start_recording() # Uses the newly set params
            self._recording_start_time = time.monotonic() # Start timer
            self.start_timer()
            self.start_canvas_update_loop()


    def _handle_recording_stopped(self, recorded_data):
        # ... (Enable settings combos) ...
        if DEBUG_CANVAS: print("HANDLE STOPPED: Updating UI...")
        if not hasattr(self, 'frame') or not self.frame.winfo_exists(): return
        self.record_button.config(state=tk.NORMAL); self.load_button.config(state=tk.NORMAL); self.sr_combo.config(state='readonly'); self.ch_combo.config(state='readonly')
        if recorded_data is not None and len(recorded_data) > 0:
            if DEBUG_CANVAS: print("HANDLE STOPPED: Data found.")
            self.play_button.config(state=tk.NORMAL)
            if self.waveform_canvas:
                self.waveform_data = recorded_data.flatten()
                if len(self.waveform_data) > self._max_buffer_samples: self.waveform_data = self.waveform_data[-self._max_buffer_samples:]
                display_data = self.waveform_data[-self._max_samples_to_display:] if len(self.waveform_data) >= self._max_samples_to_display else self.waveform_data
                if DEBUG_CANVAS: print("HANDLE STOPPED: Manual draw for final view.")
                self._draw_waveform_on_canvas(display_data)
                # Update final time display based on actual data length
                self._update_time_display(self.audio_handler.get_audio_duration())
            self._save_recording()
        else:
            if DEBUG_CANVAS: print("HANDLE STOPPED: No data found.")
            self.play_button.config(state=tk.DISABLED); self.update_status("Ready (No data recorded)"); self.clear_plot(); self._update_time_display(0)


    def _toggle_play(self):
        # ... (Disable/Enable settings combos) ...
        if not self.waveform_canvas: messagebox.showerror("Canvas Error", "Cannot play: plot error."); return
        if self.is_playing:
            if DEBUG_CANVAS: print("TOGGLE PLAY: Stopping...")
            self.stop_timer() # Stop playback timer
            self.audio_handler.stop_playback()
        else:
            if self.audio_handler.has_recorded_data():
                if DEBUG_CANVAS: print("TOGGLE PLAY: Starting...")
                self.is_playing = True
                self.play_button.config(text="■ Stop Playing"); self.record_button.config(state=tk.DISABLED); self.load_button.config(state=tk.DISABLED); self.sr_combo.config(state='disabled'); self.ch_combo.config(state='disabled')
                self.update_status("Playing...")
                self.stop_canvas_update_loop()
                # Display static waveform and final duration
                if self.waveform_canvas and self.audio_handler.audio_data is not None:
                    if DEBUG_CANVAS: print("TOGGLE PLAY: Displaying full static waveform.")
                    full_data = self.audio_handler.audio_data.flatten()
                    duration = self.audio_handler.get_audio_duration()
                    self.clear_plot()
                    self._draw_waveform_on_canvas(full_data)
                    self._update_time_display(duration) # Show full duration before play
                # Start playback in thread
                def play_thread():
                    if DEBUG_CANVAS: print("PLAY THREAD: Calling handler start_playback...")
                    self.audio_handler.start_playback()
                    if DEBUG_CANVAS: print("PLAY THREAD: Handler finished.")
                    if hasattr(self, 'frame') and self.frame.winfo_exists(): self.frame.after_idle(self._handle_playback_finished)
                    else: print("PLAY THREAD: Recorder frame destroyed.")
                threading.Thread(target=play_thread, daemon=True).start()
            else: messagebox.showwarning("No Audio", "No audio available to play.")


    def _handle_playback_finished(self):
         # ... (Enable settings combos) ...
         if DEBUG_CANVAS: print("HANDLE PLAYBACK FINISHED: Updating UI...")
         self.is_playing = False
         self.stop_timer() # Ensure timer stops
         if hasattr(self, 'play_button') and self.play_button.winfo_exists(): self.play_button.config(text="▶ Play")
         if hasattr(self, 'record_button') and self.record_button.winfo_exists():
             if not self.is_recording: self.record_button.config(state=tk.NORMAL)
         # Enable load and settings
         if hasattr(self, 'load_button') and self.load_button.winfo_exists(): self.load_button.config(state=tk.NORMAL)
         if hasattr(self, 'sr_combo') and self.sr_combo.winfo_exists(): self.sr_combo.config(state='readonly')
         if hasattr(self, 'ch_combo') and self.ch_combo.winfo_exists(): self.ch_combo.config(state='readonly')
         # Restore plot view and show final duration again
         if self.waveform_canvas:
             if DEBUG_CANVAS: print("HANDLE PLAYBACK FINISHED: Restoring real-time plot view appearance.")
             duration = self.audio_handler.get_audio_duration()
             self._update_time_display(duration) # Show final duration
             display_data = self.waveform_data[-self._max_samples_to_display:] if len(self.waveform_data) >= self._max_samples_to_display else self.waveform_data
             self.clear_plot()
             self._draw_waveform_on_canvas(display_data)


    def _load_audio_file(self):
        """Loads an audio file using a file dialog."""
        if self.is_recording or self.is_playing:
             messagebox.showwarning("Busy", "Cannot load audio while recording or playing.")
             return

        filepath = filedialog.askopenfilename(
            title="Load Audio File",
            filetypes=[("Audio Files", "*.wav *.mp3 *.flac *.ogg"), ("All Files", "*.*")]
        )
        if not filepath: return # User cancelled

        if DEBUG_CANVAS: print(f"LOAD AUDIO: User selected '{filepath}'")
        self.update_status("Loading...")
        self.record_button.config(state=tk.DISABLED); self.play_button.config(state=tk.DISABLED); self.load_button.config(state=tk.DISABLED); self.sr_combo.config(state='disabled'); self.ch_combo.config(state='disabled')
        self.stop_canvas_update_loop() # Ensure real-time updates are off

        # Load in a thread to avoid blocking GUI
        def load_thread():
            success, error_msg = self.audio_handler.load_audio(filepath)
            if hasattr(self, 'frame') and self.frame.winfo_exists():
                self.frame.after_idle(self._handle_load_result, success, error_msg)
            else: print("LOAD AUDIO THREAD: Frame destroyed.")
        threading.Thread(target=load_thread, daemon=True).start()


    def _handle_load_result(self, success, error_msg):
        """Called after load_audio finishes."""
        if DEBUG_CANVAS: print(f"HANDLE LOAD RESULT: Success={success}, Error='{error_msg}'")
        # Always re-enable buttons/settings after attempt
        self.record_button.config(state=tk.NORMAL); self.load_button.config(state=tk.NORMAL); self.sr_combo.config(state='readonly'); self.ch_combo.config(state='readonly')

        if success:
            self.play_button.config(state=tk.NORMAL) # Enable play
            self.waveform_data = self.audio_handler.audio_data.flatten() # Update internal buffer
            # Update UI settings to reflect loaded file's properties
            sr, ch = self.audio_handler.get_current_parameters()
            self.selected_sample_rate.set(sr)
            ch_str = "Stereo" if ch == 2 else "Mono"
            self.selected_channels_str.set(ch_str)
            self._update_buffer_params() # Update buffer sizes for potential recording
            # Draw the loaded waveform statically
            self.clear_plot()
            self._draw_waveform_on_canvas(self.waveform_data)
            # Update time display
            self.stop_timer() # Ensure no timer running
            self._update_time_display(self.audio_handler.get_audio_duration())
            self.update_status(f"Loaded: {os.path.basename(self.audio_handler.last_loaded_filepath if hasattr(self.audio_handler, 'last_loaded_filepath') else '... Hiba! Nincs audio_handler.py fájlban ilyen attribútum ...')}") # Use handler's stored path if available
        else:
            self.play_button.config(state=tk.DISABLED)
            messagebox.showerror("Load Error", error_msg or "Failed to load audio file.")
            self.update_status("Load failed.")
            self.clear_plot()
            self._update_time_display(0)


    def _save_recording(self):
        # ... (same as before) ...
        if not self.audio_handler.has_recorded_data(): messagebox.showerror("Error", "No recording data to save."); self.update_status("Ready (No data to save)"); return
        filename = simpledialog.askstring("Save Recording", "Enter filename (without extension):", parent=self.frame)
        if filename:
            chosen_format = self.save_format.get()
            self.update_status(f"Saving as {chosen_format.upper()}..."); self.record_button.config(state=tk.DISABLED); self.play_button.config(state=tk.DISABLED); self.load_button.config(state=tk.DISABLED); self.sr_combo.config(state='disabled'); self.ch_combo.config(state='disabled')
            def save_thread():
                if DEBUG_CANVAS: print(f"SAVE THREAD: Calling handler save_audio ({filename}.{chosen_format})...")
                saved_path, error_msg = self.audio_handler.save_audio(filename, chosen_format)
                if DEBUG_CANVAS: print(f"SAVE THREAD: Handler finished. Path: {saved_path}, Err: {error_msg}")
                if hasattr(self, 'frame') and self.frame.winfo_exists(): self.frame.after_idle(self._handle_save_result, saved_path, error_msg)
                else: print("SAVE THREAD: Recorder frame destroyed.")
            threading.Thread(target=save_thread, daemon=True).start()
        else:
            self.update_status("Save cancelled.")
            if self.audio_handler.has_recorded_data(): self.play_button.config(state=tk.NORMAL)
            self.record_button.config(state=tk.NORMAL); self.load_button.config(state=tk.NORMAL); self.sr_combo.config(state='readonly'); self.ch_combo.config(state='readonly')

    def _handle_save_result(self, saved_path, error_msg):
        # ... (Enable settings combos) ...
        if DEBUG_CANVAS: print("HANDLE SAVE RESULT: Updating UI...")
        if not hasattr(self, 'frame') or not self.frame.winfo_exists(): return
        self.record_button.config(state=tk.NORMAL); self.load_button.config(state=tk.NORMAL); self.sr_combo.config(state='readonly'); self.ch_combo.config(state='readonly')
        if self.audio_handler.has_recorded_data(): self.play_button.config(state=tk.NORMAL)
        else: self.play_button.config(state=tk.DISABLED)
        if error_msg: messagebox.showerror("Save Error", error_msg); self.update_status("Save Error!")
        elif saved_path:
            self.last_saved_filepath = saved_path; status_msg = f"Saved: {os.path.basename(saved_path)}"; print(f"File saved successfully: {saved_path}")
            if messagebox.askyesno("Transcribe Audio?", f"{status_msg}\n\nSet this file for transcription?", parent=self.frame):
                if self.update_transcription_path_callback:
                    try: self.update_transcription_path_callback(saved_path); status_msg = f"File set for transcription."
                    except Exception as cb_error: print(f"Error in transcription path callback: {cb_error}"); status_msg = f"Error setting transcription file."
                else: print("Transcription path callback not set.")
            self.update_status(status_msg)
        else: self.update_status("Save completed (unknown state).")


    # --- Canvas Update Loop & Timer ---

    def start_canvas_update_loop(self):
        # ... (same as before) ...
        if self._update_canvas_id is None:
            if DEBUG_CANVAS: print("CANVAS LOOP: Starting update loop.")
            self.clear_plot(); self._schedule_canvas_update()
        # else: if DEBUG_CANVAS: print("CANVAS LOOP: Already running.")

    def stop_canvas_update_loop(self):
        # ... (same as before) ...
        if self._update_canvas_id is not None:
            if DEBUG_CANVAS: print("CANVAS LOOP: Stopping update loop.")
            try:
                self.frame.after_cancel(self._update_canvas_id)
            except ValueError:
                 pass # Ignore error if ID is already invalid
            self._update_canvas_id = None
        # else: if DEBUG_CANVAS: print("CANVAS LOOP: Already stopped.")

    def _schedule_canvas_update(self):
        # ... (same as before) ...
        if hasattr(self, 'frame') and self.frame.winfo_exists() and hasattr(self, 'waveform_canvas') and self.waveform_canvas.winfo_exists():
             self._update_canvas_id = self.frame.after(self.CANVAS_UPDATE_INTERVAL, self._update_waveform_canvas)
        else:
             if DEBUG_CANVAS:
                 print("CANVAS LOOP: Frame/Canvas destroyed, stopping updates.")
             self._update_canvas_id = None # Ensure loop stops

    def _update_waveform_canvas(self):
        # ... (same logic as before to get data and draw) ...
        if not self.is_recording or self._update_canvas_id is None or not self.waveform_canvas: self._update_canvas_id = None; return
        current_data = self.waveform_data; num_samples_in_buffer = len(current_data)
        start_index = max(0, num_samples_in_buffer - self._max_samples_to_display)
        plot_data = current_data[start_index:]
        # if DEBUG_CANVAS and time.monotonic() % 1.0 < 0.05: print(f"CANVAS UPDATE: Buf={num_samples_in_buffer}, Plot={len(plot_data)}")
        self._draw_waveform_on_canvas(plot_data)
        self._schedule_canvas_update() # Keep loop going

    # --- Data Queue Handling ---
    def _check_audio_queue(self):
        # ... (same logic as before) ...
        queue_processed = False; new_samples_count = 0
        try:
            max_chunks_per_cycle = 10
            for _ in range(max_chunks_per_cycle):
                chunk = self.audio_queue.get_nowait()
                if isinstance(chunk, np.ndarray): new_samples_count += len(chunk.flatten()); self.waveform_data = np.append(self.waveform_data, chunk.flatten()); queue_processed = True
                else: pass
        except queue.Empty: pass
        except Exception as e: print(f"QUEUE ERROR: {e}")
        finally:
            if len(self.waveform_data) > self._max_buffer_samples: self.waveform_data = self.waveform_data[-self._max_buffer_samples:]
            # if DEBUG_CANVAS and queue_processed: print(f"QUEUE CHECK: Read {new_samples_count}. Buf {len(self.waveform_data)}")
            if hasattr(self, 'frame') and self.frame.winfo_exists(): self._schedule_queue_check()
            else: self._check_audio_queue_id = None

    # --- NEW: Timer for Recording/Playback Time ---
    def start_timer(self):
         """Starts the timer to update the time label."""
         self.stop_timer() # Ensure previous timer is stopped
         if DEBUG_CANVAS: print("TIMER: Starting timer.")
         self._update_time_label() # Initial update

    def stop_timer(self):
         """Stops the time label update timer."""
         if self._timer_id is not None:
             if DEBUG_CANVAS: print("TIMER: Stopping timer.")
             try: self.frame.after_cancel(self._timer_id)
             except ValueError: pass
             self._timer_id = None

    def _update_time_label(self):
         """Periodically updates the time label during recording."""
         if not hasattr(self, 'frame') or not self.frame.winfo_exists():
             self._timer_id = None
             return # Stop if frame destroyed

         current_time_sec = 0.0
         if self.is_recording:
             # Calculate elapsed recording time
             current_time_sec = time.monotonic() - self._recording_start_time
             # OR calculate based on buffer length (might lag slightly but reflects data)
             # current_time_sec = len(self.waveform_data) / self.sample_rate if self.sample_rate > 0 else 0.0
         elif self.is_playing:
             # Playback time update needs a different mechanism (e.g., sounddevice callback or estimate)
             # For now, we just show total duration during playback. This func won't be called via timer.
             current_time_sec = self.audio_handler.get_audio_duration() # Or keep last known time
             pass # Don't reschedule if playing (handled differently)
         else:
             # Show duration of loaded/last recorded file if idle
             current_time_sec = self.audio_handler.get_audio_duration()

         self._update_time_display(current_time_sec)

         # --- Reschedule only if recording ---
         if self.is_recording:
              # Update roughly 5 times per second
              self._timer_id = self.frame.after(200, self._update_time_label)
         else:
              self._timer_id = None # Ensure timer stops if not recording

    def _update_time_display(self, total_seconds):
        """Formats seconds and updates the time label."""
        try:
            if total_seconds < 0: total_seconds = 0
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            milliseconds = int((total_seconds - math.floor(total_seconds)) * 10)
            time_str = f"Time: {minutes:02}:{seconds:02}.{milliseconds}"
            if hasattr(self, 'time_label') and self.time_label.winfo_exists():
                 self.time_label.config(text=time_str)
        except Exception as e:
             print(f"Error updating time display: {e}")


    # --- Utility ---
    def clear_plot(self):
         # ... (same canvas clearing logic) ...
         if DEBUG_CANVAS: print("CANVAS CLEAR: Clearing canvas.")
         self.waveform_data = np.array([], dtype=np.float32)
         if self.waveform_canvas: self.waveform_canvas.delete("waveform")

    def on_close(self):
        # ... (same as before, stop timer added) ...
        if DEBUG_CANVAS: print("ON CLOSE: Cleaning up recorder tab...")
        self.stop_timer() # Stop time updater
        self.stop_canvas_update_loop()
        if hasattr(self, '_check_audio_queue_id') and self._check_audio_queue_id:
             try:
                 if self.frame.winfo_exists(): self.frame.after_cancel(self._check_audio_queue_id)
                 if DEBUG_CANVAS: print("ON CLOSE: Cancelled queue check.")
             except Exception as e: print(f"ON CLOSE ERROR: cancelling queue check: {e}")
             self._check_audio_queue_id = None
        if self.audio_handler:
            if self.is_recording: self.audio_handler.stop_recording()
            if self.is_playing: self.audio_handler.stop_playback()
        # No Matplotlib figure to close

# --- END OF MODIFIED FILE recorder_tab.py ---