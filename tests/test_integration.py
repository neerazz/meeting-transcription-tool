"""
Integration tests for the meeting transcription tool.

Tests the complete end-to-end pipeline with mock data.
This can be run to verify the entire system works correctly.
"""
import os
import sys
import json
import unittest
import tempfile
import shutil
from pathlib import Path

# Make sure src is in the path for tests to run
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.meeting_transcription_tool.exporter import (
    TranscriptSegment,
    export_txt,
    export_json,
    export_srt,
    export_docx
)
from src.meeting_transcription_tool.audio_processor import (
    validate_audio_file,
    bytes_to_readable,
    ms_to_hhmmss,
    ms_to_srt_timestamp
)


def create_mock_transcript_data():
    """Create mock transcript data to demonstrate expected output format."""
    return [
        TranscriptSegment(
            start_ms=0,
            end_ms=3500,
            text="Hello everyone, welcome to today's meeting.",
            speaker="SPEAKER_00"
        ),
        TranscriptSegment(
            start_ms=4000,
            end_ms=8200,
            text="Thank you for having me. I'm excited to discuss our project progress.",
            speaker="SPEAKER_01"
        ),
        TranscriptSegment(
            start_ms=8500,
            end_ms=12800,
            text="Let's start with the quarterly review. We've made significant progress.",
            speaker="SPEAKER_00"
        ),
        TranscriptSegment(
            start_ms=13000,
            end_ms=17500,
            text="I agree. The team has done an excellent job on the deliverables.",
            speaker="SPEAKER_02"
        ),
        TranscriptSegment(
            start_ms=18000,
            end_ms=22300,
            text="We've completed about 85% of the planned tasks for this quarter.",
            speaker="SPEAKER_01"
        ),
    ]


