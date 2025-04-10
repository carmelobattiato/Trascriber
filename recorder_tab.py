# --- START OF MODIFIED FILE recorder_tab.py ---

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import numpy as np
# No Matplotlib needed
import threading
import queue
import os
import sys
import time

from audio_handler import AudioHandler

# --- DEBUG FLAG ---
DEBUG_CANVAS = True

class RecorderTab:
    MAX_WAVEFORM_SECONDS = 10
    CANVAS_UPDATE_INTERVAL = 35 # ms
    MAX_DATA_BUFFER_SECONDS = 11

    BG_COLOR = '#f0f0f0'
    CANVAS_BG_COLOR = '#ffffff'
    WAVEFORM_COLOR = 'cornflowerblue'
    CENTER_LINE_COLOR = 'red'
    SILENCE_LINE_COLOR = '#aaaaaa'

    def __init__(self, parent, update_transcription_path_callback):
        # ... (init attributes) ...
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

        self.audio_handler = AudioHandler(status_callback=self.update_status)
        self.audio_queue = self.audio_handler.get_audio_data_queue()
        self.sample_rate = self.audio_handler.sample_rate
        self._max_buffer_samples = int(self.MAX_DATA_BUFFER_SECONDS * self.sample_rate)
        self._max_samples_to_display = int(self.MAX_WAVEFORM_SECONDS * self.sample_rate)
        if DEBUG_CANVAS: print(f"INIT: SR={self.sample_rate}, MaxBuf={self._max_buffer_samples}, MaxDisp={self._max_samples_to_display}")

        self.frame = ttk.Frame(parent, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Controls Frame... (same)
        controls_frame = ttk.Frame(self.frame); controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10)); controls_frame.columnconfigure(3, weight=1)
        self.record_button = ttk.Button(controls_frame, text="● Record", command=self._toggle_record, style="Primary.TButton", width=15); self.record_button.grid(row=0, column=0, padx=5)
        self.play_button = ttk.Button(controls_frame, text="▶ Play", command=self._toggle_play, style="Action.TButton", width=15); self.play_button.grid(row=0, column=1, padx=5); self.play_button.config(state=tk.DISABLED)
        format_frame = ttk.LabelFrame(controls_frame, text="Save Format", padding=(10, 5)); format_frame.grid(row=0, column=2, padx=20)
        ttk.Radiobutton(format_frame, text="WAV", variable=self.save_format, value="wav").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="MP3", variable=self.save_format, value="mp3").pack(side=tk.LEFT, padx=5)
        status_label = ttk.Label(controls_frame, textvariable=self.status_text, anchor=tk.E, style="Status.TLabel"); status_label.grid(row=0, column=3, padx=10, sticky='ew')

        # Waveform Canvas Frame
        canvas_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.waveform_canvas = tk.Canvas(canvas_frame, bg=self.CANVAS_BG_COLOR, highlightthickness=0)
        self.waveform_canvas.grid(row=0, column=0, sticky="nsew")
        self.waveform_canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas_width = 0
        self.canvas_height = 0
        self._static_elements_drawn = False

        if self.waveform_canvas:
            if DEBUG_CANVAS: print("CANVAS INIT: Canvas created.")
            # --- Force initial configure and draw ---
            self.frame.update_idletasks() # Try to force geometry calculation
            self._on_canvas_resize() # Manually call resize handler once
            self.clear_plot() # Draw initial empty state
            # -----------------------------------------
            self._schedule_queue_check() # Start queue polling
        else:
             if DEBUG_CANVAS: print("CANVAS INIT ERROR: Failed to create canvas.")


    def _schedule_queue_check(self):
        # ... (same as before) ...
        if self._check_audio_queue_id:
            try: self.frame.after_cancel(self._check_audio_queue_id)
            except ValueError: pass
        if hasattr(self, 'frame') and self.frame.winfo_exists():
            self._check_audio_queue_id = self.frame.after(self.CANVAS_UPDATE_INTERVAL // 2, self._check_audio_queue)

    def update_status(self, message):
        # ... (same as before) ...
        try:
            if hasattr(self, 'frame') and self.frame.winfo_exists():
                 self.frame.after_idle(lambda m=message: self.status_text.set(m))
        except Exception as e: print(f"Error updating status label: {e}")

    # --- Canvas Drawing Logic ---

    def _on_canvas_resize(self, event=None):
        # ... (same as before) ...
        new_width = self.waveform_canvas.winfo_width()
        new_height = self.waveform_canvas.winfo_height()
        if new_width > 1 and new_height > 1 and \
           (abs(new_width - self.canvas_width) > 5 or abs(new_height - self.canvas_height) > 5 or not self._static_elements_drawn):
            self.canvas_width = new_width
            self.canvas_height = new_height
            if DEBUG_CANVAS: print(f"CANVAS RESIZE: New dimensions W={self.canvas_width}, H={self.canvas_height}")
            self._draw_static_canvas_elements()
            if not self.is_recording and not self.is_playing:
                 # Redraw current state after resize if idle
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
        if DEBUG_CANVAS: print("CANVAS DRAW: Static elements drawn.")

    def _draw_waveform_on_canvas(self, data_to_draw):
        # ... (same as before, maybe add print for coords) ...
        if not (self.waveform_canvas and self.canvas_width > 0 and self.canvas_height > 0): return
        self.waveform_canvas.delete("waveform")
        num_samples = len(data_to_draw)
        if num_samples < 2: return

        y_center = self.canvas_height / 2
        y_scaling = self.canvas_height / 2 * 0.95 # Use 95% height
        # Adjust step for downsampling if needed (more aggressive?)
        step = max(1, int(num_samples / self.canvas_width + 0.5)) if self.canvas_width > 0 else 1
        coords = []
        # Use arange for potentially better performance than range+step
        indices = np.arange(0, num_samples, step)
        # Pre-calculate x coordinates
        x_coords = (indices / (num_samples - 1)) * self.canvas_width if num_samples > 1 else np.full(len(indices), self.canvas_width / 2)
        # Calculate y coordinates (vectorized)
        y_coords = y_center - (data_to_draw[indices] * y_scaling)

        # Combine into coordinate list [(x1, y1), (x2, y2), ...]
        # This might be slow for large coords, but create_line needs it this way.
        # Flattening is likely faster: [x1, y1, x2, y2, ...]
        coords = np.empty(len(indices) * 2, dtype=np.float64)
        coords[0::2] = x_coords
        coords[1::2] = y_coords

        if len(coords) >= 4:
            if DEBUG_CANVAS and time.monotonic() % 2 < 0.05: # Print coords occasionally
                  print(f"CANVAS DRAW WAVE: Coords example (first 10): {coords[:10]}")
            self.waveform_canvas.create_line(coords.tolist(), fill=self.WAVEFORM_COLOR, width=1, tags="waveform")
        # else: # No need to print this every time
            # if DEBUG_CANVAS: print(f"CANVAS DRAW WAVE: Not enough coords ({len(coords)})")

    # --- Recording / Playback Logic ---

    def _toggle_record(self):
        # ... (same as before) ...
        if not self.waveform_canvas: messagebox.showerror("Canvas Error", "Cannot record: canvas error."); return
        if self.is_recording:
            if DEBUG_CANVAS: print("TOGGLE RECORD: Stopping...")
            self.is_recording = False
            self.stop_canvas_update_loop()
            self.record_button.config(text="● Record", state=tk.DISABLED)
            self.play_button.config(state=tk.DISABLED)
            self.update_status("Processing...")
            def stop_thread():
                 if DEBUG_CANVAS: print("STOP THREAD: Calling handler stop_recording...")
                 recorded_data = self.audio_handler.stop_recording()
                 if DEBUG_CANVAS: print(f"STOP THREAD: Handler finished. Data len: {len(recorded_data) if recorded_data is not None else 'None'}")
                 if hasattr(self, 'frame') and self.frame.winfo_exists(): self.frame.after_idle(self._handle_recording_stopped, recorded_data)
                 else: print("STOP THREAD: Recorder frame destroyed.")
            threading.Thread(target=stop_thread, daemon=True).start()
        else:
            if DEBUG_CANVAS: print("TOGGLE RECORD: Starting...")
            self.is_recording = True
            self.waveform_data = np.array([], dtype=np.float32)
            self.clear_plot()
            self.record_button.config(text="■ Stop Recording")
            self.play_button.config(state=tk.DISABLED)
            self.last_saved_filepath = None
            self.audio_handler.start_recording()
            self.start_canvas_update_loop()

    def _handle_recording_stopped(self, recorded_data):
        # ... (same as before) ...
        if DEBUG_CANVAS: print("HANDLE STOPPED: Updating UI...")
        if not hasattr(self, 'frame') or not self.frame.winfo_exists(): return
        self.record_button.config(state=tk.NORMAL)
        if recorded_data is not None and len(recorded_data) > 0:
            if DEBUG_CANVAS: print("HANDLE STOPPED: Data found.")
            self.play_button.config(state=tk.NORMAL)
            if self.waveform_canvas:
                self.waveform_data = recorded_data.flatten()
                if len(self.waveform_data) > self._max_buffer_samples: self.waveform_data = self.waveform_data[-self._max_buffer_samples:]
                display_data = self.waveform_data[-self._max_samples_to_display:] if len(self.waveform_data) >= self._max_samples_to_display else self.waveform_data
                if DEBUG_CANVAS: print("HANDLE STOPPED: Manual draw for final view.")
                self._draw_waveform_on_canvas(display_data)
            self._save_recording()
        else:
            if DEBUG_CANVAS: print("HANDLE STOPPED: No data found.")
            self.play_button.config(state=tk.DISABLED)
            self.update_status("Ready (No data recorded)")
            self.clear_plot()

    def _toggle_play(self):
        # ... (same as before) ...
        if not self.waveform_canvas: messagebox.showerror("Canvas Error", "Cannot play: plot error."); return
        if self.is_playing:
            if DEBUG_CANVAS: print("TOGGLE PLAY: Stopping...")
            self.audio_handler.stop_playback()
        else:
            if self.audio_handler.has_recorded_data():
                if DEBUG_CANVAS: print("TOGGLE PLAY: Starting...")
                self.is_playing = True
                self.play_button.config(text="■ Stop Playing")
                self.record_button.config(state=tk.DISABLED)
                self.update_status("Playing...")
                self.stop_canvas_update_loop()
                if self.waveform_canvas and self.audio_handler.audio_data is not None:
                     if DEBUG_CANVAS: print("TOGGLE PLAY: Displaying full static waveform.")
                     full_data = self.audio_handler.audio_data.flatten()
                     self.clear_plot()
                     self._draw_waveform_on_canvas(full_data)
                def play_thread():
                    if DEBUG_CANVAS: print("PLAY THREAD: Calling handler start_playback...")
                    self.audio_handler.start_playback()
                    if DEBUG_CANVAS: print("PLAY THREAD: Handler finished.")
                    if hasattr(self, 'frame') and self.frame.winfo_exists(): self.frame.after_idle(self._handle_playback_finished)
                    else: print("PLAY THREAD: Recorder frame destroyed.")
                threading.Thread(target=play_thread, daemon=True).start()
            else: messagebox.showwarning("No Audio", "No recorded audio available to play.")

    def _handle_playback_finished(self):
         # ... (same as before) ...
         if DEBUG_CANVAS: print("HANDLE PLAYBACK FINISHED: Updating UI...")
         self.is_playing = False
         if hasattr(self, 'play_button') and self.play_button.winfo_exists(): self.play_button.config(text="▶ Play")
         if hasattr(self, 'record_button') and self.record_button.winfo_exists():
             if not self.is_recording: self.record_button.config(state=tk.NORMAL)
         if self.waveform_canvas:
             if DEBUG_CANVAS: print("HANDLE PLAYBACK FINISHED: Restoring real-time plot view appearance.")
             display_data = self.waveform_data[-self._max_samples_to_display:] if len(self.waveform_data) >= self._max_samples_to_display else self.waveform_data
             self.clear_plot()
             self._draw_waveform_on_canvas(display_data)

    def _save_recording(self):
        # ... (same as before) ...
        if not self.audio_handler.has_recorded_data(): messagebox.showerror("Error", "No recording data to save."); self.update_status("Ready (No data to save)"); return
        filename = simpledialog.askstring("Save Recording", "Enter filename (without extension):", parent=self.frame)
        if filename:
            chosen_format = self.save_format.get()
            self.update_status(f"Saving as {chosen_format.upper()}..."); self.record_button.config(state=tk.DISABLED); self.play_button.config(state=tk.DISABLED)
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
            self.record_button.config(state=tk.NORMAL)

    def _handle_save_result(self, saved_path, error_msg):
        # ... (same as before) ...
        if DEBUG_CANVAS: print("HANDLE SAVE RESULT: Updating UI...")
        if not hasattr(self, 'frame') or not self.frame.winfo_exists(): return
        self.record_button.config(state=tk.NORMAL)
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

    # --- Canvas Update Loop ---

    def start_canvas_update_loop(self):
        if self._update_canvas_id is None:
            if DEBUG_CANVAS: print("CANVAS LOOP: Starting update loop.")
            self.clear_plot() # Start with a clean plot
            self._schedule_canvas_update() # Start the loop
        # else: if DEBUG_CANVAS: print("CANVAS LOOP: Already running.")

    def stop_canvas_update_loop(self):
        if self._update_canvas_id is not None:
            if DEBUG_CANVAS: print("CANVAS LOOP: Stopping update loop.")
            try: self.frame.after_cancel(self._update_canvas_id)
            except ValueError: pass
            self._update_canvas_id = None
        # else: if DEBUG_CANVAS: print("CANVAS LOOP: Already stopped.")

    def _schedule_canvas_update(self):
        if hasattr(self, 'frame') and self.frame.winfo_exists() and hasattr(self, 'waveform_canvas') and self.waveform_canvas.winfo_exists():
             self._update_canvas_id = self.frame.after(self.CANVAS_UPDATE_INTERVAL, self._update_waveform_canvas)
        else:
             if DEBUG_CANVAS: print("CANVAS LOOP: Frame/Canvas destroyed, stopping updates.")
             self._update_canvas_id = None

    def _update_waveform_canvas(self):
        """Periodically called via after() to redraw the canvas when recording."""
        # Check state *before* processing
        if not self.is_recording or self._update_canvas_id is None or not self.waveform_canvas:
            # if DEBUG_CANVAS: print("CANVAS UPDATE: Skipped (not recording or loop stopped or canvas invalid).")
            self._update_canvas_id = None # Ensure loop terminates if state is wrong
            return

        # --- Get data for the display window (most recent part of buffer) ---
        current_data = self.waveform_data # Use the buffer updated by _check_audio_queue
        num_samples_in_buffer = len(current_data)

        # Select the last part of the buffer for display
        start_index = max(0, num_samples_in_buffer - self._max_samples_to_display)
        plot_data = current_data[start_index:]

        if DEBUG_CANVAS and time.monotonic() % 1.0 < 0.05: # Print occasionally
            print(f"CANVAS UPDATE: Buffer size={num_samples_in_buffer}, Plotting {len(plot_data)} samples.")

        # --- Draw ---
        self._draw_waveform_on_canvas(plot_data) # Draw the selected window

        # --- Reschedule ---
        self._schedule_canvas_update() # Keep the loop going


    # --- Data Queue Handling ---
    def _check_audio_queue(self):
        """Periodically check the audio queue for new data."""
        queue_processed = False
        new_samples_count = 0
        try:
            # Process up to N chunks to avoid blocking GUI for too long if queue is large
            max_chunks_per_cycle = 10
            for _ in range(max_chunks_per_cycle):
                chunk = self.audio_queue.get_nowait()
                if isinstance(chunk, np.ndarray):
                    new_samples_count += len(chunk.flatten())
                    self.waveform_data = np.append(self.waveform_data, chunk.flatten())
                    queue_processed = True
                else: pass
        except queue.Empty: pass # No more data for now
        except Exception as e: print(f"QUEUE ERROR: {e}")
        finally:
            # Limit buffer size *after* processing queue for the cycle
            if len(self.waveform_data) > self._max_buffer_samples:
                self.waveform_data = self.waveform_data[-self._max_buffer_samples:]

            if DEBUG_CANVAS and queue_processed:
                 print(f"QUEUE CHECK: Read {new_samples_count} new samples. Buffer size {len(self.waveform_data)}")

            # Reschedule next check
            if hasattr(self, 'frame') and self.frame.winfo_exists():
                 self._schedule_queue_check()
            else: self._check_audio_queue_id = None

    # --- Utility ---
    def clear_plot(self):
         """Clears the waveform canvas."""
         if DEBUG_CANVAS: print("CANVAS CLEAR: Clearing canvas.")
         self.waveform_data = np.array([], dtype=np.float32)
         if self.waveform_canvas:
             self.waveform_canvas.delete("waveform")

    def on_close(self):
        # ... (same as before) ...
        if DEBUG_CANVAS: print("ON CLOSE: Cleaning up recorder tab...")
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