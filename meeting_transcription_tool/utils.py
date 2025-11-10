import os
import math
from typing import Tuple


def bytes_to_readable(num_bytes: int) -> str:
	"""Return human-friendly size string."""
	if num_bytes < 1024:
		return f"{num_bytes} B"
	for unit in ["KB", "MB", "GB", "TB"]:
		num_bytes /= 1024.0
		if num_bytes < 1024.0:
			return f"{num_bytes:.2f} {unit}"
	return f"{num_bytes:.2f} PB"


def validate_audio_file(path: str, max_bytes: int = 2 * 1024 * 1024 * 1024) -> Tuple[bool, str]:
	"""
	Basic validation: existence, extension, size under 2GB.
	Duration validation is skipped to avoid requiring ffmpeg; OpenAI accepts large files via streaming.
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


