# Meeting Transcription Tool

Welcome to the single source of truth for the Meeting Transcription Tool.  
This documentation covers everything you need to install, operate, and extend the project.

## Key Capabilities
- Accurate Whisper-based transcription with diarization.
- GPT-5 Mini (with reasoning) speaker relabeling that honours timeline metadata and attached audio.
- Modular pipeline stages for rapid testing and iteration.
- Rich exports (TXT, JSON, SRT, DOCX) plus per-run summary reports and cost estimates.
- Automated documentation publishing via GitHub Pages.

## Quick Start
1. **Install dependencies** – see [Getting Started](./getting-started.md#installation).
2. **Set up credentials** – configure OpenAI, Hugging Face, and optional Google keys.
3. **Transcribe a file**:
   ```bash
   python -m src.meeting_transcription_tool.cli transcribe --input path/to/audio.m4a
   ```
4. **Review outputs** – transcripts, speaker-labelled variants, and summary reports live in your chosen output directory.

## Documentation Map
- [Getting Started](./getting-started.md) – environment, configuration, and CLI basics.
- [Pipeline Stages](./pipeline.md) – detailed explanation of each stage and intermediate artefact.
- [Speaker Identification](./speaker-identification.md) – GPT-5 Mini prompts, audio uploads, and auditing metadata.
- [Contributing](./contributing.md) – development workflow, coding standards, testing, and documentation guidelines.

## Support & Feedback
Open an issue on GitHub for bugs or feature ideas. Pull requests are welcome—please read the [contribution guidelines](./contributing.md) first.

