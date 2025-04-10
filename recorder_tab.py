# --- START OF MODIFIED FILE recorder_tab.py ---

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.animation import FuncAnimation
import threading
import queue
import os
import sys # Import sys for error printing if needed
import time # Import time for debugging if needed

from audio_handler import AudioHandler # Import the handler

class RecorderTab:
    MAX_WAVEFORM_SECONDS = 10 # Max seconds to display on waveform at once
    ANIMATION_INTERVAL = 50 # Milliseconds between waveform updates (lower for smoother, higher for less CPU)
    MAX_DATA_BUFFER_SECONDS = 15 # Store slightly more data than displayed for smoother scrolling

    def __init__(self, parent, update_transcription_path_callback):
        # ... (init remains largely the same) ...
        self.parent = parent
        self.update_transcription_path_callback = update_transcription_path_callback
        self.is_recording = False
        self.is_playing = False
        self.save_format = tk.StringVar(value="wav")
        self.status_text = tk.StringVar(value="Ready")
        self.last_saved_filepath = None
        self.waveform_data = np.array([], dtype=np.float32)
        self._max_buffer_samples = 0
        self.animation = None
        self._animation_running = False
        self._check_audio_queue_id = None

        self.audio_handler = AudioHandler(
            status_callback=self.update_status,
            waveform_callback=None
        )
        self.audio_queue = self.audio_handler.get_audio_data_queue()
        # Calculate buffer size based on actual sample rate from handler
        self._max_buffer_samples = int(self.MAX_DATA_BUFFER_SECONDS * self.audio_handler.sample_rate)
        print(f"Max buffer samples: {self._max_buffer_samples}") # Debug print

        self.frame = ttk.Frame(parent, padding="10")
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Controls Frame
        controls_frame = ttk.Frame(self.frame)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.columnconfigure(3, weight=1)

        self.record_button = ttk.Button(controls_frame, text="● Record", command=self._toggle_record, style="Primary.TButton", width=15)
        self.record_button.grid(row=0, column=0, padx=5)
        self.play_button = ttk.Button(controls_frame, text="▶ Play", command=self._toggle_play, style="Action.TButton", width=15)
        self.play_button.grid(row=0, column=1, padx=5)
        self.play_button.config(state=tk.DISABLED)

        format_frame = ttk.LabelFrame(controls_frame, text="Save Format", padding=(10, 5))
        format_frame.grid(row=0, column=2, padx=20)
        ttk.Radiobutton(format_frame, text="WAV", variable=self.save_format, value="wav").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="MP3", variable=self.save_format, value="mp3").pack(side=tk.LEFT, padx=5)

        status_label = ttk.Label(controls_frame, textvariable=self.status_text, anchor=tk.E, style="Status.TLabel")
        status_label.grid(row=0, column=3, padx=10, sticky='ew')

        # Waveform Plot Frame
        plot_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        plot_frame.grid(row=1, column=0, sticky="nsew")
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)

        self.fig = self.ax = self.line = self.canvas = self.canvas_widget = None
        try:
            # --- Plot Initialization ---
            self.fig, self.ax = plt.subplots()
            self.fig.set_facecolor('#f0f0f0')
            self.ax.set_facecolor('#ffffff')
            self.ax.margins(0.01, 0.1) # Smaller margins
            self.ax.tick_params(axis='y', labelsize=8)
            self.ax.tick_params(axis='x', labelsize=8)
            self.ax.set_ylim(-1.05, 1.05)
            self.ax.set_yticks([-1, 0, 1])
            self.ax.set_xlabel("Time (s)", fontsize=9)
            self.ax.set_ylabel("Amplitude", fontsize=9)
            self.ax.grid(True, linestyle=':', linewidth=0.5, alpha=0.7)
            # Initialize with valid data points to avoid plot errors initially
            self.line, = self.ax.plot([0], [0], lw=1, color='cornflowerblue')

            self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
            self.canvas_widget = self.canvas.get_tk_widget()
            self.canvas_widget.grid(row=0, column=0, sticky="nsew")

            self.fig.tight_layout(pad=1.5)
            self.canvas.draw_idle()
            print("Matplotlib plot initialized successfully.")
        except Exception as e:
             print(f"Error initializing Matplotlib plot: {e}")
             # Display error in the plot area
             error_label = ttk.Label(plot_frame, text=f"Error initializing plot:\n{e}\nCheck Matplotlib/TkAgg setup.", style="Status.TLabel", anchor="center", justify="center")
             error_label.grid(row=0, column=0, sticky="nsew")

        if self.canvas:
            self._schedule_queue_check()

    def _schedule_queue_check(self):
        # ... (same as before) ...
        if self._check_audio_queue_id:
            try: self.frame.after_cancel(self._check_audio_queue_id)
            except ValueError: pass # Ignore if ID is already invalid
        if hasattr(self, 'frame') and self.frame.winfo_exists():
            self._check_audio_queue_id = self.frame.after(self.ANIMATION_INTERVAL // 2, self._check_audio_queue)

    def update_status(self, message):
        # ... (same as before) ...
        try:
            if hasattr(self, 'frame') and self.frame.winfo_exists():
                 self.frame.after_idle(lambda m=message: self.status_text.set(m))
        except Exception as e:
             print(f"Error updating status label: {e}")


    def _toggle_record(self):
        # ... (mostly same, ensures animation start/stop) ...
        if not self.canvas:
             messagebox.showerror("Plot Error", "Cannot record: waveform plot failed initialization.")
             return

        if self.is_recording:
            print("Stop recording requested.")
            self.is_recording = False
            # UI updates first
            self.record_button.config(text="● Record", state=tk.DISABLED)
            self.play_button.config(state=tk.DISABLED)
            self.update_status("Processing...")

            # Stop audio handler in thread
            def stop_thread():
                 print("Running stop_recording in thread...")
                 recorded_data = self.audio_handler.stop_recording()
                 print(f"stop_recording finished. Data len: {len(recorded_data) if recorded_data is not None else 'None'}")
                 # Schedule GUI updates back on the main thread
                 if hasattr(self, 'frame') and self.frame.winfo_exists():
                     # Pass data to handler, then stop animation
                     self.frame.after_idle(self._handle_recording_stopped, recorded_data)
                     # Stop animation AFTER handling stopped state (allows final plot)
                     self.frame.after_idle(self.stop_animation)
                 else:
                     print("Recorder frame destroyed before handling stopped recording.")


            threading.Thread(target=stop_thread, daemon=True).start()

        else:
            print("Start recording requested.")
            self.is_recording = True
            self.waveform_data = np.array([], dtype=np.float32)
            self.clear_plot() # Clears plot visually

            self.record_button.config(text="■ Stop Recording")
            self.play_button.config(state=tk.DISABLED)
            self.last_saved_filepath = None
            # Start handler AFTER UI updates
            self.audio_handler.start_recording()

            self.start_animation() # Start plotting


    def _handle_recording_stopped(self, recorded_data):
        # ... (mostly same, ensures plot update) ...
        print("Handling stopped recording in main thread.")
        if not hasattr(self, 'frame') or not self.frame.winfo_exists():
             print("Frame destroyed before handling stopped recording.")
             return

        self.record_button.config(state=tk.NORMAL) # Re-enable record button

        if recorded_data is not None and len(recorded_data) > 0:
            print("Recorded data found, enabling play button and updating plot.")
            self.play_button.config(state=tk.NORMAL)
            # Update the internal buffer and plot one last time
            if self.canvas and self.line:
                self.waveform_data = recorded_data.flatten() # Use the complete final data
                self._update_waveform_plot(None) # Manually trigger final plot update
                self.canvas.draw_idle() # Explicit draw request
            self._save_recording() # Ask to save
        else:
            print("No recorded data found.")
            self.play_button.config(state=tk.DISABLED)
            self.update_status("Ready (No data recorded)")
            self.clear_plot() # Clear plot if no data


    def _toggle_play(self):
        # ... (mostly same, ensures plot update before play) ...
        if not self.canvas:
            messagebox.showerror("Plot Error", "Cannot play: waveform plot failed initialization.")
            return

        if self.is_playing:
            print("Stop playback requested.")
            self.audio_handler.stop_playback() # Handler callback will update state
        else:
            if self.audio_handler.has_recorded_data():
                print("Start playback requested.")
                self.is_playing = True
                self.play_button.config(text="■ Stop Playing")
                self.record_button.config(state=tk.DISABLED)
                self.update_status("Playing...")

                # Ensure the full recorded waveform is displayed before starting playback
                if self.canvas and self.line and self.audio_handler.audio_data is not None:
                     self.waveform_data = self.audio_handler.audio_data.flatten()
                     self._update_waveform_plot(None) # Manual update
                     self.canvas.draw_idle() # Force draw

                def play_thread():
                    print("Running start_playback in thread...")
                    self.audio_handler.start_playback() # This blocks the thread
                    print("start_playback finished in thread.")
                    if hasattr(self, 'frame') and self.frame.winfo_exists():
                        # Schedule finished handler
                        self.frame.after_idle(self._handle_playback_finished)
                    else:
                         print("Recorder frame destroyed before handling finished playback.")

                threading.Thread(target=play_thread, daemon=True).start()
            else:
                messagebox.showwarning("No Audio", "No recorded audio available to play.")

    def _handle_playback_finished(self):
         # ... (same as before) ...
         print("Handling finished playback in main thread.")
         self.is_playing = False
         if hasattr(self, 'play_button') and self.play_button.winfo_exists():
             self.play_button.config(text="▶ Play")
         if hasattr(self, 'record_button') and self.record_button.winfo_exists():
             if not self.is_recording:
                 self.record_button.config(state=tk.NORMAL)


    def _save_recording(self):
        # ... (same as before) ...
        if not self.audio_handler.has_recorded_data():
            messagebox.showerror("Error", "No recording data to save.")
            self.update_status("Ready (No data to save)")
            return

        filename = simpledialog.askstring("Save Recording", "Enter filename (without extension):", parent=self.frame)

        if filename:
            chosen_format = self.save_format.get()
            self.update_status(f"Saving as {chosen_format.upper()}...")
            self.record_button.config(state=tk.DISABLED)
            self.play_button.config(state=tk.DISABLED)

            def save_thread():
                print(f"Running save_audio in thread for {filename}.{chosen_format}...")
                saved_path, error_msg = self.audio_handler.save_audio(filename, chosen_format)
                print(f"save_audio finished. Path: {saved_path}, Error: {error_msg}")
                if hasattr(self, 'frame') and self.frame.winfo_exists():
                    self.frame.after_idle(self._handle_save_result, saved_path, error_msg)
                else:
                     print("Recorder frame destroyed before handling save result.")
            threading.Thread(target=save_thread, daemon=True).start()
        else:
            self.update_status("Save cancelled.")
            if self.audio_handler.has_recorded_data(): self.play_button.config(state=tk.NORMAL)
            self.record_button.config(state=tk.NORMAL)


    def _handle_save_result(self, saved_path, error_msg):
        # ... (same as before) ...
        print("Handling save result in main thread.")
        if not hasattr(self, 'frame') or not self.frame.winfo_exists(): return

        self.record_button.config(state=tk.NORMAL)
        if self.audio_handler.has_recorded_data(): self.play_button.config(state=tk.NORMAL)
        else: self.play_button.config(state=tk.DISABLED)

        if error_msg:
            messagebox.showerror("Save Error", error_msg)
            self.update_status("Save Error!")
        elif saved_path:
            self.last_saved_filepath = saved_path
            status_msg = f"Saved: {os.path.basename(saved_path)}"
            print(f"File saved successfully: {saved_path}")
            if messagebox.askyesno("Transcribe Audio?", f"{status_msg}\n\nSet this file for transcription?", parent=self.frame):
                if self.update_transcription_path_callback:
                    try:
                        self.update_transcription_path_callback(saved_path)
                        status_msg = f"File set for transcription."
                    except Exception as cb_error:
                         print(f"Error in transcription path callback: {cb_error}")
                         status_msg = f"Error setting transcription file."
                else:
                    print("Transcription path callback not set.")
            self.update_status(status_msg)
        else:
            self.update_status("Save completed (unknown state).")


    # --- Waveform Plotting Methods ---

    def start_animation(self):
        """Starts the waveform animation."""
        if not self.canvas: return
        if not self._animation_running:
            print("Starting waveform animation.")
            try:
                # --- FIX: Address UserWarning and ensure animation starts ---
                self.animation = FuncAnimation(
                    self.fig,
                    self._update_waveform_plot,
                    interval=self.ANIMATION_INTERVAL,
                    blit=False, # Keep blit=False for TkAgg robustness
                    cache_frame_data=False # Explicitly disable cache to silence warning
                )
                self._animation_running = True
                self.canvas.draw_idle() # Initial draw request
                print("Animation object created and flag set.")
            except Exception as e:
                print(f"Error starting FuncAnimation: {e}")
                self.animation = None
                self._animation_running = False
        # else:
        #     print("Animation already running or starting.")


    def stop_animation(self):
        """Stops the waveform animation."""
        if self._animation_running and self.animation is not None:
            try:
                print("Stopping waveform animation.")
                # Stop the animation's event source before clearing reference
                if hasattr(self.animation, 'event_source') and self.animation.event_source:
                    self.animation.event_source.stop()
                # Clear the reference
                self.animation = None
                self._animation_running = False
                print("Animation stopped and flag cleared.")
            except Exception as e:
                print(f"Error stopping animation: {e}")
                # Force reset state even if stop failed
                self.animation = None
                self._animation_running = False
        # Ensure flag is false if animation object was already None or stop failed
        self._animation_running = False


    def _check_audio_queue(self):
        """Periodically check the audio queue for new data from the handler."""
        # ... (same buffer logic as before) ...
        data_processed_this_cycle = False
        try:
            while True:
                chunk = self.audio_queue.get_nowait()
                if isinstance(chunk, np.ndarray):
                    self.waveform_data = np.append(self.waveform_data, chunk.flatten())
                    data_processed_this_cycle = True
                else: pass # Ignore non-array data

                if len(self.waveform_data) > self._max_buffer_samples:
                    excess = len(self.waveform_data) - self._max_buffer_samples
                    self.waveform_data = self.waveform_data[excess:]

        except queue.Empty: pass
        except Exception as e: print(f"Error processing audio queue: {e}")
        finally:
            # Reschedule ONLY if the frame still exists
            if hasattr(self, 'frame') and self.frame.winfo_exists():
                 self._schedule_queue_check() # Use helper to reschedule
            else:
                 self._check_audio_queue_id = None # Ensure no dangling reference


    def _update_waveform_plot(self, frame_num):
        """Called by FuncAnimation to update the plot."""
        # Add more robust checks at the beginning
        if not self._animation_running or not (self.canvas and self.ax and self.line):
            # print("Plot update skipped: Animation not running or plot elements missing.")
            return self.line or tuple() # Return existing artists or empty tuple

        try:
            # --- Get data to plot (same logic as before) ---
            current_data = self.waveform_data
            current_length_samples = len(current_data)
            sr = self.audio_handler.sample_rate if self.audio_handler else AudioHandler.DEFAULT_SAMPLE_RATE
            max_samples_to_display = int(self.MAX_WAVEFORM_SECONDS * sr)

            if current_length_samples == 0:
                plot_data = np.array([0.0]) # Single point at zero
                time_axis = np.array([0.0])
                time_offset = 0
            elif current_length_samples > max_samples_to_display:
                plot_data = current_data[-max_samples_to_display:]
                start_sample_index = current_length_samples - max_samples_to_display
                time_axis = np.arange(max_samples_to_display) / sr # Relative time 0 to MAX_SECS
                time_offset = start_sample_index / sr # Absolute start time of this window
            else:
                plot_data = current_data
                time_axis = np.arange(current_length_samples) / sr
                time_offset = 0

            # --- Debug Print (Optional) ---
            # if frame_num % 10 == 0: # Print every 10 frames
            #      print(f"Plot Update: Frame {frame_num}, BufLen={current_length_samples}, PlotLen={len(plot_data)}, Offset={time_offset:.2f}")


            # --- Update plot ---
            self.line.set_data(time_axis + time_offset, plot_data)

            # --- Adjust X limits ---
            if current_length_samples == 0:
                display_start_time = 0
                display_end_time = self.MAX_WAVEFORM_SECONDS # Show full default window
            elif current_length_samples > max_samples_to_display:
                 display_end_time = current_length_samples / sr # Absolute end time
                 display_start_time = display_end_time - self.MAX_WAVEFORM_SECONDS
            else:
                 display_start_time = 0
                 # Expand end time, but ensure it's at least MAX_WAVEFORM_SECONDS wide if possible
                 display_end_time = max(current_length_samples / sr, self.MAX_WAVEFORM_SECONDS) if sr > 0 else self.MAX_WAVEFORM_SECONDS

            # Prevent setting identical limits which can cause issues
            if abs(display_start_time - display_end_time) < 1e-6: # If limits are virtually the same
                 display_end_time += 0.1 # Add a small amount

            self.ax.set_xlim(display_start_time, display_end_time)

            # --- Force Redraw (Moved Here) ---
            # Although FuncAnimation should handle drawing with blit=False,
            # explicitly requesting it can sometimes resolve update issues in TkAgg.
            # Do this *after* setting data and limits.
            self.canvas.draw_idle()

        except Exception as e:
             print(f"Error during plot update (_update_waveform_plot frame {frame_num}): {e}")
             # import traceback
             # traceback.print_exc() # More detailed error
             # self.stop_animation() # Consider stopping animation if errors persist

        return self.line, # Return the updated artists


    def clear_plot(self):
        # ... (same as before, added checks) ...
         self.waveform_data = np.array([], dtype=np.float32)
         if self.line:
             try: self.line.set_data([0], [0]) # Set to single point instead of empty
             except Exception as e: print(f"Error clearing plot line data: {e}")
         if self.ax:
             try:
                 self.ax.set_xlim(0, self.MAX_WAVEFORM_SECONDS)
                 self.ax.set_ylim(-1.05, 1.05)
             except Exception as e: print(f"Error resetting plot axes limits: {e}")
         if self.canvas:
             try: self.canvas.draw_idle()
             except Exception as e: print(f"Error drawing idle canvas: {e}")


    def on_close(self):
        # ... (same as before) ...
        print("Closing Recorder Tab...")
        if hasattr(self, '_check_audio_queue_id') and self._check_audio_queue_id:
             try:
                 if self.frame.winfo_exists(): self.frame.after_cancel(self._check_audio_queue_id)
                 print("Cancelled audio queue check.")
             except Exception as e: print(f"Error cancelling queue check: {e}")
             self._check_audio_queue_id = None

        self.stop_animation()

        if self.audio_handler:
            if self.is_recording:
                 print("Stopping recording on close...")
                 self.audio_handler.stop_recording()
            if self.is_playing:
                 print("Stopping playback on close...")
                 self.audio_handler.stop_playback()

        try:
             if self.fig: plt.close(self.fig); print("Matplotlib figure closed."); self.fig = None
        except Exception as e: print(f"Error closing Matplotlib figure: {e}")

# --- END OF MODIFIED FILE recorder_tab.py ---