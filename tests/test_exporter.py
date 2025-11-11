"""
Unit tests for the exporter module.

Tests all export functionality: TXT, JSON, SRT, and DOCX formats.
"""
import os
import json
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Make sure src is in the path for tests to run
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.meeting_transcription_tool.exporter import (
    TranscriptSegment,
    export_txt,
    export_json,
    export_srt,
    export_docx,
    ensure_dir,
)


class TestTranscriptSegment(unittest.TestCase):
    """Test the TranscriptSegment dataclass."""

    def test_segment_creation(self):
        """Test creating a segment with all fields."""
        seg = TranscriptSegment(
            start_ms=1000,
            end_ms=2000,
            text="Hello world",
            speaker="SPEAKER_00"
        )
        self.assertEqual(seg.start_ms, 1000)
        self.assertEqual(seg.end_ms, 2000)
        self.assertEqual(seg.text, "Hello world")
        self.assertEqual(seg.speaker, "SPEAKER_00")

    def test_segment_default_speaker(self):
        """Test that default speaker is 'Speaker 1'."""
        seg = TranscriptSegment(
            start_ms=0,
            end_ms=1000,
            text="Test"
        )
        self.assertEqual(seg.speaker, "Speaker 1")


class TestExporterUtils(unittest.TestCase):
    """Test utility functions."""

    def test_ensure_dir_creates_directory(self):
        """Test that ensure_dir creates a directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = os.path.join(tmpdir, "new_dir", "nested")
            ensure_dir(test_path)
            self.assertTrue(os.path.exists(test_path))

    def test_ensure_dir_with_existing_directory(self):
        """Test that ensure_dir handles existing directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should not raise an exception
            ensure_dir(tmpdir)
            self.assertTrue(os.path.exists(tmpdir))


class TestExportTXT(unittest.TestCase):
    """Test TXT export functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.segments = [
            TranscriptSegment(0, 1000, "Hello world", "SPEAKER_00"),
            TranscriptSegment(1000, 2000, "How are you?", "SPEAKER_01"),
            TranscriptSegment(2000, 3000, "I'm fine.", "SPEAKER_00"),
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_export_txt_creates_file(self):
        """Test that export_txt creates a file."""
        path = export_txt(self.segments, self.temp_dir, "test")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith("test.txt"))

    def test_export_txt_content_format(self):
        """Test that TXT format is correct."""
        path = export_txt(self.segments, self.temp_dir, "test")
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        self.assertEqual(len(lines), 3)
        self.assertIn("[00:00:00 - 00:00:01] SPEAKER_00: Hello world", lines[0])
        self.assertIn("[00:00:01 - 00:00:02] SPEAKER_01: How are you?", lines[1])
        self.assertIn("[00:00:02 - 00:00:03] SPEAKER_00: I'm fine.", lines[2])

    def test_export_txt_with_unicode(self):
        """Test TXT export with Unicode characters."""
        unicode_segments = [
            TranscriptSegment(0, 1000, "Привет мир 🌍", "SPEAKER_00"),
            TranscriptSegment(1000, 2000, "你好世界", "SPEAKER_01"),
        ]
        path = export_txt(unicode_segments, self.temp_dir, "unicode_test")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        self.assertIn("Привет мир 🌍", content)
        self.assertIn("你好世界", content)


class TestExportJSON(unittest.TestCase):
    """Test JSON export functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.segments = [
            TranscriptSegment(0, 1500, "Test segment", "SPEAKER_00"),
            TranscriptSegment(1500, 3000, "Another one", "SPEAKER_01"),
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_export_json_creates_file(self):
        """Test that export_json creates a file."""
        path = export_json(self.segments, self.temp_dir, "test")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith("test.json"))

    def test_export_json_structure(self):
        """Test that JSON has correct structure."""
        metadata = {"source": "test.mp3", "model": "whisper-1"}
        path = export_json(self.segments, self.temp_dir, "test", metadata=metadata)
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.assertIn("metadata", data)
        self.assertIn("segments", data)
        self.assertEqual(data["metadata"]["source"], "test.mp3")
        self.assertEqual(len(data["segments"]), 2)

    def test_export_json_segment_fields(self):
        """Test that each segment has all required fields."""
        path = export_json(self.segments, self.temp_dir, "test")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        seg = data["segments"][0]
        self.assertIn("start_ms", seg)
        self.assertIn("end_ms", seg)
        self.assertIn("start", seg)
        self.assertIn("end", seg)
        self.assertIn("speaker", seg)
        self.assertIn("text", seg)
        
        self.assertEqual(seg["start_ms"], 0)
        self.assertEqual(seg["end_ms"], 1500)
        self.assertEqual(seg["text"], "Test segment")
        self.assertEqual(seg["speaker"], "SPEAKER_00")

    def test_export_json_without_metadata(self):
        """Test JSON export without metadata."""
        path = export_json(self.segments, self.temp_dir, "test")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.assertEqual(data["metadata"], {})


