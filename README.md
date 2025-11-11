# Meeting Transcription Tool

Professional-grade audio transcription with AI-powered speaker identification, batch processing, and clean output.

## Features

✅ **Transcription** - OpenAI Whisper API  
✅ **Speaker Diarization** - pyannote.audio identifies different speakers  
✅ **AI Speaker Identification** - GPT-4o or Gemini identifies speakers by name (enabled by default)  
✅ **Clean Text Output** - Filters garbled characters and silence artifacts  
✅ **Multiple Formats** - TXT, JSON, SRT, DOCX  
✅ **Batch Processing** - Process multiple files in parallel  
✅ **Modular Pipeline** - Test stages independently  
✅ **Smart Context Extraction** - Automatically extracts meeting info from filenames

---

## Quick Start

### Installation

```powershell
# Clone and setup
git clone <repository>
cd meeting-transcription-tool
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (required for M4A files)
# See INSTALL_FFMPEG.md for details
choco install ffmpeg
```

### Setup API Keys

Create `.env` file in project root:

```
OPENAI_API_KEY=your_openai_key_here
HUGGING_FACE_TOKEN=your_hf_token_here
GOOGLE_API_KEY=your_google_key_here  # Optional, for Gemini
```

**Note**: Accept Hugging Face model agreements (see HUGGINGFACE_SETUP.md)

---

## Usage

### Single File (default settings)

```powershell
# Full transcription with AI speaker identification (default)
python -m src.meeting_transcription_tool.cli transcribe --input "meeting.m4a"
```

**Output**:
- `meeting.txt` - Transcript with generic labels (SPEAKER_00, SPEAKER_01)
- `meeting_speakers.txt` - With AI-identified names (Ian, Candidate)
- `meeting.json` - JSON format
- `meeting.srt` - Subtitles
- `meeting_SUMMARY.txt` - Processing report

### Entire Directory (auto parallelism)

```powershell
# Process every M4A file in a directory
python -m src.meeting_transcription_tool.cli transcribe `
    --input "F:\Meetings\" `
    --file-filter "*.m4a"
```

> ℹ️ Parallel workers are auto-detected (CPU cores − 1, capped at 8).  
> The CLI prints the detected value before processing begins.

### Directory With Manual Parallel Override

```powershell
# Force 6 parallel workers (overrides auto-detected value)
python -m src.meeting_transcription_tool.cli transcribe `
    --input "F:\Meetings\" `
    --parallel 6
```

**Output**: All files transcribed + **ONE** consolidated summary: `batch_summary_YYYYMMDD_HHMMSS.txt`

### Without AI Speaker Identification

```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "meeting.m4a" `
    --no-identify-speakers
```

---

## Modular Pipeline (For Testing)

Break the pipeline into stages for faster development:

```powershell
# Stage 1: Transcribe & Diarize (run once, ~8-10 min)
python -m src.meeting_transcription_tool.cli_stages stage1 `
    --input "meeting.m4a" `
    --output-dir "./output"

# Stage 2: AI Speaker ID (test quickly, ~2-5 sec)
python -m src.meeting_transcription_tool.cli_stages stage2 `
    --input "./output/meeting_stage1_transcript.json" `
    --output-dir "./output" `
    --speaker-context "1-on-1 interview"

# Stage 3: Create Files (instant)
python -m src.meeting_transcription_tool.cli_stages stage3 `
    --transcript "./output/meeting_stage1_transcript.json" `
    --mappings "./output/meeting_stage2_speaker_mappings.json" `
    --output-dir "./output"
```

**See PIPELINE_TESTING.md for detailed guide**

---

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` `-i` | Audio file or directory | Required |
| `--output-dir` `-o` | Output directory | Same as input |
| `--formats` | Output formats (`--formats txt json`) | txt,json,srt |
| `--language` | Whisper language hint (ISO code) | Auto-detect |
| `--temperature` | Whisper sampling temperature | 0.0 |
| `--model` | Whisper model name | whisper-1 |
| `--api-key` | Override `OPENAI_API_KEY` | `.env` / env var |
| `--hf-token` | Override `HUGGING_FACE_TOKEN` | `.env` / env var |
| `--identify-speakers` | AI speaker identification | **Enabled** |
| `--no-identify-speakers` | Disable AI speaker ID | - |
| `--speaker-context` | Meeting context | Auto-extract |
| `--ai-model` | AI model (gpt-4o/gemini-2.0-flash) | gpt-4o |
| `--file-filter` | Batch file pattern | *.m4a |
| `--parallel` `-p` | Parallel workers | Auto (CPU cores − 1, max 8) |
| `--overwrite` | Overwrite existing output files | Enabled |

---

## Command Recipes

Use these copy‑paste friendly examples to cover common scenarios:

### 1. Process a Single File With Default Settings
```powershell
python -m src.meeting_transcription_tool.cli transcribe --input "C:\Audio\interview.m4a"
```

### 2. Process an Entire Directory (auto parallel)
```powershell
python -m src.meeting_transcription_tool.cli transcribe --input "F:\Meta\Quarterly Reviews"
```

### 3. Restrict to MP3 Files
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "F:\Meta\Raw Audio" `
    --file-filter "*.mp3"
