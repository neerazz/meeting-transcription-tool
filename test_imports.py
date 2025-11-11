#!/usr/bin/env python3
"""Quick test to verify all imports work correctly."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from meeting_transcription_tool.cli import cli
    print("✓ CLI import successful")
except Exception as e:
    print(f"✗ CLI import failed: {e}")
    sys.exit(1)

try:
    from meeting_transcription_tool.speaker_identifier import identify_speakers, SpeakerIdentificationResult
    print("✓ Speaker identifier import successful")
except Exception as e:
    print(f"✗ Speaker identifier import failed: {e}")
    sys.exit(1)

try:
    from meeting_transcription_tool.ai_logger import get_ai_logger
    print("✓ AI logger import successful")
except Exception as e:
    print(f"✗ AI logger import failed: {e}")
    sys.exit(1)

try:
    from meeting_transcription_tool.pipeline_stages import stage2_identify_speakers
    print("✓ Pipeline stages import successful")
except Exception as e:
    print(f"✗ Pipeline stages import failed: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")