class TestIntegrationMockData(unittest.TestCase):
    """Integration tests using mock data."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.segments = create_mock_transcript_data()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_full_export_pipeline(self):
        """Test complete export pipeline with all formats."""
        base_name = "integration_test"
        metadata = {
            "source_file": "mock_audio.mp3",
            "model": "whisper-1",
            "generated_at": "2025-11-10T12:00:00Z",
        }

        # Export to all formats
        txt_path = export_txt(self.segments, self.temp_dir, base_name)
        json_path = export_json(self.segments, self.temp_dir, base_name, metadata=metadata)
        srt_path = export_srt(self.segments, self.temp_dir, base_name)

        # Verify all files were created
        self.assertTrue(os.path.exists(txt_path))
        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(srt_path))

    def test_txt_output_format(self):
        """Verify TXT output format matches specification."""
        path = export_txt(self.segments, self.temp_dir, "test")
        
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Check format: [HH:MM:SS - HH:MM:SS] SPEAKER_XX: text
        self.assertEqual(len(lines), len(self.segments))
        
        # First line should be formatted correctly
        expected_format = "[00:00:00 - 00:00:04] SPEAKER_00: Hello everyone, welcome to today's meeting."
        self.assertEqual(lines[0].strip(), expected_format)

    def test_json_output_structure(self):
        """Verify JSON output structure and content."""
        metadata = {
            "source_file": "test.mp3",
            "model": "whisper-1",
            "generated_at": "2025-11-10T12:00:00Z",
        }
        path = export_json(self.segments, self.temp_dir, "test", metadata=metadata)
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check structure
        self.assertIn("metadata", data)
        self.assertIn("segments", data)
        
        # Check metadata
        self.assertEqual(data["metadata"]["source_file"], "test.mp3")
        self.assertEqual(data["metadata"]["model"], "whisper-1")
        
        # Check segments
        self.assertEqual(len(data["segments"]), len(self.segments))
        
        # Check first segment has all fields
        first_seg = data["segments"][0]
        required_fields = ["start_ms", "end_ms", "start", "end", "speaker", "text"]
        for field in required_fields:
            self.assertIn(field, first_seg)
        
        # Verify timestamps are formatted correctly
        self.assertEqual(first_seg["start"], "00:00:00")
        self.assertEqual(first_seg["end"], "00:00:04")

    def test_srt_output_format(self):
        """Verify SRT output format matches subtitle standard."""
        path = export_srt(self.segments, self.temp_dir, "test")
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for SRT format: sequence number, timestamp, text, blank line
        lines = content.strip().split('\n')
        
        # First subtitle should start with 1
        self.assertEqual(lines[0], "1")
        
        # Second line should be timestamp
        self.assertIn("-->", lines[1])
        self.assertIn("00:00:00,000", lines[1])
        
        # Third line should be text with speaker
        self.assertIn("SPEAKER_00:", lines[2])

    def test_speaker_consistency(self):
        """Verify speaker labels are consistent across exports."""
        base_name = "consistency_test"
        
        txt_path = export_txt(self.segments, self.temp_dir, base_name)
        json_path = export_json(self.segments, self.temp_dir, base_name)
        
        # Get speakers from TXT
        with open(txt_path, "r", encoding="utf-8") as f:
            txt_speakers = []
            for line in f:
                speaker = line.split("] ")[1].split(":")[0]
                txt_speakers.append(speaker)
        
        # Get speakers from JSON
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            json_speakers = [seg["speaker"] for seg in data["segments"]]
        
        # Verify they match
        self.assertEqual(txt_speakers, json_speakers)

    def test_timestamp_accuracy(self):
        """Verify timestamp conversions are accurate."""
        # Test ms_to_hhmmss conversion
        self.assertEqual(ms_to_hhmmss(0), "00:00:00")
        self.assertEqual(ms_to_hhmmss(3500), "00:00:04")
        self.assertEqual(ms_to_hhmmss(61000), "00:01:01")
        self.assertEqual(ms_to_hhmmss(3661000), "01:01:01")
        
        # Test ms_to_srt_timestamp conversion
        self.assertEqual(ms_to_srt_timestamp(0), "00:00:00,000")
        self.assertEqual(ms_to_srt_timestamp(3500), "00:00:03,500")
        self.assertEqual(ms_to_srt_timestamp(61234), "00:01:01,234")

    def test_unicode_handling(self):
        """Test that Unicode characters are handled correctly in all formats."""
        unicode_segments = [
            TranscriptSegment(0, 1000, "Hello 世界 🌍", "SPEAKER_00"),
            TranscriptSegment(1000, 2000, "Привет мир", "SPEAKER_01"),
        ]
        
        base_name = "unicode_test"
        txt_path = export_txt(unicode_segments, self.temp_dir, base_name)
        json_path = export_json(unicode_segments, self.temp_dir, base_name)
        srt_path = export_srt(unicode_segments, self.temp_dir, base_name)
        
        # Verify TXT handles Unicode
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Hello 世界 🌍", content)
            self.assertIn("Привет мир", content)
        
        # Verify JSON handles Unicode
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["segments"][0]["text"], "Hello 世界 🌍")
            self.assertEqual(data["segments"][1]["text"], "Привет мир")
        
        # Verify SRT handles Unicode
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Hello 世界 🌍", content)
            self.assertIn("Привет мир", content)


class TestAudioValidation(unittest.TestCase):
    """Test audio file validation in integration context."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_validate_supported_formats(self):
        """Test validation of supported audio formats."""
        formats = [".mp3", ".wav", ".m4a", ".flac"]
        
        for fmt in formats:
            # Create a mock file
            file_path = os.path.join(self.temp_dir, f"test{fmt}")
            with open(file_path, "wb") as f:
                f.write(b"mock audio content")
            
            # Should pass file existence and format check
            # (might fail on duration if mutagen is installed)
            ok, reason = validate_audio_file(file_path)
            if not ok:
                # If it fails, it should be because of duration, not format
                self.assertNotIn("Unsupported format", reason)

    def test_validate_unsupported_format(self):
        """Test that unsupported formats are rejected."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("not audio")
        
        ok, reason = validate_audio_file(file_path)
        self.assertFalse(ok)
        self.assertIn("Unsupported format", reason)

    def test_validate_nonexistent_file(self):
        """Test that nonexistent files are rejected."""
        ok, reason = validate_audio_file("nonexistent.mp3")
        self.assertFalse(ok)
        self.assertIn("File not found", reason)


class TestOutputDirectoryCreation(unittest.TestCase):
    """Test output directory creation and management."""

    def test_nested_directory_creation(self):
        """Test that nested output directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = os.path.join(tmpdir, "output", "nested", "deep")
            segments = [TranscriptSegment(0, 1000, "Test", "SPEAKER_00")]
            
            # Should create all nested directories
            path = export_txt(segments, nested_path, "test")
            self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    # Run all integration tests
    unittest.main(verbosity=2)

