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
    
    # Check if we need to convert the audio format
    # torchaudio has issues with M4A files, so convert to WAV if needed
    temp_wav_path = None
    
    if audio_path.lower().endswith('.m4a'):
        try:
            from pydub import AudioSegment
            import tempfile
            
            print("[INFO] Converting M4A to WAV for diarization...")
            
            # Create temporary WAV file
            temp_fd, temp_wav_path = tempfile.mkstemp(suffix='.wav')
            os.close(temp_fd)  # Close the file descriptor
            
            # Load M4A and export as WAV
            audio = AudioSegment.from_file(audio_path, format="m4a")
            audio.export(temp_wav_path, format="wav")
            
            audio_path = temp_wav_path
            print("[INFO] Conversion complete")
        except (FileNotFoundError, OSError) as e:
            # This catches both FileNotFoundError and Windows OSError for missing ffmpeg
            error_msg = str(e).lower()
            if 'ffmpeg' in error_msg or 'avconv' in error_msg or 'winerror 2' in error_msg or 'system cannot find' in error_msg:
                raise RuntimeError(
                    "\n" + "="*80 + "\n"
                    "ERROR: FFmpeg is required to process M4A files\n\n"
                    "Please install FFmpeg:\n\n"
                    "Windows (PowerShell as Admin):\n"
                    "  choco install ffmpeg\n"
                    "  OR download from: https://www.gyan.dev/ffmpeg/builds/\n\n"
                    "Mac:\n"
                    "  brew install ffmpeg\n\n"
                    "Linux:\n"
                    "  sudo apt install ffmpeg\n\n"
                    "After installation, restart your terminal and try again.\n\n"
                    "See INSTALL_FFMPEG.md for detailed instructions.\n"
                    + "="*80
                )
            raise
        except Exception as e:
            # If conversion fails, try with original file anyway
            print(f"[WARNING] Could not convert M4A to WAV: {e}")
            print("[WARNING] Attempting to use original file...")

    # Use a pre-trained pipeline
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token,
        )
    except Exception as e:
        # Check if it's an access issue
        error_msg = str(e)
        if "gated" in error_msg.lower() or "private" in error_msg.lower() or "authenticate" in error_msg.lower():
            raise ValueError(
                "\n" + "="*80 + "\n"
                "ERROR: Cannot access pyannote/speaker-diarization-3.1\n\n"
                "This model requires accepting the user agreement first:\n\n"
                "1. Go to: https://huggingface.co/pyannote/speaker-diarization-3.1\n"
                "2. Click 'Accept user agreement' button\n"
                "3. Also accept: https://huggingface.co/pyannote/segmentation-3.0\n"
                "4. Then run the script again\n\n"
                "Your HF token has been found and is being used, but you need to\n"
                "accept the model license agreements first.\n"
                + "="*80
            )
        else:
            raise

    # Send pipeline to GPU if available
    if torch.cuda.is_available():
        pipeline.to(torch.device("cuda"))

    try:
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
    
    finally:
        # Clean up temporary WAV file if we created one
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except:
                pass
