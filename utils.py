from datetime import timedelta
import wave

def get_audio_duration(file_path):
    try:
        with wave.open(file_path, 'r') as audio:
            return audio.getnframes() / audio.getframerate()
    except Exception as e:
        return 0

def format_duration(seconds):
    return str(timedelta(seconds=int(seconds)))