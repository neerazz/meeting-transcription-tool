# Meeting Transcription Tool

Modern transcription pipeline with diarization, GPT-5 Mini speaker relabeling, comprehensive AI logging, and production-ready exports.

## Highlights
- **Whisper-based transcription** with accurate diarization
- **GPT-5 Mini reasoning** for speaker name/role identification (audio upload + timeline aware)
- **Comprehensive AI logging** - track every request/response with cost analysis
- **Intelligent prompt optimization** - saves tokens when filename has context, uses full transcript for quality
- **Parallel processing** - auto-optimized to 50% CPU utilization
- **Modular CLI stages** for fast iteration and auditing
- **Rich exports** (TXT, JSON, SRT, DOCX) plus per-run summary reports
- **Automated documentation** with MkDocs and GitHub Pages

## Quick Start

### Installation
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Setup API Keys
Create `.env` file:
```
OPENAI_API_KEY=your_openai_key_here
HUGGING_FACE_TOKEN=your_hf_token_here
GOOGLE_API_KEY=your_google_key_here  # optional, for Gemini
```

### Basic Usage
```bash
python -m src.meeting_transcription_tool.cli transcribe --input "/path/to/audio.m4a"
```

**Outputs:**
- `audio.txt` - Transcript with diarization labels
- `audio_speakers.txt` - GPT-5 Mini labelled transcript (names/roles)
- `audio.json` - Structured transcript with metadata
- `audio.srt` - Subtitles
- `audio_SUMMARY.txt` - Processing report with cost breakdown

## Usage Examples

### 1. Single File Transcription
```bash
python -m src.meeting_transcription_tool.cli transcribe \
    --input "meeting.m4a" \
    --output-dir "./output"
```

### 2. Batch Processing (Auto-Parallel)
```bash
# Process all M4A files in a directory
python -m src.meeting_transcription_tool.cli transcribe \
    --input "/path/to/meetings" \
    --file-filter "*.m4a" \
    --output-dir "./output"

# Auto-detects optimal parallel workers (50% of CPU cores)
```

### 3. Custom Parallel Workers
```bash
# Override auto-detection
python -m src.meeting_transcription_tool.cli transcribe \
    --input "/path/to/meetings" \
    --parallel 8
```

### 4. Different AI Models
```bash
# Use GPT-5 Mini (default, reasoning model)
python -m src.meeting_transcription_tool.cli transcribe \
    --input "meeting.m4a" \
    --ai-model gpt-5-mini

# Use GPT-4o
python -m src.meeting_transcription_tool.cli transcribe \
    --input "meeting.m4a" \
    --ai-model gpt-4o

# Use Gemini 2.0 Flash
python -m src.meeting_transcription_tool.cli transcribe \
    --input "meeting.m4a" \
    --ai-model gemini-2.0-flash

# Disable speaker identification
python -m src.meeting_transcription_tool.cli transcribe \
    --input "meeting.m4a" \
    --no-identify-speakers
```

### 5. Provide Meeting Context
```bash
# Help AI identify speakers with context
python -m src.meeting_transcription_tool.cli transcribe \
    --input "meeting.m4a" \
    --speaker-context "Quarterly review with CEO Alice Chen and CFO David Ortiz"
```

### 6. Custom Output Formats
```bash
# Export only specific formats
python -m src.meeting_transcription_tool.cli transcribe \
    --input "meeting.m4a" \
    --formats txt json srt docx
```

### 7. Pipeline Stages (For Testing/Iteration)

#### Stage 1: Transcribe & Diarize
```bash
python -m src.meeting_transcription_tool.cli_stages stage1 \
    --input "meeting.m4a" \
    --output-dir "./output"
```
Creates: `meeting_stage1_transcript.json`

#### Stage 2: AI Speaker Identification
```bash
python -m src.meeting_transcription_tool.cli_stages stage2 \
    --input "./output/meeting_stage1_transcript.json" \
    --output-dir "./output" \
    --ai-model gpt-5-mini \
    --speaker-context "1-on-1 interview"
```
Creates: `meeting_stage2_speaker_mappings.json` (includes full AI request/response logs)

