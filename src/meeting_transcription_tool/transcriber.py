from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import asyncio

from .exporter import TranscriptSegment
from .diarization import run_diarization, SpeakerSegment


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


async def transcribe_with_whisper_async(
    audio_path: str,
    model: str = "whisper-1",
    api_key: Optional[str] = None,
    language: Optional[str] = None,
    temperature: float = 0.0,
    poll_interval: int = 5,
    max_retries: int = 3,
) -> TranscriptionResult:
    """
    Transcribe an audio file asynchronously using OpenAI Whisper API.
    """
    client = _get_openai_client(api_key)

    for attempt in range(max_retries):
        try:
            with open(audio_path, "rb") as f:
                response = await asyncio.to_thread(
                    client.audio.transcriptions.create,
                    model=model,
                    file=f,
                    response_format="verbose_json",
                    temperature=temperature,
                    language=language,
                )
            break  # Success
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(poll_interval)
            else:
                raise e # Re-raise the last exception

    try:
        raw: Dict[str, Any] = response.model_dump()
    except Exception:
        try:
            raw = response.to_dict()
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
                speaker="Unknown", # Placeholder, will be replaced by diarization
            )
        )

    if not segments:
        segments.append(TranscriptSegment(start_ms=0, end_ms=max(1000, len(text) // 2), text=text or ""))

    return TranscriptionResult(text=text, segments=segments, raw=raw)

def find_speaker_for_segment(whisper_segment: TranscriptSegment, diarization_segments: List[SpeakerSegment]) -> str:
    """Find the speaker for a given Whisper segment."""
    max_overlap = 0
    speaker_label = "Unknown"

    for dia_segment in diarization_segments:
        # Calculate overlap between whisper_segment and dia_segment in seconds
        overlap_start = max(whisper_segment.start_ms / 1000, dia_segment.start_s)
        overlap_end = min(whisper_segment.end_ms / 1000, dia_segment.end_s)

        overlap_duration = overlap_end - overlap_start

        if overlap_duration > max_overlap:
            max_overlap = overlap_duration
            speaker_label = dia_segment.speaker_label

    return speaker_label


async def run_transcription_pipeline(
    audio_path: str,
    hf_token: str | None = None,
    **whisper_kwargs,
) -> TranscriptionResult:
    """
    Run the full transcription and diarization pipeline.
    """
    # Step 1: Diarization
    diarization_segments = await asyncio.to_thread(run_diarization, audio_path, hf_token)

    # Step 2: Transcription
    transcription_result = await transcribe_with_whisper_async(audio_path, **whisper_kwargs)

    # Step 3: Map speakers to transcription segments
    for segment in transcription_result.segments:
        segment.speaker = find_speaker_for_segment(segment, diarization_segments)

    return transcription_result
