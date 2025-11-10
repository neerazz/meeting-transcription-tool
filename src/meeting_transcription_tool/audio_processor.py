import os
import math
from typing import Tuple

try:
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    from mutagen.flac import FLAC
    from mutagen.m4a import M4A
    from mutagen.easyid3 import EasyID3
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False


def get_audio_duration(filepath: str) -> float:
    """Get audio file duration in seconds, return 0 if error."""
    if not HAS_MUTAGEN:
        return 0.0

    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".mp3":
            audio = MP3(filepath)
        elif ext == ".wav":
            audio = WAVE(filepath)
        elif ext == ".flac":
            audio = FLAC(filepath)
        elif ext == ".m4a":
            audio = M4A(filepath)
        else:
            return 0.0
        return float(audio.info.length)
    except Exception:
        return 0.0


def convert_audio(
    input_path: str,
    output_path: str,
    target_format: str = "mp3"
) -> str:
    """
    Converts audio file to a target format using pydub.
    Returns the path to the converted file.
    """
    if not HAS_PYDUB:
        raise RuntimeError("pydub is not installed. Please install it with 'pip install pydub'")

    sound = AudioSegment.from_file(input_path)
    sound.export(output_path, format=target_format)
    return output_path


def get_audio_metadata(filepath: str) -> dict:
    """Get audio file metadata, return empty dict if error."""
    if not HAS_MUTAGEN:
        return {}

    try:
        audio = EasyID3(filepath)
        return dict(audio)
    except Exception:
        return {}


def bytes_to_readable(num_bytes: int) -> str:
	"""Return human-friendly size string."""
	if num_bytes < 1024:
		return f"{num_bytes} B"
	for unit in ["KB", "MB", "GB", "TB"]:
		num_bytes /= 1024.0
		if num_bytes < 1024.0:
			return f"{num_bytes:.2f} {unit}"
	return f"{num_bytes:.2f} PB"


def validate_audio_file(
    path: str,
    max_bytes: int = 2 * 1024 * 1024 * 1024,
    max_duration_s: int = 5 * 60 * 60
) -> Tuple[bool, str]:
    """
    Basic validation: existence, extension, size, and duration.
    """
    if not os.path.exists(path):
        return False, f"File not found: {path}"
    if not os.path.isfile(path):
        return False, f"Not a regular file: {path}"

    ext = os.path.splitext(path)[1].lower()
    allowed = {".mp3", ".wav", ".m4a", ".flac"}
    if ext not in allowed:
        return False, f"Unsupported format '{ext}'. Allowed: {', '.join(sorted(allowed))}"

    size = os.path.getsize(path)
    if size > max_bytes:
        return False, f"File is too large: {bytes_to_readable(size)} > {bytes_to_readable(max_bytes)}"

    duration = get_audio_duration(path)
    if duration > 0 and duration > max_duration_s:
        return False, f"File is too long: {duration:.2f}s > {max_duration_s}s"
    elif duration <= 0 and HAS_MUTAGEN:
        # If mutagen is installed, we expect to be able to read the duration
        return False, f"Could not determine audio duration."

    return True, ""


def ms_to_hhmmss(milliseconds: int) -> str:
	"""Convert milliseconds to HH:MM:SS."""
	seconds = int(round(milliseconds / 1000.0))
	h = seconds // 3600
	m = (seconds % 3600) // 60
	s = seconds % 60
	return f"{h:02d}:{m:02d}:{s:02d}"


def ms_to_srt_timestamp(milliseconds: int) -> str:
	"""Convert milliseconds to SRT timestamp format HH:MM:SS,mmm."""
	total_ms = int(milliseconds)
	hours = total_ms // 3_600_000
	minutes = (total_ms % 3_600_000) // 60_000
	seconds = (total_ms % 60_000) // 1_000
	ms = total_ms % 1_000
	return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