#### Stage 3: Apply Names & Export
```bash
python -m src.meeting_transcription_tool.cli_stages stage3 \
    --transcript "./output/meeting_stage1_transcript.json" \
    --mappings "./output/meeting_stage2_speaker_mappings.json" \
    --output-dir "./output" \
    --formats txt json srt
```

### 8. Process Directory from Stage 2
```bash
# Process all stage1 files through stage2 in parallel
python process_stage2_directory.py \
    -d "/path/to/stage1/files" \
    -o "/path/to/output" \
    --ai-model gpt-5-mini \
    --parallel 8  # Optional: override auto-detection
```

### 9. View AI Costs
```bash
# View comprehensive cost summary
python view_ai_costs.py
```

Shows:
- Total API calls
- Total cost (USD)
- Token usage (input/output)
- Last 24 hours summary

### 10. Check AI Logs
```bash
# View all AI request/response logs
ls -lh ./ai_logs/

# View a specific request
cat ./ai_logs/ai_request_*.json

# View corresponding response
cat ./ai_logs/ai_request_*_response.json
```

## AI Optimization Features

### Intelligent Prompt Optimization
- **Filename has context**: Uses truncated transcript (8000 chars) → saves tokens
- **Filename lacks context**: Uses FULL transcript → maximum quality
- Automatic detection and optimization

### Comprehensive Logging
- Every AI call logged to `./ai_logs/`
- Full request/response data
- Token usage and cost tracking
- View with `python view_ai_costs.py`

### Parallel Processing
- Auto-detects CPU cores
- Uses 50% of CPU (optimal balance)
- Maximum 16 workers
- Prevents system overload

### Filename Intelligence
The system automatically extracts:
- Participant names (up to 4 names)
- Meeting types (1-on-1, interview, review, etc.)
- Dates and times
- Context descriptions

**Best Practice**: Use descriptive filenames like:
- `Alice_Bob_1on1_2024-01-15.m4a` ✅
- `meeting.m4a` ❌

## Output Files

### With Speaker Identification (Default)
- `filename.txt` - Generic labels (SPEAKER_00, SPEAKER_01)
- `filename_speakers.txt` - AI-identified names (Alice, Bob, Manager)
- `filename.json` - Structured JSON with metadata
- `filename.srt` - Subtitles
- `filename_SUMMARY.txt` - Processing report with costs

### Batch Mode
- Individual files for each audio file
- Consolidated `batch_summary_YYYYMMDD_HHMMSS.txt`

## Cost Optimization Tips

1. **Use descriptive filenames** - Include participant names
2. **Monitor costs** - Run `python view_ai_costs.py` regularly
3. **Review logs** - Check `./ai_logs/` to see what's being sent
4. **Choose right model** - GPT-5 Mini (o1-mini) is most cost-effective for reasoning

## Quality Optimization Tips

1. **Provide context** - Use `--speaker-context` if filename doesn't help
2. **Full transcript mode** - System auto-uses full transcript if filename lacks context
3. **Review mappings** - Check `_stage2_speaker_mappings.json` for reasoning
4. **Timeline accuracy** - All timestamps preserved in exports

## Documentation

The `docs/` directory is the single source of truth.  
MkDocs (Material theme) builds the GitHub Pages site.

- [Overview](docs/index.md)
- [Getting Started](docs/getting-started.md)
- [Pipeline Stages](docs/pipeline.md)
- [Speaker Identification](docs/speaker-identification.md)
- [Contributing](docs/contributing.md)
- [AI Optimization Guide](AI_OPTIMIZATION_GUIDE.md)

## Troubleshooting

### High AI Costs
- Check `./ai_logs/` for large requests
- Ensure filenames have participant names
- Review token usage in logs

### Poor Speaker Identification
- Ensure filenames are descriptive
- Provide `--speaker-context` manually
- Check if full transcript is being used (see logs)

### Processing Hangs
- Check timeout settings (300s default)
- Reduce parallel workers if CPU overloaded
- Check network connectivity

## Contributing

See the [contributor guide](docs/contributing.md) for:
- Branching strategy
- Coding standards
- Testing requirements
- Documentation expectations

## License

MIT License – see [`LICENSE`](LICENSE).
