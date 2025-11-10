import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Make sure src is in the path for tests to run
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.meeting_transcription_tool.transcriber import run_transcription_pipeline, TranscriptionResult
from src.meeting_transcription_tool.diarization import SpeakerSegment
from src.meeting_transcription_tool.exporter import TranscriptSegment

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_audio"
        os.makedirs(self.test_dir, exist_ok=True)
        self.mock_audio_path = os.path.join(self.test_dir, "test.mp3")
        with open(self.mock_audio_path, "wb") as f:
            f.write(b"mock_audio_content")

    def tearDown(self):
        if os.path.exists(self.mock_audio_path):
            os.remove(self.mock_audio_path)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    @patch("src.meeting_transcription_tool.transcriber.transcribe_with_whisper_async")
    @patch("src.meeting_transcription_tool.transcriber.run_diarization")
    def test_pipeline_speaker_mapping(self, mock_run_diarization, mock_transcribe_async):
        # Mock the diarization result
        mock_diarization_result = [
            SpeakerSegment(start_s=0.0, end_s=2.0, speaker_label="SPEAKER_00"),
            SpeakerSegment(start_s=2.0, end_s=4.0, speaker_label="SPEAKER_01"),
        ]

        async def mock_diarization_thread(func, *args, **kwargs):
            return mock_diarization_result

        # Mock the transcription result
        mock_transcription_result = TranscriptionResult(
            text="Hello world. This is a test.",
            segments=[
                TranscriptSegment(start_ms=500, end_ms=1500, text="Hello world.", speaker="Unknown"),
                TranscriptSegment(start_ms=2500, end_ms=3500, text="This is a test.", speaker="Unknown"),
            ],
            raw={}
        )

        async def mock_transcribe(*args, **kwargs):
            return mock_transcription_result

        mock_transcribe_async.side_effect = mock_transcribe

        with patch('asyncio.to_thread', mock_diarization_thread):
            # Run the pipeline
            result = asyncio.run(run_transcription_pipeline(self.mock_audio_path))

        # Assert that the speakers were mapped correctly
        self.assertEqual(len(result.segments), 2)
        self.assertEqual(result.segments[0].speaker, "SPEAKER_00")
        self.assertEqual(result.segments[1].speaker, "SPEAKER_01")

if __name__ == "__main__":
    unittest.main()
