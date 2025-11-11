# Getting Started

This guide walks you through preparing a development environment, installing dependencies, and running the transcription pipeline end to end.

## Prerequisites
- Python 3.9 or newer.
- FFmpeg installed and available on your `PATH`.
- Basic command-line familiarity.

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Optional: documentation tooling
pip install -r docs/requirements.txt
```

### Project Extras (PyProject)
To install everything (runtime + docs) in one command:
```bash
pip install .[docs]
```

## API Credentials
Create a `.env` file (or export env vars) with the following keys:
```
OPENAI_API_KEY=your_openai_key_here
HUGGING_FACE_TOKEN=your_hf_token_here
GOOGLE_API_KEY=your_google_key_here  # optional, Gemini support
```

- OpenAI: required for transcription (`whisper-1`) and GPT-5 Mini speaker identification.
- Hugging Face: required for diarization models.
- Google: optional, only needed if you plan to run Gemini-based speaker identification.

## Verifying Dependencies
After activation run:
```bash
python -m pip check
pytest
```
All tests should pass, confirming an end-to-end functional environment.

## First Transcription
```bash
python -m src.meeting_transcription_tool.cli transcribe --input "/path/to/audio.m4a"
```

### Outputs
- `audio.txt` – transcript with diarization labels.
- `audio_speakers.txt` – GPT-5 Mini labelled transcript (names/roles applied).
- `audio.json` – structured transcript with metadata.
- `audio.srt` – subtitles.
- `audio_SUMMARY.txt` – processing + cost breakdown.

### Batch Mode
```bash
python -m src.meeting_transcription_tool.cli transcribe \
    --input "/path/to/directory" \
    --file-filter "*.mp3"
```

### Speaker Identification Controls
- `--ai-model gpt-5-mini` (default)
- `--ai-model gpt-4o`
- `--ai-model gemini-2.0-flash`
- `--no-identify-speakers`

## Working With Pipeline Stages
For faster iteration:
1. Run `cli_stages stage1` once to cache the transcription.
2. Run `cli_stages stage2` repeatedly while tweaking speaker-identification logic.
3. Run `cli_stages stage3` to generate exports using the latest mappings.

See [Pipeline Stages](./pipeline.md) for details.

## Next Steps
- Understand the [speaker identification pipeline](./speaker-identification.md).
- Learn how to contribute and run linters in the [contributor guide](./contributing.md).

