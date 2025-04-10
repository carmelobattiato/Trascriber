# AudioScript - Trascrizione Audio Professionale

![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Choose your license -->

AudioScript is a desktop application with a modern GUI (built with Tkinter/ttk) for professional audio transcription using OpenAI's powerful Whisper models. It allows users to easily transcribe WAV audio files, select different Whisper models for varying speed/accuracy trade-offs, choose the language, and leverage GPU acceleration where available (MPS on Mac, DirectML on Windows).

![image](https://github.com/user-attachments/assets/f70aee07-4020-46d4-aa2a-5867a65cf11c)

*--(Add a screenshot of your application here. Create an 'images' folder in your repo for it.)--*

---

## Features

*   **User-Friendly GUI:** Clean and intuitive interface built with Tkinter and ttk themes.
*   **Whisper Integration:** Leverages OpenAI's Whisper for state-of-the-art transcription accuracy.
*   **Model Selection:** Choose from various Whisper models (`tiny`, `base`, `small`, `medium`, `large`) to balance speed and precision.
*   **Language Support:** Transcribe audio in multiple languages (Italian, English, French, German, Spanish, Japanese, Chinese initially supported).
*   **GPU Acceleration:**
    *   Uses Metal Performance Shaders (MPS) on compatible Macs.
    *   Uses DirectML on Windows with compatible integrated/discrete GPUs (via `torch-directml`).
    *   Falls back gracefully to CPU if GPU is unavailable or not configured.
*   **Real-time Updates:** View transcription results as they are generated.
*   **Console Output:** Monitor the transcription process, view logs, and see audio file details.
*   **Transcription Control:** Start and gracefully stop the transcription process.
*   **Easy Export:**
    *   Copy the full transcription text to the clipboard.
    *   Save the transcription to a text file (`.txt`).
*   **Progress Indication:** Visual feedback on the current task and progress bar during model loading and transcription.
*   **Audio File Info:** Automatically displays duration, channels, and sample rate of the selected WAV file.

## Requirements

*   **Operating System:**
    *   Windows 10/11 (Tested)
    *   macOS (Should work, especially with MPS support)
    *   Linux (Should work, GPU support depends on PyTorch installation)
*   **Python:** Version 3.9 or 3.10 (Recommended for Whisper and PyTorch compatibility).
*   **RAM:** 8GB minimum, 16GB+ recommended for larger models (`medium`, `large`).
*   **Disk Space:** Up to 10GB if downloading all Whisper models, ~2GB for the `large` model.
*   **FFmpeg:** Whisper requires FFmpeg. It needs to be installed and accessible in your system's PATH.
    *   **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH, or install via package managers like Chocolatey (`choco install ffmpeg`) or Scoop (`scoop install ffmpeg`).
    *   **macOS:** Install via Homebrew: `brew install ffmpeg`.
    *   **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install ffmpeg`.

## Installation

Follow these steps to set up AudioScript:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/carmelobattiato/Trascriber.git # Replace with your repo URL
    cd audioscript
    ```

2.  **Install Python:**
    Ensure you have Python 3.9 or 3.10 installed. You can download it from [python.org](https://www.python.org/). During installation on Windows, make sure to check "Add Python to PATH".

3.  **Create and Activate a Virtual Environment:** (Highly Recommended)
    ```bash
    # Create a virtual environment named 'venv'
    python -m venv venv

    # Activate it:
    # Windows (cmd/powershell)
    .\venv\Scripts\activate
    # macOS/Linux (bash/zsh)
    source venv/bin/activate
    ```
    You should see `(venv)` appear at the beginning of your terminal prompt.

4.  **Install Dependencies:**
    *   **Upgrade Pip:**
        ```bash
        python -m pip install --upgrade pip
        ```
    *   **Install PyTorch:** Choose the command that matches your system and GPU setup. Visit the [PyTorch website](https://pytorch.org/get-started/locally/) for the latest commands if needed.

        *   **NVIDIA GPU (CUDA):** (Check your CUDA version compatibility)
            ```bash
            # Example for CUDA 11.8 - Adjust if needed
            pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
            ```
        *   **Windows with DirectML (Intel/AMD/NVIDIA):**
            ```bash
            pip install torch-directml
            # PyTorch CPU is also needed as a base
            pip install torch torchaudio
            ```
        *   **macOS (CPU or MPS):**
            ```bash
            pip install torch torchaudio
            ```
        *   **CPU Only (Any OS):**
            ```bash
            pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
            ```

    *   **Install Whisper:**
        ```bash
        pip install -U openai-whisper
        # Or for the latest git version:
        # pip install git+https://github.com/openai/whisper.git
        ```
    *   **(Optional but recommended) Install setuptools-rust:** Required by the tokenizer used in Whisper if building from source or for certain updates.
        ```bash
        pip install setuptools-rust
        ```

5.  **Download Whisper Models:**
    The first time you select a model in the application, it will be downloaded automatically (~tens of MB to ~1.5GB depending on the model). Models are typically cached in `~/.cache/whisper` (Linux/macOS) or `C:\Users\<YourUser>\.cache\whisper` (Windows). You *don't need* to pre-download them unless you want to.

6.  **Verify FFmpeg:**
    Make sure FFmpeg is installed and accessible. Open a new terminal and run:
    ```bash
    ffmpeg -version
    ```
    If this command works, Whisper should be able to find it.

## Usage

1.  **Activate Virtual Environment:**
    If you closed your terminal, navigate back to the `audioscript` directory and activate the virtual environment again (`.\venv\Scripts\activate` or `source venv/bin/activate`).

2.  **Run the Application:**
    ```bash
    python main.py
    ```

3.  **Using the Interface:**
    *   **Select Audio File:** Click "Sfoglia..." (`Browse...`) to choose a `.wav` file. File details (duration, channels, rate) will appear in the console log.
    *   **Choose Options:**
        *   Select the desired `Modello` (`Model`) from the dropdown (e.g., `large` for best quality, `base` for speed). The description updates automatically.
        *   Select the `Lingua` (`Language`) of the audio.
        *   Check `Usa GPU` (`Use GPU`) if you want to attempt hardware acceleration (requires compatible hardware and correctly installed PyTorch/DirectML). Hover over the checkbox for details.
    *   **Start Transcription:** Click "✓ Avvia Trascrizione" (`✓ Start Transcription`).
    *   **Monitor Progress:**
        *   The status bar at the bottom shows the current stage (Loading model, Transcribing...).
        *   The progress bar animates during active processing.
        *   The "Console e Log" tab shows detailed messages from Whisper.
        *   The "Trascrizione" tab displays the transcribed text as it's generated.
    *   **Stop Transcription:** Click "⨯ Interrompi" (`⨯ Stop`) if needed. The process will stop after completing the current segment.
    *   **Get Results:**
        *   Click "📋 Copia negli Appunti" (`📋 Copy to Clipboard`) to copy the text.
        *   Click "💾 Salva Trascrizione" (`💾 Save Transcription`) to save the text to a `.txt` file.

## Troubleshooting

*   **Error: `RuntimeError: CUDA out of memory`:**
    *   You are likely using a large model (`medium` or `large`) on a GPU with insufficient VRAM.
    *   **Solution:** Try a smaller model (`small`, `base`), uncheck "Usa GPU" to use CPU, or close other applications using the GPU.
*   **Error: `FileNotFoundError: [WinError 2] The system cannot find the file specified` (often related to `ffmpeg`):**
    *   Whisper cannot find the required `ffmpeg` executable.
    *   **Solution:** Ensure FFmpeg is installed correctly and its location is added to your system's PATH environment variable. Restart the application (and possibly your terminal or computer) after modifying the PATH.
*   **Slow Performance:**
    *   Transcription speed heavily depends on the model size, audio length, and hardware (CPU/GPU).
    *   **Solutions:**
        *   Use a smaller model (`tiny`, `base`, `small`).
        *   Ensure "Usa GPU" is checked *if* you have a compatible and correctly configured GPU (check console logs for device usage: `mps`, `cuda`, `directml`, or `cpu`).
        *   Close other resource-intensive applications.
        *   Ensure the input audio quality is decent (clear speech, low noise).
*   **Incorrect Transcription / Language Issues:**
    *   **Solutions:**
        *   Ensure the correct `Lingua` (`Language`) is selected in the options.
        *   Try a larger, more accurate model (e.g., `large`).
        *   Improve the quality of the input audio (reduce background noise, ensure clear speech).
*   **DirectML Issues (Windows):**
    *   Ensure you have installed `torch-directml` (`pip install torch-directml`).
    *   Make sure your GPU drivers are up to date.
    *   DirectML support can vary depending on the specific GPU and driver version. If it causes issues, uncheck "Usa GPU" to fallback to CPU.
*   **Application Fails to Start / Module Not Found Errors:**
    *   **Solution:** Make sure you have activated the correct virtual environment (`venv`) before running `python main.py`. Verify all dependencies were installed correctly using `pip list`.

## Future Implementations / Roadmap

This project is functional but can be extended further. Potential future enhancements include:

*   **[ ] More Audio Formats:** Support for common formats like MP3, M4A, FLAC (would require integrating `ffmpeg` or `pydub` for conversion before processing).
*   **[ ] Batch Processing:** Ability to select multiple files or a folder for transcription.
*   **[ ] Speaker Diarization:** Identifying and labeling different speakers in the audio.
*   **[ ] Timestamping:** Option to include timestamps (per word or segment) in the output.
*   **[ ] More Export Formats:** Saving transcriptions as SRT, VTT, DOCX, etc.
*   **[ ] Determinate Progress Bar:** Show actual percentage completion based on audio processed, rather than indeterminate animation.
*   **[ ] Configuration Saving:** Remember the last used model, language, and window size.
*   **[ ] UI Internationalization:** Translate the GUI itself into different languages.
*   **[ ] Direct Audio Input:** Option to transcribe directly from a microphone.
*   **[ ] Improved Error Handling:** More specific error messages displayed within the GUI.
*   **[ ] Pre-processing Options:** Basic noise reduction or audio normalization options.

## Contributing

Contributions are welcome! If you'd like to help improve AudioScript, please follow these steps:

1.  **Fork the repository.**
2.  **Create a new branch** for your feature or bug fix:
    ```bash
    git checkout -b feature/your-feature-name # or fix/your-bug-fix
    ```
3.  **Make your changes.** Please try to follow existing code style.
4.  **Test your changes thoroughly.**
5.  **Commit your changes:**
    ```bash
    git commit -m "feat: Add feature X" -m "Detailed description of changes." # Or fix:, chore:, docs:, etc.
    ```
6.  **Push to your fork:**
    ```bash
    git push origin feature/your-feature-name
    ```
7.  **Open a Pull Request** against the `main` branch of the original repository. Provide a clear description of your changes and why they are needed.

If you find a bug or have a feature suggestion, please open an issue on the GitHub repository's "Issues" tab first to discuss it.
