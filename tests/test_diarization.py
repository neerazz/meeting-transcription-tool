"""
Unit tests for the diarization module.

Tests speaker diarization functionality with mocked pyannote.audio.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Make sure src is in the path for tests to run
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.meeting_transcription_tool.diarization import (
    run_diarization,
    SpeakerSegment
)


class TestSpeakerSegment(unittest.TestCase):
    """Test the SpeakerSegment dataclass."""

    def test_speaker_segment_creation(self):
        """Test creating a speaker segment."""
        seg = SpeakerSegment(
            start_s=0.5,
            end_s=2.5,
            speaker_label="SPEAKER_00"
        )
        self.assertEqual(seg.start_s, 0.5)
        self.assertEqual(seg.end_s, 2.5)
        self.assertEqual(seg.speaker_label, "SPEAKER_00")


class TestDiarization(unittest.TestCase):
    """Test diarization functionality."""

    def setUp(self):
        self.audio_path = "test_audio.mp3"
        self.hf_token = "test_token"

    @patch.dict(os.environ, {"HUGGING_FACE_TOKEN": "env_token"})
    @patch("src.meeting_transcription_tool.diarization.Pipeline")
    @patch("src.meeting_transcription_tool.diarization.torch")
    def test_run_diarization_with_token(self, mock_torch, mock_pipeline_class):
        """Test diarization with provided token."""
        # Mock CUDA availability
        mock_torch.cuda.is_available.return_value = False
        
        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        
        # Mock diarization result with itertracks
        mock_turn1 = MagicMock()
        mock_turn1.start = 0.0
        mock_turn1.end = 2.0
        
        mock_turn2 = MagicMock()
        mock_turn2.start = 2.5
        mock_turn2.end = 4.5
        
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = [
            (mock_turn1, None, "SPEAKER_00"),
            (mock_turn2, None, "SPEAKER_01"),
        ]
        mock_pipeline.return_value = mock_diarization
        
        # Run diarization
        segments = run_diarization(self.audio_path, hf_token=self.hf_token)
        
        # Verify
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].speaker_label, "SPEAKER_00")
        self.assertEqual(segments[0].start_s, 0.0)
        self.assertEqual(segments[0].end_s, 2.0)
        self.assertEqual(segments[1].speaker_label, "SPEAKER_01")
        
        # Verify pipeline was called correctly
        mock_pipeline_class.from_pretrained.assert_called_once_with(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=self.hf_token,
        )

    @patch.dict(os.environ, {"HUGGING_FACE_TOKEN": "env_token"})
    @patch("src.meeting_transcription_tool.diarization.Pipeline")
    @patch("src.meeting_transcription_tool.diarization.torch")
    def test_run_diarization_with_env_token(self, mock_torch, mock_pipeline_class):
        """Test diarization uses environment variable when token not provided."""
        mock_torch.cuda.is_available.return_value = False
        
        mock_pipeline = MagicMock()
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = []
        mock_pipeline.return_value = mock_diarization
        
        # Run without token - should use env variable
        segments = run_diarization(self.audio_path)
        
        # Verify env token was used
        mock_pipeline_class.from_pretrained.assert_called_once_with(
            "pyannote/speaker-diarization-3.1",
            use_auth_token="env_token",
        )

    def test_run_diarization_no_token_raises(self):
        """Test that missing token raises ValueError."""
        with self.assertRaises(ValueError) as context:
            run_diarization(self.audio_path, hf_token=None)
        
        self.assertIn("Hugging Face token not found", str(context.exception))

    @patch.dict(os.environ, {"HUGGING_FACE_TOKEN": "test_token"})
    @patch("src.meeting_transcription_tool.diarization.Pipeline")
    @patch("src.meeting_transcription_tool.diarization.torch")
    def test_run_diarization_with_cuda(self, mock_torch, mock_pipeline_class):
        """Test diarization uses GPU when available."""
        # Mock CUDA as available
        mock_torch.cuda.is_available.return_value = True
        mock_device = MagicMock()
        mock_torch.device.return_value = mock_device
        
        mock_pipeline = MagicMock()
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = []
        mock_pipeline.return_value = mock_diarization
        
        # Run diarization
        run_diarization(self.audio_path)
        
        # Verify pipeline was moved to GPU
        mock_torch.device.assert_called_once_with("cuda")
        mock_pipeline.to.assert_called_once_with(mock_device)

    @patch.dict(os.environ, {"HUGGING_FACE_TOKEN": "test_token"})
    @patch("src.meeting_transcription_tool.diarization.Pipeline")
    @patch("src.meeting_transcription_tool.diarization.torch")
    def test_run_diarization_multiple_speakers(self, mock_torch, mock_pipeline_class):
        """Test diarization with multiple speakers."""
        mock_torch.cuda.is_available.return_value = False
        
        mock_pipeline = MagicMock()
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        
        # Create multiple speaker turns
        mock_turns = []
        for i in range(5):
            turn = MagicMock()
            turn.start = float(i * 2)
            turn.end = float(i * 2 + 1.5)
            mock_turns.append((turn, None, f"SPEAKER_{i % 3:02d}"))
        
        mock_diarization = MagicMock()
        mock_diarization.itertracks.return_value = mock_turns
        mock_pipeline.return_value = mock_diarization
        
        # Run diarization
        segments = run_diarization(self.audio_path)
        
        # Verify
        self.assertEqual(len(segments), 5)
        # Check speakers alternate/repeat properly
        self.assertEqual(segments[0].speaker_label, "SPEAKER_00")
        self.assertEqual(segments[1].speaker_label, "SPEAKER_01")
        self.assertEqual(segments[2].speaker_label, "SPEAKER_02")
        self.assertEqual(segments[3].speaker_label, "SPEAKER_00")


if __name__ == "__main__":
    unittest.main()

