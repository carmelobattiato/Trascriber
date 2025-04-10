# utils.py remains unchanged as it doesn't involve UI text
from datetime import timedelta
import wave

def get_audio_duration(file_path):
    try:
        with wave.open(file_path, 'r') as audio:
            frames = audio.getnframes()
            rate = audio.getframerate()
            if rate <= 0: return 0 # Avoid division by zero
            return frames / float(rate)
    except Exception as e:
        # Optionally log the error here if needed for debugging
        # print(f"Error getting duration for {file_path}: {e}")
        return 0

def format_duration(seconds):
    # Format to HH:MM:SS or MM:SS if less than an hour
    td = timedelta(seconds=int(seconds))
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    else:
        return f"{minutes:02}:{seconds:02}"