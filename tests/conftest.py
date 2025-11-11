"""
Pytest configuration and shared fixtures for tests.

This file is automatically loaded by pytest and provides
common fixtures and configuration for all tests.
"""
import os
import sys
import tempfile
import shutil
import pytest

# Add src to path for all tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    # Cleanup
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)


@pytest.fixture
def mock_audio_file(temp_dir):
    """Create a mock audio file for testing."""
    file_path = os.path.join(temp_dir, "test_audio.mp3")
    with open(file_path, "wb") as f:
        f.write(b"mock audio content")
    return file_path


@pytest.fixture
def mock_transcript_segments():
    """Create mock transcript segments for testing."""
    from src.meeting_transcription_tool.exporter import TranscriptSegment
    
    return [
        TranscriptSegment(0, 1000, "Hello world", "SPEAKER_00"),
        TranscriptSegment(1000, 2000, "How are you?", "SPEAKER_01"),
        TranscriptSegment(2000, 3000, "I'm fine", "SPEAKER_00"),
    ]


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return {
        "source_file": "test_audio.mp3",
        "model": "whisper-1",
        "generated_at": "2025-11-10T12:00:00Z",
    }


# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_api: mark test as requiring API keys"
    )

