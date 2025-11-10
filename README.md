# Meeting Transcription Tool

# Meeting Transcription Tool

Simple CLI to transcribe meeting audio using OpenAI Whisper and export to TXT/JSON/SRT/DOCX.

## Quick Start (Windows / PowerShell)

1) Create and activate a virtual environment:

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```

2) Install dependencies:

```powershell
pip install -U pip
pip install -r requirements.txt
```

3) Set your OpenAI API key (PowerShell session):

```powershell
$env:OPENAI_API_KEY = "YOUR_OPENAI_KEY"
```

4) Run transcription:

```powershell
python -m meeting_transcription_tool.cli transcribe `
  --input "F:\Meta\Final Proof With Audio and Transcript\Jason 1on1 - Q3 2025 Performance 09-19 09-37 am.m4a" `
  --output-dir "outputs" `
  --formats txt json srt docx
```

Outputs will be written to the `outputs` directory.

> Note: If you prefer, you can pass `--api-key` on the command instead of using the environment variable.

## Features

- Transcription via OpenAI Whisper (`whisper-1` by default)
- Exports:
  - TXT (with `[HH:MM:SS - HH:MM:SS] Speaker X: text`)
  - JSON (structured with metadata)
  - SRT (subtitle format)
  - DOCX (requires `python-docx`)
- Basic audio validation (format and size)
- Clean CLI with progress indicator

## Limitations / Roadmap

- Speaker diarization is not implemented yet; segments are labeled `Speaker 1`. We can add diarization in a subsequent version.
- Duration validation is not enforced to keep setup simple (no ffmpeg requirement).

## Developer Notes

- Project structure:

```
meeting_transcription_tool/
  cli.py
  exporters.py
  transcriber.py
  utils.py
```

- Invoke CLI via module: `python -m meeting_transcription_tool.cli`
- Configure `OPENAI_API_KEY` in your environment or use `--api-key` flag.

A Python-based tool to upload meeting audio files and generate transcripts with speaker labels and timestamps, similar to the transcription feature in Microsoft Word.

## Features

- 🎙️ **Audio Upload**: Support for various audio formats (MP3, WAV, M4A, etc.)
- 👥 **Speaker Diarization**: Identify and label different speakers in the meeting
- ⏱️ **Timestamps**: Precise timestamps for each spoken segment
- 📝 **Text Transcription**: High-quality speech-to-text conversion
- 📄 **Export Options**: Export transcripts in multiple formats (TXT, DOCX, JSON, SRT)
- 🎯 **MS Word Style**: Output format similar to Microsoft Word's transcription feature

## Project Structure

```
meeting-transcription-tool/
├── src/
│   ├── __init__.py
│   ├── audio_processor.py    # Audio file handling and preprocessing
│   ├── transcriber.py        # Speech-to-text transcription
│   ├── diarization.py        # Speaker identification and labeling
│   └── exporter.py           # Export transcripts to various formats
├── tests/
│   ├── test_audio_processor.py
│   ├── test_transcriber.py
│   └── test_diarization.py
├── data/
│   ├── sample_audio/         # Sample audio files for testing
│   └── output/               # Generated transcripts
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup
├── README.md
└── .gitignore
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- FFmpeg (for audio processing)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/neerazz/meeting-transcription-tool.git
cd meeting-transcription-tool
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg:
- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Usage

### Basic Usage

```python
from src.transcriber import MeetingTranscriber

# Initialize the transcriber
transcriber = MeetingTranscriber()

# Transcribe an audio file
result = transcriber.transcribe(
    audio_file="path/to/meeting.mp3",
    enable_diarization=True,
    num_speakers=3  # Optional: specify number of speakers
)

# Export the transcript
result.export("output.docx", format="docx")
```

### Command Line Interface

```bash
# Basic transcription
python -m src.main --input meeting.mp3 --output transcript.txt

# With speaker diarization
python -m src.main --input meeting.mp3 --output transcript.docx --speakers 3

# Specify output format
python -m src.main --input meeting.mp3 --output transcript.json --format json
```

## Technologies & Libraries

### Planned Technologies:

- **Speech Recognition**:
  - OpenAI Whisper (recommended for high accuracy)
  - Google Speech-to-Text API
  - Azure Speech Services
  - AssemblyAI API

- **Speaker Diarization**:
  - pyannote.audio
  - resemblyzer
  - speechbrain

- **Audio Processing**:
  - pydub
  - librosa
  - soundfile

- **Export Formats**:
  - python-docx (for DOCX)
  - reportlab (for PDF)
  - json, csv (built-in)

## Output Format

The transcript will be formatted similar to MS Word's transcription:

```
[00:00:00] Speaker 1: Welcome everyone to today's meeting.

[00:00:05] Speaker 2: Thanks for having me. Let's discuss the project timeline.

[00:00:12] Speaker 1: Sure, we have three main milestones to cover.

[00:00:18] Speaker 3: I'd like to add some points about the budget.
```

## Development

### Setting up Development Environment

This project is designed to work with:
- **Cursor IDE**
- **Visual Studio Code**
- **JetBrains PyCharm / IntelliJ IDEA**

### Recommended VS Code Extensions:
- Python
- Pylance
- Python Test Explorer
- GitLens

### Recommended PyCharm Plugins:
- Python Community Edition features
- Key Promoter X
- Rainbow Brackets

## Roadmap

- [ ] Set up project structure
- [ ] Implement audio file upload and validation
- [ ] Integrate speech-to-text API (Whisper/Google/Azure)
- [ ] Implement speaker diarization
- [ ] Add timestamp generation
- [ ] Create export functionality (TXT, DOCX, JSON)
- [ ] Build command-line interface
- [ ] Add web interface (Flask/FastAPI)
- [ ] Implement batch processing
- [ ] Add support for video files
- [ ] Create Docker container
- [ ] Add unit tests
- [ ] Write documentation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by Microsoft Word's transcription feature
- Thanks to the open-source community for the amazing tools and libraries

## Contact

Neeraj Kumar Singh B - [@neerazz](https://github.com/neerazz)

Project Link: [https://github.com/neerazz/meeting-transcription-tool](https://github.com/neerazz/meeting-transcription-tool)
