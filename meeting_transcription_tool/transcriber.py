from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .exporters import TranscriptSegment


@dataclass
class TranscriptionResult:
	text: str
	segments: List[TranscriptSegment]
	raw: Dict[str, Any]


def _get_openai_client(api_key: Optional[str] = None):
	# Lazy import so the package is optional until used
	from openai import OpenAI
	key = api_key or os.getenv("OPENAI_API_KEY")
	if not key:
		raise RuntimeError("Missing OpenAI API key. Set environment variable OPENAI_API_KEY.")
	return OpenAI(api_key=key)


def transcribe_with_whisper(
	audio_path: str,
	model: str = "whisper-1",
	api_key: Optional[str] = None,
	language: Optional[str] = None,
	temperature: float = 0.0,
) -> TranscriptionResult:
	"""
	Transcribe an audio file using OpenAI Whisper API with verbose JSON so we can map timestamps.
	"""
	client = _get_openai_client(api_key)
	response = None
	with open(audio_path, "rb") as f:
		# Use verbose_json to get segments with start/end
		response = client.audio.transcriptions.create(
			model=model,
			file=f,
			response_format="verbose_json",
			temperature=temperature,
			language=language,
		)

	# The SDK object is pydantic-like; normalize to dict
	try:
		# new SDKs
		raw: Dict[str, Any] = response.model_dump()
	except Exception:
		try:
			raw = response.to_dict()  # older fallbacks
		except Exception:
			raw = dict(response) if isinstance(response, dict) else {"text": getattr(response, "text", ""), "segments": []}

	text = raw.get("text") or ""
	segments_data = raw.get("segments") or []
	segments: List[TranscriptSegment] = []
	for seg in segments_data:
		start_s = float(seg.get("start", 0.0))
		end_s = float(seg.get("end", max(start_s, start_s + 0.5)))
		segments.append(
			TranscriptSegment(
				start_ms=int(start_s * 1000),
				end_ms=int(end_s * 1000),
				text=seg.get("text", "").strip(),
				speaker="Speaker 1",  # placeholder; diarization not implemented yet
			)
		)

	# If no segments provided, fall back to a single segment covering entire text
	if not segments:
		segments.append(TranscriptSegment(start_ms=0, end_ms=max(1000, len(text) // 2), text=text or ""))

	return TranscriptionResult(text=text, segments=segments, raw=raw)


