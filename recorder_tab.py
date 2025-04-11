# --- START OF REVISED recorder_tab.py ---

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import numpy as np
import threading
import queue
import os
import sys
import time
import math
import typing # Added for type hinting

from audio_handler import AudioHandler

# Added for type hinting gui_app
if typing.TYPE_CHECKING:
    from gui import ModernTranscriptionApp

# --- DEBUG FLAG ---
DEBUG_CANVAS = False # Set True for detailed logs

class RecorderTab:
    MAX_WAVEFORM_SECONDS = 10
    CANVAS_UPDATE_INTERVAL = 35 # ms
    MAX_DATA_BUFFER_SECONDS = 11

    # Colors
    BG_COLOR = '#f0f0f0'
    CANVAS_BG_COLOR = '#ffffff'
    WAVEFORM_COLOR = 'cornflowerblue'
    CENTER_LINE_COLOR = 'red'
    SILENCE_LINE_COLOR = '#aaaaaa'

    # Audio Parameter Options
    SAMPLE_RATES = [8000, 16000, 22050, 44100, 48000] # Common rates
    CHANNELS_MAP = {"Mono": 1, "Stereo": 2}
    CHANNELS_MAP_REV = {1: "Mono", 2: "Stereo"} # Reverse mapping for UI updates

    # Pass gui_app for translations
    def __init__(self, parent_notebook: ttk.Notebook, gui_app: 'ModernTranscriptionApp', update_transcription_path_callback):
        self.parent = parent_notebook # This is the ttk.Notebook
        self.gui_app = gui_app # Reference to the main app instance
        self.update_transcription_path_callback = update_transcription_path_callback
        self.is_recording = False
        self.is_playing = False
        self.save_format = tk.StringVar(value="wav")
        self.status_text = tk.StringVar(value="") # Set in update_ui_text
        self.last_saved_filepath = None # Store path of last saved file
        self.last_loaded_filepath = None # Store path of last loaded file

        # Waveform data handling
        self.waveform_data = np.array([], dtype=np.float32)
        self._max_buffer_samples = 0
        self._max_samples_to_display = 0
        self._check_audio_queue_id = None
        self._update_canvas_id = None

        # Timers and state
        self._current_playback_time = 0.0
        self._recording_start_time = 0.0
        self._timer_id = None # For time display update

        # Tkinter Variables for Audio Settings (initialized with defaults)
        self.selected_sample_rate = tk.IntVar(value=AudioHandler.DEFAULT_SAMPLE_RATE)
        # Find default channel string from map
        default_channel_str = self.CHANNELS_MAP_REV.get(AudioHandler.DEFAULT_CHANNELS, "Mono")
        self.selected_channels_str = tk.StringVar(value=default_channel_str)

        # Initialize AudioHandler with defaults
        self.audio_handler = AudioHandler(
            status_callback=self.update_status, # Use local method
            initial_sample_rate=self.selected_sample_rate.get(),
            initial_channels=self.CHANNELS_MAP.get(self.selected_channels_str.get(), 1)
        )
        self.audio_queue = self.audio_handler.get_audio_data_queue()
        # Update internal params based on handler's actual initial params
        self._update_buffer_params()

        # --- UI Setup ---
        self.frame = ttk.Frame(parent_notebook, padding="10")
        # self.frame.grid(row=0, column=0, sticky="nsew") # Frame is added to notebook, no grid needed here
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1) # Make canvas row expand

        self._create_widgets() # Call helper to create widgets

        # Initial setup after layout is calculated
        self.frame.after_idle(self._initial_canvas_setup)

    def _create_widgets(self):
        """Creates the widgets for the recorder tab."""
        # --- Controls Frame ---
        controls_frame = ttk.Frame(self.frame)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        controls_frame.columnconfigure(5, weight=1) # Status label expansion

        # Row 0: Buttons, Format, Status
        self.record_button = ttk.Button(controls_frame, text="", command=self._toggle_record, style="Primary.TButton", width=14) # TEXT REMOVED
        self.record_button.grid(row=0, column=0, padx=(0,5), pady=2)
        self.play_button = ttk.Button(controls_frame, text="", command=self._toggle_play, style="Action.TButton", width=14) # TEXT REMOVED
        self.play_button.grid(row=0, column=1, padx=5, pady=2)
        self.play_button.config(state=tk.DISABLED) # Initially disabled
        self.load_button = ttk.Button(controls_frame, text="", command=self._load_audio_file, style="Action.TButton", width=12) # TEXT REMOVED
        self.load_button.grid(row=0, column=2, padx=5, pady=2)

        # Save Format Frame
        self.format_frame = ttk.LabelFrame(controls_frame, text="", padding=(5, 2)) # TEXT REMOVED
        self.format_frame.grid(row=0, column=3, padx=10, pady=2, sticky='w')
        self.wav_radio = ttk.Radiobutton(self.format_frame, text="WAV", variable=self.save_format, value="wav") # Static text ok
        self.wav_radio.pack(side=tk.LEFT, padx=2)
        self.mp3_radio = ttk.Radiobutton(self.format_frame, text="MP3", variable=self.save_format, value="mp3") # Static text ok
        self.mp3_radio.pack(side=tk.LEFT, padx=2)

        # Status Label
        self.status_label = ttk.Label(controls_frame, textvariable=self.status_text, anchor=tk.E, style="Status.TLabel")
        self.status_label.grid(row=0, column=5, padx=5, pady=2, sticky='ew')

        # --- Options Frame ---
        self.options_frame = ttk.LabelFrame(self.frame, text="", padding=(10, 5)) # TEXT REMOVED
        self.options_frame.grid(row=1, column=0, sticky="ew", pady=(5, 10))

        self.sr_label = ttk.Label(self.options_frame, text="") # TEXT REMOVED
        self.sr_label.pack(side=tk.LEFT, padx=(0, 5))
        self.sr_combo = ttk.Combobox(self.options_frame, textvariable=self.selected_sample_rate, values=self.SAMPLE_RATES, width=8, state='readonly')
        self.sr_combo.pack(side=tk.LEFT, padx=5)
        self.sr_combo.bind("<<ComboboxSelected>>", self._on_settings_changed)

        self.ch_label = ttk.Label(self.options_frame, text="") # TEXT REMOVED
        self.ch_label.pack(side=tk.LEFT, padx=(15, 5))
        self.ch_combo = ttk.Combobox(self.options_frame, textvariable=self.selected_channels_str, values=list(self.CHANNELS_MAP.keys()), width=7, state='readonly')
        self.ch_combo.pack(side=tk.LEFT, padx=5)
        self.ch_combo.bind("<<ComboboxSelected>>", self._on_settings_changed)

        # Time Display Label
        self.time_label = ttk.Label(self.options_frame, text="...", font=("Segoe UI", 10, "bold")) # Placeholder text
        self.time_label.pack(side=tk.RIGHT, padx=(10, 0))

        # --- Waveform Canvas Frame ---
        canvas_frame = ttk.Frame(self.frame, borderwidth=1, relief="sunken")
        canvas_frame.grid(row=2, column=0, sticky="nsew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.waveform_canvas = tk.Canvas(canvas_frame, bg=self.CANVAS_BG_COLOR, highlightthickness=0)
        self.waveform_canvas.grid(row=0, column=0, sticky="nsew")
        self.waveform_canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas_width = 0
        self.canvas_height = 0
        self._static_elements_drawn = False


    def _initial_canvas_setup(self):
        """Perform initial canvas setup after widgets are mapped."""
        if self.waveform_canvas and self.waveform_canvas.winfo_exists():
            if DEBUG_CANVAS: print("CANVAS INIT: Canvas created.")
            self._on_canvas_resize() # Calculate initial size
            self.clear_plot() # Draw static elements
            self._schedule_queue_check() # Start checking for audio data
            self.update_ui_text() # Set initial text for labels/buttons
        else:
             if DEBUG_CANVAS: print("CANVAS INIT ERROR: Failed to create canvas.")


    def update_ui_text(self):
        """Updates widget text based on GUI language."""
        # print(f"DEBUG: recorder_tab.update_ui_text called for lang {self.gui_app.current_language.get()}")
        if not hasattr(self, 'frame') or not self.frame.winfo_exists(): return

        try:
            # Update button texts based on state
            if hasattr(self, 'record_button') and self.record_button.winfo_exists():
                rec_text_key = "record_button_stop" if self.is_recording else "record_button_start"
                self.record_button.config(text=self.gui_app.translate(rec_text_key))

            if hasattr(self, 'play_button') and self.play_button.winfo_exists():
                play_text_key = "play_button_stop" if self.is_playing else "play_button_start"
                self.play_button.config(text=self.gui_app.translate(play_text_key))

            if hasattr(self, 'load_button') and self.load_button.winfo_exists():
                self.load_button.config(text=self.gui_app.translate("load_audio_button"))

            # Update LabelFrame texts
            if hasattr(self, 'format_frame') and self.format_frame.winfo_exists():
                self.format_frame.config(text=self.gui_app.translate("save_format_label"))
                # Radiobutton text is static (WAV/MP3), no translation needed currently

            if hasattr(self, 'options_frame') and self.options_frame.winfo_exists():
                 self.options_frame.config(text=self.gui_app.translate("audio_options_label"))
                 # Update labels inside options_frame
                 if hasattr(self, 'sr_label') and self.sr_label.winfo_exists():
                      self.sr_label.config(text=self.gui_app.translate("sample_rate_label"))
                 if hasattr(self, 'ch_label') and self.ch_label.winfo_exists():
                      self.ch_label.config(text=self.gui_app.translate("channels_label"))

            # Update status if "Ready" or empty
            current_status = self.status_text.get()
            is_ready_or_empty = not current_status
            if not is_ready_or_empty:
                 for lang_code in self.gui_app.translations:
                     # Use specific recorder ready status key
                     ready_text = self.gui_app.translations[lang_code].get('recorder_status_ready')
                     if ready_text and current_status == ready_text:
                         is_ready_or_empty = True
                         break
            if is_ready_or_empty:
                 self.status_text.set(self.gui_app.translate("recorder_status_ready"))

            # Update Time label prefix (if time label exists)
            if hasattr(self, 'time_label') and self.time_label.winfo_exists():
                 self._update_time_display(self.audio_handler.get_audio_duration()) # Update with current duration

        except tk.TclError as e:
            print(f"Recorder Tab: TclError during update_ui_text: {e}", file=sys.__stderr__)
        except Exception as e:
            import traceback
            print(f"Recorder Tab: Unexpected error during update_ui_text: {e}\n{traceback.format_exc()}", file=sys.__stderr__)


    def _update_buffer_params(self):
        """Update buffer sizes based on current sample rate from audio_handler."""
        sr, _ = self.audio_handler.get_current_parameters()
        self.sample_rate = sr
        self._max_buffer_samples = int(self.MAX_DATA_BUFFER_SECONDS * self.sample_rate)
        self._max_samples_to_display = int(self.MAX_WAVEFORM_SECONDS * self.sample_rate)
        if DEBUG_CANVAS: print(f"PARAMS UPDATE: SR={self.sample_rate}, MaxBuf={self._max_buffer_samples}, MaxDisp={self._max_samples_to_display}")


    def _schedule_queue_check(self):
        if self._check_audio_queue_id:
            try: self.frame.after_cancel(self._check_audio_queue_id)
            except (ValueError, tk.TclError): pass
        if hasattr(self, 'frame') and self.frame.winfo_exists():
            self._check_audio_queue_id = self.frame.after(self.CANVAS_UPDATE_INTERVAL // 2, self._check_audio_queue)


    def update_status(self, message):
        """Callback for AudioHandler status updates."""
        try:
            if hasattr(self, 'frame') and self.frame.winfo_exists():
                self.frame.after_idle(lambda m=message: self.status_text.set(m))
        except Exception as e:
            print(f"Error updating status label: {e}", file=sys.__stderr__)

    # --- Canvas Drawing Logic ---
    def _on_canvas_resize(self, event=None):
        if not (hasattr(self, 'waveform_canvas') and self.waveform_canvas.winfo_exists()): return
        new_width = self.waveform_canvas.winfo_width(); new_height = self.waveform_canvas.winfo_height()
        if new_width > 1 and new_height > 1 and (abs(new_width - self.canvas_width) > 5 or abs(new_height - self.canvas_height) > 5 or not self._static_elements_drawn):
            self.canvas_width = new_width; self.canvas_height = new_height
            if DEBUG_CANVAS: print(f"CANVAS RESIZE: New dimensions W={self.canvas_width}, H={self.canvas_height}")
            self._draw_static_canvas_elements()
            if not self.is_recording and not self.is_playing:
                 display_data = self.waveform_data[-self._max_samples_to_display:]
                 self._draw_waveform_on_canvas(display_data)

    def _draw_static_canvas_elements(self):
        if not (self.waveform_canvas and self.canvas_width > 0 and self.canvas_height > 0): return
        self.waveform_canvas.delete("static_line")
        y_center = self.canvas_height / 2
        self.waveform_canvas.create_line(0, y_center, self.canvas_width, y_center, fill=self.SILENCE_LINE_COLOR, width=1, tags="static_line")
        x_center = self.canvas_width / 2
        self.waveform_canvas.create_line(x_center, 0, x_center, self.canvas_height, fill=self.CENTER_LINE_COLOR, width=1, dash=(4, 2), tags="static_line")
        self._static_elements_drawn = True

    def _draw_waveform_on_canvas(self, data_to_draw):
        if not (self.waveform_canvas and self.canvas_width > 0 and self.canvas_height > 0): return
        self.waveform_canvas.delete("waveform")
        num_samples = len(data_to_draw)
        if num_samples < 2: return

        y_center = self.canvas_height / 2; y_scaling = self.canvas_height / 2 * 0.95
        step = max(1, int(num_samples / self.canvas_width)) if self.canvas_width > 0 else 1
        indices = np.arange(0, num_samples, step)
        sampled_data = data_to_draw[indices]
        x_coords = np.linspace(0, self.canvas_width, len(indices), endpoint=True)
        y_coords = y_center - (np.clip(sampled_data, -1.0, 1.0) * y_scaling)
        coords = np.empty(len(indices) * 2, dtype=np.float64); coords[0::2] = x_coords; coords[1::2] = y_coords

        if len(coords) >= 4:
            self.waveform_canvas.create_line(coords.tolist(), fill=self.WAVEFORM_COLOR, width=1, tags="waveform")

    # --- Settings Change Handler ---
    def _on_settings_changed(self, event=None):
        if self.is_recording or self.is_playing:
             messagebox.showwarning(self.gui_app.translate("warning_title"),
                                    self.gui_app.translate("recorder_warn_settings_busy"),
                                    parent=self.frame)
             sr, ch = self.audio_handler.get_current_parameters()
             self.selected_sample_rate.set(sr)
             ch_str = self.CHANNELS_MAP_REV.get(ch, "Mono")
             self.selected_channels_str.set(ch_str)
             return

        try:
             new_sr = self.selected_sample_rate.get()
             new_ch_str = self.selected_channels_str.get()
             new_ch = self.CHANNELS_MAP.get(new_ch_str, 1)

             if DEBUG_CANVAS: print(f"SETTINGS CHANGED: User selected SR={new_sr}, Ch={new_ch}")
             success = self.audio_handler.set_audio_parameters(new_sr, new_ch)
             if success:
                 self._update_buffer_params()
                 self.update_status(f"{self.gui_app.translate('recorder_status_settings')}: {new_sr} Hz, {new_ch_str}")
             else:
                 messagebox.showerror(self.gui_app.translate("error_title"),
                                       self.gui_app.translate("recorder_error_settings_apply"),
                                       parent=self.frame)
                 sr, ch = self.audio_handler.get_current_parameters()
                 self.selected_sample_rate.set(sr)
                 ch_str = self.CHANNELS_MAP_REV.get(ch, "Mono")
                 self.selected_channels_str.set(ch_str)
        except Exception as e:
             print(f"Error handling settings change: {e}", file=sys.__stderr__)
             messagebox.showerror(self.gui_app.translate("error_title"), f"Invalid audio settings selected: {e}", parent=self.frame)


    # --- Recording / Playback / Load Logic ---

    def _toggle_record(self):
        if not (hasattr(self, 'waveform_canvas') and self.waveform_canvas.winfo_exists()):
            messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("recorder_error_no_canvas"), parent=self.frame); return

        if self.is_recording:
            # --- Stop Recording ---
            if DEBUG_CANVAS: print("TOGGLE RECORD: Stopping...")
            self.is_recording = False
            self.stop_canvas_update_loop()
            self.stop_timer()
            self._set_controls_state(recording=False, playing=False, busy=True)
            self.update_status(self.gui_app.translate("recorder_status_processing"))

            def stop_thread():
                 if DEBUG_CANVAS: print("STOP THREAD: Calling handler stop_recording...")
                 recorded_data = self.audio_handler.stop_recording()
                 if DEBUG_CANVAS: print(f"STOP THREAD: Handler finished. Data len: {len(recorded_data) if recorded_data is not None else 'None'}")
                 if hasattr(self, 'frame') and self.frame.winfo_exists():
                     self.frame.after_idle(self._handle_recording_stopped, recorded_data)
                 else: print("STOP THREAD: Recorder frame destroyed.", file=sys.__stderr__)
            threading.Thread(target=stop_thread, daemon=True).start()

        else:
            # --- Start Recording ---
            sr = self.selected_sample_rate.get()
            ch_str = self.selected_channels_str.get()
            ch = self.CHANNELS_MAP.get(ch_str, 1)
            if not self.audio_handler.set_audio_parameters(sr, ch):
                 messagebox.showerror(self.gui_app.translate("error_title"),
                                       self.gui_app.translate("recorder_error_settings_apply"),
                                       parent=self.frame)
                 return
            self._update_buffer_params()

            if DEBUG_CANVAS: print("TOGGLE RECORD: Starting...")
            self.is_recording = True
            self.waveform_data = np.array([], dtype=np.float32)
            self.clear_plot()
            self._set_controls_state(recording=True, playing=False, busy=False)
            self.last_saved_filepath = None
            self.last_loaded_filepath = None

            self.audio_handler.start_recording()
            # Small delay to check if handler status updated correctly
            self.frame.after(100, self._check_recording_start_status)


    def _check_recording_start_status(self):
        """Check if recording actually started after a short delay."""
        if not self.is_recording: return # Already stopped or failed before check

        # Check status text set by the handler via callback
        # Use the English version for comparison as a fallback if translation fails
        expected_status = self.gui_app.translate("recorder_status_recording")
        if not expected_status.startswith("<"): # Ensure translation key exists
            if expected_status not in self.status_text.get():
                 print(f"Warning: Recording status mismatch. Expected something like '{expected_status}', got '{self.status_text.get()}'. Handler might have failed.")
                 # Assume failure if status isn't "Recording..."
                 self.is_recording = False
                 self._set_controls_state(recording=False, playing=False, busy=False)
                 # Status label should show the error from the handler callback
                 return

        # If status seems ok, proceed with timer and canvas updates
        self._recording_start_time = time.monotonic()
        self.start_timer()
        self.start_canvas_update_loop()


    def _set_controls_state(self, recording: bool, playing: bool, busy: bool, has_data: typing.Optional[bool] = None):
        """Helper to enable/disable controls based on state."""
        if not hasattr(self, 'frame') or not self.frame.winfo_exists(): return

        is_idle = not recording and not playing and not busy
        # Determine if data is available for playback
        can_play = has_data if has_data is not None else (self.audio_handler.has_recorded_data())

        rec_state = tk.DISABLED if (playing or busy) else tk.NORMAL
        play_state = tk.DISABLED if (recording or busy or not can_play) else tk.NORMAL
        load_state = tk.DISABLED if (recording or playing or busy) else tk.NORMAL
        settings_state = 'disabled' if (recording or playing or busy) else 'readonly'

        try:
            if hasattr(self, 'record_button'): self.record_button.config(state=rec_state)
            if hasattr(self, 'play_button'): self.play_button.config(state=play_state)
            if hasattr(self, 'load_button'): self.load_button.config(state=load_state)
            if hasattr(self, 'sr_combo'): self.sr_combo.config(state=settings_state)
            if hasattr(self, 'ch_combo'): self.ch_combo.config(state=settings_state)
            # Update button text via update_ui_text (called AFTER setting state vars like is_recording)
            self.update_ui_text()
        except tk.TclError as e:
            print(f"Recorder Tab: TclError setting control state: {e}", file=sys.__stderr__)


    def _handle_recording_stopped(self, recorded_data):
        if DEBUG_CANVAS: print("HANDLE STOPPED: Updating UI...")
        if not hasattr(self, 'frame') or not self.frame.winfo_exists(): return

        has_data = recorded_data is not None and len(recorded_data) > 0

        if has_data:
            if DEBUG_CANVAS: print("HANDLE STOPPED: Data found.")
            self.waveform_data = recorded_data.flatten() if recorded_data.ndim > 1 else recorded_data
            if self.waveform_canvas:
                display_data = self.waveform_data[-self._max_samples_to_display:]
                if DEBUG_CANVAS: print("HANDLE STOPPED: Manual draw for final view.")
                self._draw_waveform_on_canvas(display_data)
            final_duration = self.audio_handler.get_audio_duration()
            self._update_time_display(final_duration)
            self._save_recording() # Will eventually call _set_controls_state
        else:
            if DEBUG_CANVAS: print("HANDLE STOPPED: No data found.")
            self.update_status(self.gui_app.translate("recorder_status_no_data"))
            self.clear_plot()
            self._update_time_display(0)
            self._set_controls_state(recording=False, playing=False, busy=False, has_data=False)

    def _toggle_play(self):
        if not (hasattr(self, 'waveform_canvas') and self.waveform_canvas.winfo_exists()):
            messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("recorder_error_no_canvas"), parent=self.frame); return

        if self.is_playing:
            # --- Stop Playback ---
            if DEBUG_CANVAS: print("TOGGLE PLAY: Stopping...")
            self.is_playing = False
            self.stop_timer()
            self.audio_handler.stop_playback()
            # UI state is set by _handle_playback_finished or status update from handler
            self._set_controls_state(recording=False, playing=False, busy=True) # Brief busy state
            # Schedule check in case handler doesn't update status quickly
            self.frame.after(100, lambda: self._set_controls_state(recording=False, playing=False, busy=False, has_data=self.audio_handler.has_recorded_data()))

        else:
            # --- Start Playback ---
            if self.audio_handler.has_recorded_data():
                if DEBUG_CANVAS: print("TOGGLE PLAY: Starting...")
                self.is_playing = True
                self._set_controls_state(recording=False, playing=True, busy=False)
                self.stop_canvas_update_loop()

                if self.waveform_canvas and self.audio_handler.audio_data is not None:
                    if DEBUG_CANVAS: print("TOGGLE PLAY: Displaying full static waveform.")
                    full_data = self.audio_handler.audio_data.flatten() if self.audio_handler.audio_data.ndim > 1 else self.audio_handler.audio_data
                    duration = self.audio_handler.get_audio_duration()
                    self.clear_plot()
                    self._draw_waveform_on_canvas(full_data)
                    self._update_time_display(duration)

                def play_thread():
                    if DEBUG_CANVAS: print("PLAY THREAD: Calling handler start_playback...")
                    self.audio_handler.start_playback() # Blocking call
                    if DEBUG_CANVAS: print("PLAY THREAD: Handler finished.")
                    if hasattr(self, 'frame') and self.frame.winfo_exists():
                        self.frame.after_idle(self._handle_playback_finished)
                    else: print("PLAY THREAD: Recorder frame destroyed.", file=sys.__stderr__)
                threading.Thread(target=play_thread, daemon=True).start()
            else:
                messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("recorder_warn_no_audio_play"), parent=self.frame)


    def _handle_playback_finished(self):
         if DEBUG_CANVAS: print("HANDLE PLAYBACK FINISHED: Updating UI...")
         self.is_playing = False
         self.stop_timer()

         if self.waveform_canvas and self.audio_handler.audio_data is not None:
             if DEBUG_CANVAS: print("HANDLE PLAYBACK FINISHED: Restoring display waveform.")
             full_data = self.audio_handler.audio_data.flatten() if self.audio_handler.audio_data.ndim > 1 else self.audio_handler.audio_data
             duration = self.audio_handler.get_audio_duration()
             self.clear_plot()
             self._draw_waveform_on_canvas(full_data)
             self._update_time_display(duration)

         self._set_controls_state(recording=False, playing=False, busy=False, has_data=True)
         # Status might be set by handler, but set a fallback here
         self.update_status(self.gui_app.translate("recorder_status_playback_finished"))


    def _load_audio_file(self):
        if self.is_recording or self.is_playing:
             messagebox.showwarning(self.gui_app.translate("warning_title"), self.gui_app.translate("recorder_warn_load_busy"), parent=self.frame)
             return

        file_types = [
            (self.gui_app.translate("audio_files_label"), "*.wav *.mp3 *.flac *.ogg"),
            (self.gui_app.translate("all_files_label"), "*.*")
        ]
        filepath = filedialog.askopenfilename(
            title=self.gui_app.translate("load_audio_title"),
            filetypes=file_types,
            parent=self.frame
        )
        if not filepath: return

        if DEBUG_CANVAS: print(f"LOAD AUDIO: User selected '{filepath}'")
        self.update_status(self.gui_app.translate("recorder_status_loading"))
        self._set_controls_state(recording=False, playing=False, busy=True)
        self.stop_canvas_update_loop()

        def load_thread():
            success, error_msg = self.audio_handler.load_audio(filepath)
            loaded_path = filepath if success else None
            if hasattr(self, 'frame') and self.frame.winfo_exists():
                self.frame.after_idle(self._handle_load_result, success, error_msg, loaded_path)
            else: print("LOAD AUDIO THREAD: Frame destroyed.", file=sys.__stderr__)
        threading.Thread(target=load_thread, daemon=True).start()


    def _handle_load_result(self, success, error_msg, loaded_path):
        if DEBUG_CANVAS: print(f"HANDLE LOAD RESULT: Success={success}, Error='{error_msg}', Path='{loaded_path}'")

        if success and loaded_path:
            self.last_loaded_filepath = loaded_path
            self.last_saved_filepath = None
            self.waveform_data = self.audio_handler.audio_data.flatten() if self.audio_handler.audio_data.ndim > 1 else self.audio_handler.audio_data

            sr, ch = self.audio_handler.get_current_parameters()
            self.selected_sample_rate.set(sr)
            ch_str = self.CHANNELS_MAP_REV.get(ch, "Mono")
            self.selected_channels_str.set(ch_str)
            self._update_buffer_params()

            self.clear_plot()
            self._draw_waveform_on_canvas(self.waveform_data)

            self.stop_timer()
            duration = self.audio_handler.get_audio_duration()
            self._update_time_display(duration)
            self.update_status(f"{self.gui_app.translate('recorder_status_loaded')}: {os.path.basename(loaded_path)}")
            self._set_controls_state(recording=False, playing=False, busy=False, has_data=True)

        else:
            self.last_loaded_filepath = None
            messagebox.showerror(self.gui_app.translate("error_title"), error_msg or self.gui_app.translate("recorder_error_load_generic"), parent=self.frame)
            self.update_status(self.gui_app.translate("recorder_status_load_failed"))
            self.clear_plot()
            self._update_time_display(0)
            self._set_controls_state(recording=False, playing=False, busy=False, has_data=False)


    def _save_recording(self):
        if not self.audio_handler.has_recorded_data():
             messagebox.showerror(self.gui_app.translate("error_title"), self.gui_app.translate("recorder_error_no_data_save"), parent=self.frame)
             self.update_status(self.gui_app.translate("recorder_status_ready"))
             self._set_controls_state(recording=False, playing=False, busy=False, has_data=False)
             return

        filename = simpledialog.askstring(self.gui_app.translate("save_recording_title"),
                                          self.gui_app.translate("save_recording_prompt"),
                                          parent=self.frame)
        if filename:
            chosen_format = self.save_format.get()
            self.update_status(f"{self.gui_app.translate('recorder_status_saving')} {chosen_format.upper()}...")
            self._set_controls_state(recording=False, playing=False, busy=True)

            def save_thread():
                if DEBUG_CANVAS: print(f"SAVE THREAD: Calling handler save_audio ({filename}.{chosen_format})...")
                saved_path, error_msg = self.audio_handler.save_audio(filename, chosen_format)
                if DEBUG_CANVAS: print(f"SAVE THREAD: Handler finished. Path: {saved_path}, Err: {error_msg}")
                if hasattr(self, 'frame') and self.frame.winfo_exists():
                    self.frame.after_idle(self._handle_save_result, saved_path, error_msg)
                else: print("SAVE THREAD: Recorder frame destroyed.", file=sys.__stderr__)
            threading.Thread(target=save_thread, daemon=True).start()

        else:
            self.update_status(self.gui_app.translate("recorder_status_save_cancelled"))
            self._set_controls_state(recording=False, playing=False, busy=False, has_data=True)


    def _handle_save_result(self, saved_path, error_msg):
        if DEBUG_CANVAS: print("HANDLE SAVE RESULT: Updating UI...")
        has_data = self.audio_handler.has_recorded_data()

        if error_msg:
            messagebox.showerror(self.gui_app.translate("error_title"), error_msg, parent=self.frame)
            status_msg = self.gui_app.translate("recorder_status_save_error")
        elif saved_path:
            self.last_saved_filepath = saved_path
            self.last_loaded_filepath = None
            status_msg = f"{self.gui_app.translate('recorder_status_saved')}: {os.path.basename(saved_path)}"
            print(f"File saved successfully: {saved_path}")

            if messagebox.askyesno(self.gui_app.translate("transcribe_audio_q_title"),
                                   self.gui_app.translate("transcribe_audio_q_msg").format(filename=os.path.basename(saved_path)),
                                   parent=self.frame):
                if self.update_transcription_path_callback:
                    try:
                        self.update_transcription_path_callback(saved_path)
                        status_msg = self.gui_app.translate("recorder_status_set_for_transcription")
                    except Exception as cb_error:
                        print(f"Error in transcription path callback: {cb_error}", file=sys.__stderr__)
                        status_msg = self.gui_app.translate("recorder_error_set_for_transcription")
                else:
                    print("Transcription path callback not set.", file=sys.__stderr__)
        else:
            status_msg = self.gui_app.translate("recorder_status_save_unknown")

        self.update_status(status_msg)
        self._set_controls_state(recording=False, playing=False, busy=False, has_data=has_data)


    # --- Canvas Update Loop & Timer ---

    def start_canvas_update_loop(self):
        if self._update_canvas_id is None:
            if DEBUG_CANVAS: print("CANVAS LOOP: Starting update loop.")
            self._schedule_canvas_update()

    def stop_canvas_update_loop(self):
        if self._update_canvas_id is not None:
            if DEBUG_CANVAS: print("CANVAS LOOP: Stopping update loop.")
            try:
                if hasattr(self, 'frame') and self.frame.winfo_exists():
                    self.frame.after_cancel(self._update_canvas_id)
            except (ValueError, tk.TclError): pass
            self._update_canvas_id = None

    def _schedule_canvas_update(self):
        if hasattr(self, 'frame') and self.frame.winfo_exists() and hasattr(self, 'waveform_canvas') and self.waveform_canvas.winfo_exists() and self.is_recording:
             self._update_canvas_id = self.frame.after(self.CANVAS_UPDATE_INTERVAL, self._update_waveform_canvas)
        else:
             self._update_canvas_id = None

    def _update_waveform_canvas(self):
        if not self.is_recording or self._update_canvas_id is None or not hasattr(self, 'waveform_canvas') or not self.waveform_canvas.winfo_exists():
            self._update_canvas_id = None; return
        current_data = self.waveform_data
        num_samples_in_buffer = len(current_data)
        start_index = max(0, num_samples_in_buffer - self._max_samples_to_display)
        plot_data = current_data[start_index:]
        self._draw_waveform_on_canvas(plot_data)
        self._schedule_canvas_update()

    # --- Data Queue Handling ---
    def _check_audio_queue(self):
        new_samples_count = 0
        try:
            max_chunks_per_cycle = 10
            for _ in range(max_chunks_per_cycle):
                chunk = self.audio_queue.get_nowait()
                if isinstance(chunk, np.ndarray):
                    flat_chunk = chunk.flatten()
                    new_samples_count += len(flat_chunk)
                    self.waveform_data = np.append(self.waveform_data, flat_chunk)
        except queue.Empty: pass
        except Exception as e: print(f"QUEUE ERROR processing audio chunk: {e}", file=sys.__stderr__)
        finally:
            if len(self.waveform_data) > self._max_buffer_samples:
                self.waveform_data = self.waveform_data[-self._max_buffer_samples:]
            if hasattr(self, 'frame') and self.frame.winfo_exists():
                 self._schedule_queue_check()
            else: self._check_audio_queue_id = None

    # --- Timer for Recording/Playback Time ---
    def start_timer(self):
        self.stop_timer()
        if DEBUG_CANVAS: print("TIMER: Starting timer.")
        self._update_time_label()

    def stop_timer(self):
        if self._timer_id is not None:
             if DEBUG_CANVAS: print("TIMER: Stopping timer.")
             try:
                 if hasattr(self, 'frame') and self.frame.winfo_exists():
                     self.frame.after_cancel(self._timer_id)
             except (ValueError, tk.TclError): pass
             self._timer_id = None


    def _update_time_label(self):
        if not (hasattr(self, 'frame') and self.frame.winfo_exists()):
             self._timer_id = None; return

        current_time_sec = 0.0
        if self.is_recording:
             current_time_sec = time.monotonic() - self._recording_start_time
        elif self.is_playing:
             current_time_sec = self.audio_handler.get_audio_duration()
        else:
             current_time_sec = self.audio_handler.get_audio_duration()

        self._update_time_display(current_time_sec)

        if self.is_recording:
             if hasattr(self, 'frame') and self.frame.winfo_exists():
                 self._timer_id = self.frame.after(200, self._update_time_label)
             else: self._timer_id = None
        else: self._timer_id = None


    def _update_time_display(self, total_seconds):
        """Formats seconds and updates the time label, including translated prefix."""
        try:
            if not hasattr(self, 'time_label') or not self.time_label.winfo_exists(): return

            if total_seconds < 0: total_seconds = 0
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            milliseconds = int((total_seconds - math.floor(total_seconds)) * 10) # One decimal place

            # Get translated prefix
            prefix = self.gui_app.translate("time_label_prefix") # e.g., "Time:", "Tempo:"
            # Format the numerical part
            time_value_str = f"{minutes:02}:{seconds:02}.{milliseconds}"
            # Combine prefix and value
            time_str = f"{prefix} {time_value_str}" # Add space after prefix

            self.time_label.config(text=time_str)
        except Exception as e:
             print(f"Error updating time display: {e}", file=sys.__stderr__)


    # --- Utility ---
    def clear_plot(self):
        if DEBUG_CANVAS: print("CANVAS CLEAR: Clearing waveform.")
        # Don't clear self.waveform_data here, only the visual plot
        if self.waveform_canvas and self.waveform_canvas.winfo_exists():
            self.waveform_canvas.delete("waveform")
            self._draw_static_canvas_elements() # Redraw background lines


    def on_close(self):
        if DEBUG_CANVAS: print("ON CLOSE: Cleaning up recorder tab...")
        self.stop_timer()
        self.stop_canvas_update_loop()

        if hasattr(self, '_check_audio_queue_id') and self._check_audio_queue_id:
             try:
                 if hasattr(self, 'frame') and self.frame.winfo_exists():
                     self.frame.after_cancel(self._check_audio_queue_id)
                 if DEBUG_CANVAS: print("ON CLOSE: Cancelled queue check.")
             except Exception as e: print(f"ON CLOSE ERROR: cancelling queue check: {e}", file=sys.__stderr__)
             self._check_audio_queue_id = None

        if self.audio_handler:
            if self.is_recording:
                print("ON CLOSE: Stopping active recording...")
                # Note: stop_recording might take time, ideally wait or handle gracefully
                self.audio_handler.stop_recording()
            if self.is_playing:
                print("ON CLOSE: Stopping active playback...")
                self.audio_handler.stop_playback()

# --- END OF REVISED recorder_tab.py ---