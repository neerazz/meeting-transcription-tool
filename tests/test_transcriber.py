import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Make sure src is in the path for tests to run
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.meeting_transcription_tool.transcriber import transcribe_with_whisper_async
from src.meeting_transcription_tool.exporter import TranscriptSegment

# A mock response object that simulates the OpenAI SDK's response
class MockTranscriptionResponse:
    def __init__(self, text, segments):
        self._text = text
        self._segments = segments

    def model_dump(self):
        return {"text": self._text, "segments": self._segments}

class TestTranscriber(unittest.TestCase):
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

    @patch("src.meeting_transcription_tool.transcriber._get_openai_client")
    def test_transcribe_async_happy_path(self, mock_get_client):
        # Mock the OpenAI client and its response
        mock_client = MagicMock()
        mock_create = AsyncMock()

        # Correctly mock the coroutine function `to_thread`
        async def mock_to_thread(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_response = MockTranscriptionResponse(
            text="Hello world.",
            segments=[{"start": 0.0, "end": 1.0, "text": "Hello world."}]
        )

        # Configure the mock to return a valid response from the create call
        def create_sync(*args, **kwargs):
            return mock_response

        mock_client.audio.transcriptions.create = create_sync

        mock_get_client.return_value = mock_client

        # Run the async function
        with patch('asyncio.to_thread', mock_to_thread):
            result = asyncio.run(transcribe_with_whisper_async(self.mock_audio_path))

        # Assert the results
        self.assertEqual(result.text, "Hello world.")
        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0].text, "Hello world.")

    @patch("src.meeting_transcription_tool.transcriber._get_openai_client")
    def test_transcribe_async_retry_logic(self, mock_get_client):
        # Mock the OpenAI client to fail twice then succeed
        mock_client = MagicMock()

        # Side effect list: two exceptions, then a valid response
        side_effects = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            MockTranscriptionResponse(text="Success", segments=[])
        ]

        def create_sync(*args, **kwargs):
            effect = side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            return effect

        mock_client.audio.transcriptions.create = create_sync
        mock_get_client.return_value = mock_client

        async def mock_to_thread(func, *args, **kwargs):
            return func(*args, **kwargs)

        # Run with retries and a short poll interval for testing
        with patch('asyncio.to_thread', mock_to_thread):
            result = asyncio.run(transcribe_with_whisper_async(
                self.mock_audio_path, max_retries=3, poll_interval=0.1
            ))

        # Assert success on the third attempt
        self.assertEqual(result.text, "Success")

    @patch("src.meeting_transcription_tool.transcriber._get_openai_client")
    def test_transcribe_async_max_retries_failed(self, mock_get_client):
        # Mock the client to fail consistently
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = Exception("Permanent API Error")
        mock_get_client.return_value = mock_client

        async def mock_to_thread(func, *args, **kwargs):
            raise mock_client.audio.transcriptions.create.side_effect

        # Expect the exception to be re-raised after all retries fail
        with self.assertRaises(Exception):
            with patch('asyncio.to_thread', mock_to_thread):
                asyncio.run(transcribe_with_whisper_async(
                    self.mock_audio_path, max_retries=3, poll_interval=0.1
                ))

if __name__ == "__main__":
    unittest.main()