```

### 4. Choose a Custom Output Folder
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "C:\Audio\demo.m4a" `
    --output-dir "C:\Transcripts\demo-output"
```

### 5. Export Only TXT + JSON
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "C:\Audio\standup.m4a" `
    --formats txt json
```

### 6. Provide Meeting Context (improves name resolution)
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "C:\Audio\board-meeting.m4a" `
    --speaker-context "Quarterly board review with CEO Alice Chen and CFO David Ortiz"
```

### 7. Force English Transcription & Warmer Temperature
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "C:\Audio\podcast-episode.mp3" `
    --language en `
    --temperature 0.4
```

### 8. Use Gemini for Speaker Identification
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "C:\Audio\panel.m4a" `
    --ai-model gemini-2.0-flash
```

### 9. Disable AI Speaker Identification Entirely
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "C:\Audio\training-session.m4a" `
    --no-identify-speakers
```

### 10. Supply API Credentials Inline (overrides `.env`)
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "C:\Audio\press-briefing.m4a" `
    --api-key sk-your-openai-key `
    --hf-token hf_your_hf_token
```

### 11. Manual Parallel Override (power users)
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "F:\Meta\All Hands\" `
    --parallel 5
```

---

## Output Files

### With AI Speaker ID (Default)
- `filename.txt` - Generic labels (SPEAKER_00, SPEAKER_01)
- `filename_speakers.txt` - AI names (Ian, Candidate)
- `filename.json`, `filename.srt` - Other formats
- `filename_SUMMARY.txt` - Individual report

### Batch Mode
- Individual files for each audio file
- **ONE** consolidated: `batch_summary_YYYYMMDD_HHMMSS.txt`

---

## Processing Time & Cost

### Time (30-minute audio)
- Diarization: ~5-6 minutes
- Transcription: ~3-4 minutes
- AI Speaker ID: ~2-5 seconds
- **Total**: ~8-10 minutes

### Cost (30-minute audio)
- Whisper: $0.18
- Speaker ID (GPT-4o): $0.01-0.02
- Speaker ID (Gemini): $0.005-0.01
- **Total**: ~$0.19-0.20

---

## Examples

### Interview
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "Ian 1on1 interview.m4a"
# Auto-detects: "1-on-1 meeting with Ian"
# Result: Ian → Ian, other speaker → Candidate
```

### Team Meeting
```powershell
python -m src.meeting_transcription_tool.cli transcribe `
    --input "team-standup.m4a" `
    --speaker-context "Weekly standup, Sarah is manager"
```

### Compare AI Models
```powershell
# Test GPT-4o vs Gemini on same file
python -m src.meeting_transcription_tool.cli_stages stage2 `
    --input "output/meeting_stage1_transcript.json" `
    --ai-model gpt-4o

python -m src.meeting_transcription_tool.cli_stages stage2 `
    --input "output/meeting_stage1_transcript.json" `
    --ai-model gemini-2.0-flash
```

---

## Documentation

- **PIPELINE_TESTING.md** - Modular pipeline guide
- **SETUP_GUIDE.md** - Detailed setup instructions
- **HUGGINGFACE_SETUP.md** - HuggingFace model setup
- **INSTALL_FFMPEG.md** - FFmpeg installation

---

## Project Structure

```
src/meeting_transcription_tool/
├── cli.py                 # Main CLI (full pipeline)
├── cli_stages.py          # Modular stages CLI
├── pipeline_stages.py     # Stage functions
├── audio_processor.py     # Audio validation
├── transcriber.py         # Whisper transcription
├── diarization.py         # Speaker diarization
├── speaker_identifier.py  # AI speaker identification
├── context_extractor.py   # Smart context from filenames
├── exporter.py            # Multiple format export
└── summary_report.py      # Metrics & reporting

tests/
├── test_*.py              # Unit tests
└── conftest.py            # Test fixtures
```

---

## Troubleshooting

### "FFmpeg not found"
Install FFmpeg (required for M4A):
```powershell
choco install ffmpeg
```

### "Gated model" error
Accept Hugging Face agreements:
1. https://huggingface.co/pyannote/speaker-diarization-3.1
2. https://huggingface.co/pyannote/segmentation-3.0

### Speaker ID not working
Check `.env` has `OPENAI_API_KEY` set correctly.

---

## Development

### Run Tests
```powershell
pytest
pytest --cov=src/meeting_transcription_tool
```

### Test Individual Stages
See PIPELINE_TESTING.md for modular testing workflow.

---

## License

[Your License]

---

## Version

Current: 1.0.0
- ✅ Transcription with Whisper
- ✅ Speaker diarization
- ✅ AI speaker identification (default)
- ✅ Clean text filtering
- ✅ Batch processing with parallel execution
- ✅ Modular pipeline for testing
- ✅ Consolidated batch summaries
