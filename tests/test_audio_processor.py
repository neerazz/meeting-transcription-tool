import os
import unittest
from unittest.mock import patch, MagicMock

# Make sure src is in the path for tests to run
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.meeting_transcription_tool.audio_processor import (
    get_audio_duration,
    convert_audio,
    get_audio_metadata,
    validate_audio_file,
    bytes_to_readable,
    ms_to_hhmmss,
    ms_to_srt_timestamp,
)


class TestAudioProcessor(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_audio"
        os.makedirs(self.test_dir, exist_ok=True)
        self.mock_mp3_path = os.path.join(self.test_dir, "test.mp3")
        self.mock_wav_path = os.path.join(self.test_dir, "test.wav")
        self.mock_txt_path = os.path.join(self.test_dir, "test.txt")

        with open(self.mock_mp3_path, "wb") as f:
            f.write(b"mock_mp3_content")
        with open(self.mock_wav_path, "wb") as f:
            f.write(b"mock_wav_content")
        with open(self.mock_txt_path, "w") as f:
            f.write("text file")

    def tearDown(self):
        for path in [self.mock_mp3_path, self.mock_wav_path, self.mock_txt_path]:
            if os.path.exists(path):
                os.remove(path)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    # --- get_audio_duration ---

    @patch("src.meeting_transcription_tool.audio_processor.MP3")
    def test_get_audio_duration_mp3_happy(self, mock_mp3):
        mock_mp3.return_value.info.length = 120.5
        duration = get_audio_duration(self.mock_mp3_path)
        self.assertEqual(duration, 120.5)

    @patch("src.meeting_transcription_tool.audio_processor.WAVE")
    def test_get_audio_duration_wav_happy(self, mock_wave):
        mock_wave.return_value.info.length = 60.2
        duration = get_audio_duration(self.mock_wav_path)
        self.assertEqual(duration, 60.2)

    def test_get_audio_duration_file_not_found(self):
        duration = get_audio_duration("non_existent_file.mp3")
        self.assertEqual(duration, 0.0)

    @patch("src.meeting_transcription_tool.audio_processor.MP3")
    def test_get_audio_duration_mutagen_error(self, mock_mp3):
        mock_mp3.side_effect = Exception("mutagen error")
        duration = get_audio_duration(self.mock_mp3_path)
        self.assertEqual(duration, 0.0)

    def test_get_audio_duration_unsupported_format(self):
        duration = get_audio_duration(self.mock_txt_path)
        self.assertEqual(duration, 0.0)

    # --- convert_audio ---

    @patch("src.meeting_transcription_tool.audio_processor.AudioSegment")
    def test_convert_audio_happy(self, mock_audio_segment):
        mock_sound = MagicMock()
        mock_audio_segment.from_file.return_value = mock_sound
        output_path = os.path.join(self.test_dir, "output.wav")
        result = convert_audio(self.mock_mp3_path, output_path, "wav")
        self.assertEqual(result, output_path)
        mock_audio_segment.from_file.assert_called_with(self.mock_mp3_path)
        mock_sound.export.assert_called_with(output_path, format="wav")

    @patch("src.meeting_transcription_tool.audio_processor.AudioSegment")
    def test_convert_audio_input_not_found(self, mock_audio_segment):
        mock_audio_segment.from_file.side_effect = FileNotFoundError
        output_path = os.path.join(self.test_dir, "output.wav")
        with self.assertRaises(FileNotFoundError):
            convert_audio("non_existent.mp3", output_path, "wav")

    @patch("src.meeting_transcription_tool.audio_processor.AudioSegment")
    def test_convert_audio_pydub_error(self, mock_audio_segment):
        mock_sound = MagicMock()
        mock_audio_segment.from_file.return_value = mock_sound
        mock_sound.export.side_effect = Exception("pydub error")
        output_path = os.path.join(self.test_dir, "output.wav")
        with self.assertRaises(Exception):
            convert_audio(self.mock_mp3_path, output_path, "wav")

    # --- get_audio_metadata ---

    @patch("src.meeting_transcription_tool.audio_processor.EasyID3")
    def test_get_audio_metadata_happy(self, mock_easyid3):
        mock_easyid3.return_value = {"artist": ["Test Artist"], "title": ["Test Title"]}
        metadata = get_audio_metadata(self.mock_mp3_path)
        self.assertEqual(metadata, {"artist": ["Test Artist"], "title": ["Test Title"]})

    def test_get_audio_metadata_no_metadata(self):
        # This is tricky to mock without a real file, so we'll assume an exception means no metadata
        with patch("src.meeting_transcription_tool.audio_processor.EasyID3", side_effect=Exception):
            metadata = get_audio_metadata(self.mock_mp3_path)
            self.assertEqual(metadata, {})

    def test_get_audio_metadata_file_not_found(self):
        metadata = get_audio_metadata("non_existent_file.mp3")
        self.assertEqual(metadata, {})

    # --- validate_audio_file ---

    @patch("src.meeting_transcription_tool.audio_processor.get_audio_duration", return_value=10)
    def test_validate_audio_file_happy(self, mock_get_duration):
        ok, reason = validate_audio_file(self.mock_mp3_path)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_validate_audio_file_not_found(self):
        ok, reason = validate_audio_file("non_existent_file.mp3")
        self.assertFalse(ok)
        self.assertTrue("File not found" in reason)

    def test_validate_audio_file_unsupported_format(self):
        ok, reason = validate_audio_file(self.mock_txt_path)
        self.assertFalse(ok)
        self.assertTrue("Unsupported format" in reason)

    @patch("os.path.getsize", return_value=3 * 1024 * 1024 * 1024)
    def test_validate_audio_file_too_large(self, mock_getsize):
        ok, reason = validate_audio_file(self.mock_mp3_path)
        self.assertFalse(ok)
        self.assertTrue("File is too large" in reason)

    @patch("src.meeting_transcription_tool.audio_processor.get_audio_duration", return_value=6 * 60 * 60)
    def test_validate_audio_file_too_long(self, mock_get_duration):
        ok, reason = validate_audio_file(self.mock_mp3_path)
        self.assertFalse(ok)
        self.assertTrue("File is too long" in reason)

    # --- Other utils ---

    def test_bytes_to_readable(self):
        self.assertEqual(bytes_to_readable(500), "500 B")
        self.assertEqual(bytes_to_readable(1500), "1.46 KB")
        self.assertEqual(bytes_to_readable(1500000), "1.43 MB")

    def test_ms_to_hhmmss(self):
        self.assertEqual(ms_to_hhmmss(1000), "00:00:01")
        self.assertEqual(ms_to_hhmmss(61000), "00:01:01")
        self.assertEqual(ms_to_hhmmss(3661000), "01:01:01")

    def test_ms_to_srt_timestamp(self):
        self.assertEqual(ms_to_srt_timestamp(1234), "00:00:01,234")
        self.assertEqual(ms_to_srt_timestamp(61234), "00:01:01,234")
        self.assertEqual(ms_to_srt_timestamp(3661234), "01:01:01,234")


if __name__ == "__main__":
    unittest.main()