class TestExportSRT(unittest.TestCase):
    """Test SRT subtitle export functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.segments = [
            TranscriptSegment(0, 1234, "First subtitle", "SPEAKER_00"),
            TranscriptSegment(1234, 2345, "Second subtitle", "SPEAKER_01"),
            TranscriptSegment(2345, 3456, "Third subtitle", "SPEAKER_00"),
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_export_srt_creates_file(self):
        """Test that export_srt creates a file."""
        path = export_srt(self.segments, self.temp_dir, "test")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith("test.srt"))

    def test_export_srt_format(self):
        """Test that SRT format is correct."""
        path = export_srt(self.segments, self.temp_dir, "test")
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for proper SRT structure
        self.assertIn("1\n", content)
        self.assertIn("00:00:00,000 --> 00:00:01,234", content)
        self.assertIn("SPEAKER_00: First subtitle", content)
        
        self.assertIn("2\n", content)
        self.assertIn("00:00:01,234 --> 00:00:02,345", content)
        self.assertIn("SPEAKER_01: Second subtitle", content)

    def test_export_srt_sequence_numbers(self):
        """Test that SRT sequence numbers are correct."""
        path = export_srt(self.segments, self.temp_dir, "test")
        
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # First subtitle should be numbered 1
        self.assertEqual(lines[0].strip(), "1")
        # After blank line, second subtitle should be numbered 2
        subtitle_2_index = None
        for i, line in enumerate(lines):
            if line.strip() == "2":
                subtitle_2_index = i
                break
        self.assertIsNotNone(subtitle_2_index)


class TestExportDOCX(unittest.TestCase):
    """Test DOCX export functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.segments = [
            TranscriptSegment(0, 1000, "Document test", "SPEAKER_00"),
            TranscriptSegment(1000, 2000, "Another line", "SPEAKER_01"),
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch("src.meeting_transcription_tool.exporter.has_docx", True)
    @patch("src.meeting_transcription_tool.exporter.Document")
    def test_export_docx_creates_file(self, mock_document):
        """Test that export_docx creates a file when python-docx is available."""
        mock_doc_instance = MagicMock()
        mock_document.return_value = mock_doc_instance
        
        path = export_docx(self.segments, self.temp_dir, "test")
        
        self.assertTrue(path.endswith("test.docx"))
        mock_document.assert_called_once()
        mock_doc_instance.add_heading.assert_called_once_with("Meeting Transcript", level=1)
        self.assertEqual(mock_doc_instance.add_paragraph.call_count, 2)
        mock_doc_instance.save.assert_called_once()

    @patch("src.meeting_transcription_tool.exporter.has_docx", False)
    def test_export_docx_raises_when_not_installed(self):
        """Test that export_docx raises error when python-docx is not installed."""
        with self.assertRaises(RuntimeError) as context:
            export_docx(self.segments, self.temp_dir, "test")
        
        self.assertIn("python-docx is not installed", str(context.exception))


class TestExporterEdgeCases(unittest.TestCase):
    """Test edge cases in exporter."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_export_empty_segments(self):
        """Test exporting empty segment list."""
        empty_segments = []
        
        # TXT export
        txt_path = export_txt(empty_segments, self.temp_dir, "empty")
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "")
        
        # JSON export
        json_path = export_json(empty_segments, self.temp_dir, "empty")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["segments"]), 0)
        
        # SRT export
        srt_path = export_srt(empty_segments, self.temp_dir, "empty")
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "")

    def test_export_long_text_segment(self):
        """Test exporting segment with very long text."""
        long_text = "A" * 10000
        segments = [TranscriptSegment(0, 1000, long_text, "SPEAKER_00")]
        
        path = export_txt(segments, self.temp_dir, "long")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(long_text, content)

    def test_export_special_characters_in_filename(self):
        """Test exporting with special characters in base name."""
        segments = [TranscriptSegment(0, 1000, "Test", "SPEAKER_00")]
        
        # Should handle spaces and other characters
        path = export_txt(segments, self.temp_dir, "test file")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith("test file.txt"))


if __name__ == "__main__":
    unittest.main()

