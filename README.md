# Meeting Transcription Tool

Modern transcription pipeline with diarization, GPT-5 Mini speaker relabeling, and production-ready exports.

### Highlights
- Whisper-based transcription with accurate diarization.
- GPT-5 Mini reasoning for speaker name/role identification (audio upload + timeline aware).
- Modular CLI stages for fast iteration and auditing.
- Rich exports (TXT, JSON, SRT, DOCX) plus per-run summary reports.
- Automated MkDocs documentation and GitHub Pages publishing.

### Quick Start
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Optional: documentation tooling
pip install -r docs/requirements.txt

python -m src.meeting_transcription_tool.cli transcribe --input "/path/to/audio.m4a"
```

Outputs include diarized transcripts, GPT-5 Mini speaker-labelled transcripts, JSON/SRT exports, and detailed summary reports.

### Documentation
The `docs/` directory is the single source of truth for project guidance.  
MkDocs (Material theme) builds the GitHub Pages site from these files.

- [Overview](docs/index.md)
- [Getting Started](docs/getting-started.md)
- [Pipeline Stages](docs/pipeline.md)
- [Speaker Identification](docs/speaker-identification.md)
- [Contributing](docs/contributing.md)

### Contributing
See the [contributor guide](docs/contributing.md) for branching strategy, coding standards, testing, and documentation expectations before opening a PR.

### License
MIT License – see [`LICENSE`](LICENSE).
