import os
import unittest
from unittest.mock import patch, AsyncMock
from click.testing import CliRunner

# Make sure src is in the path for tests to run
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.meeting_transcription_tool.cli import cli

class TestCli(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.test_dir = "test_data"
        self.output_dir = os.path.join(self.test_dir, "outputs")
        self.input_audio = os.path.join(self.test_dir, "sample.mp3")

        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.input_audio, "wb") as f:
            f.write(b"mock_audio_content")

    def tearDown(self):
        # Clean up created files
        if os.path.exists(self.output_dir):
            for f in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, f))
            os.rmdir(self.output_dir)
        if os.path.exists(self.input_audio):
            os.remove(self.input_audio)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    @patch("src.meeting_transcription_tool.cli.validate_audio_file", return_value=(True, ""))
    @patch("src.meeting_transcription_tool.cli.identify_speakers")
    @patch("src.meeting_transcription_tool.cli.run_transcription_pipeline", new_callable=AsyncMock)
    def test_cli_transcribe_command(self, mock_pipeline, mock_identify, mock_validate):
        # Mock the pipeline to return a predictable result
        from src.meeting_transcription_tool.transcriber import TranscriptionResult
        from src.meeting_transcription_tool.exporter import TranscriptSegment
        from src.meeting_transcription_tool.speaker_identifier import SpeakerIdentificationResult

        mock_pipeline.return_value = TranscriptionResult(
            text="Hello world.",
            segments=[
                TranscriptSegment(start_ms=0, end_ms=1000, text="Hello", speaker="SPEAKER_00"),
                TranscriptSegment(start_ms=1000, end_ms=2000, text="world.", speaker="SPEAKER_01"),
            ],
            raw={}
        )

        mock_identify.return_value = SpeakerIdentificationResult(
            mappings={"SPEAKER_00": "Narrator", "SPEAKER_01": "Guest"},
            model="gpt-5-mini",
            provider="openai",
            request_metadata={"api_method": "responses"},
            response_metadata={"status": "mocked"},
        )

        # Run the CLI command
        result = self.runner.invoke(
            cli,
            [
                "transcribe",
                "--input", self.input_audio,
                "--output-dir", self.output_dir,
                "--formats", "txt",
                "--formats", "json"
            ],
        )

        # Check that the command executed successfully
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("Transcription complete!", result.output)

        # Check that the output files were created
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "sample.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "sample.json")))

if __name__ == "__main__":
    unittest.main()
