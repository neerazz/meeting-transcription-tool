"""
This module contains the speaker diarization functionality.

It uses the `pyannote.audio` library to identify speaker segments in an audio file.
"""
from __future__ import annotations

import os
from typing import List, Tuple
from dataclasses import dataclass

import torch
from pyannote.audio import Pipeline


@dataclass
class SpeakerSegment:
    """Represents a segment of audio spoken by a specific speaker."""
    start_s: float
    end_s: float
    speaker_label: str


def run_diarization(audio_path: str, hf_token: str | None = None) -> List[SpeakerSegment]:
    """
    Run speaker diarization on an audio file using a pre-trained pyannote.audio model.

    Args:
        audio_path: Path to the audio file.
        hf_token: Hugging Face API token. If not provided, it will be read from the
                  HUGGING_FACE_TOKEN environment variable.

    Returns:
        A list of SpeakerSegment objects, each representing a segment of audio spoken by a
        specific speaker.
    """
    token = hf_token or os.getenv("HUGGING_FACE_TOKEN")
    if not token:
        raise ValueError(
            "Hugging Face token not found. Please set the HUGGING_FACE_TOKEN "
            "environment variable or pass the token as an argument."
        )

    # Use a pre-trained pipeline
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=token,
    )

    # Send pipeline to GPU if available
    if torch.cuda.is_available():
        pipeline.to(torch.device("cuda"))

    # Apply the pipeline to the audio file
    diarization_result = pipeline(audio_path)

    # Extract speaker segments
    segments = []
    for turn, _, speaker in diarization_result.itertracks(yield_label=True):
        segments.append(
            SpeakerSegment(
                start_s=turn.start,
                end_s=turn.end,
                speaker_label=speaker,
            )
        )

    return segments
