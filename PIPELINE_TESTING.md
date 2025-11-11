# Modular Pipeline Testing Guide

## Overview

The transcription pipeline is now broken into **3 independent stages** that you can run and test separately. This saves time during development by avoiding re-running the entire pipeline.

---

## Pipeline Stages

### 🔵 **Stage 1: Transcribe & Diarize**
- **Input**: Audio file (MP3, WAV, M4A, FLAC)
- **Output**: `filename_stage1_transcript.json` (intermediate file)
- **What it does**: Transcribes audio with Whisper, identifies speakers with pyannote
- **Time**: ~8-10 minutes

### 🟢 **Stage 2: AI Speaker Identification**
- **Input**: `filename_stage1_transcript.json`
- **Output**: `filename_stage2_speaker_mappings.json`
- **What it does**: Uses AI to identify speakers (SPEAKER_00 → Ian, etc.)
- **Time**: ~2-5 seconds

### 🟡 **Stage 3: Create Final Files**
- **Input**: Stage 1 transcript + Stage 2 mappings
- **Output**: Final transcripts (`filename.txt`, `filename_speakers.txt`, etc.)
- **What it does**: Applies speaker names, creates clean output files
- **Time**: <1 second

---

## Usage

### Run Individual Stages

```powershell
# Stage 1: Transcribe & Diarize (only once!)
python -m src.meeting_transcription_tool.cli_stages stage1 `
    --input "meeting.m4a" `
    --output-dir "./output"

# Output: meeting_stage1_transcript.json

# Stage 2: Identify Speakers (test AI prompts quickly!)
python -m src.meeting_transcription_tool.cli_stages stage2 `
    --input "./output/meeting_stage1_transcript.json" `
    --output-dir "./output" `
    --speaker-context "1-on-1 interview"

# Output: meeting_stage2_speaker_mappings.json

# Stage 3: Create Final Files (instant!)
python -m src.meeting_transcription_tool.cli_stages stage3 `
    --transcript "./output/meeting_stage1_transcript.json" `
    --mappings "./output/meeting_stage2_speaker_mappings.json" `
    --output-dir "./output" `
    --formats txt json srt

# Output: meeting.txt, meeting_speakers.txt, meeting.json, meeting.srt
```

---

## Testing Workflows

### Workflow 1: Test AI Speaker Identification

You want to test different AI prompts/contexts without re-transcribing:

```powershell
# 1. Transcribe ONCE
python -m src.meeting_transcription_tool.cli_stages stage1 `
    --input "meeting.m4a" `
    --output-dir "./output"

# 2. Test different contexts (fast! ~2-5 seconds each)
python -m src.meeting_transcription_tool.cli_stages stage2 `
    --input "./output/meeting_stage1_transcript.json" `
    --output-dir "./output" `
    --speaker-context "1-on-1 interview"

python -m src.meeting_transcription_tool.cli_stages stage2 `
    --input "./output/meeting_stage1_transcript.json" `
    --output-dir "./output" `
    --speaker-context "Team standup with Sarah as manager"

# 3. Create final files with best mapping
python -m src.meeting_transcription_tool.cli_stages stage3 `
    --transcript "./output/meeting_stage1_transcript.json" `
    --mappings "./output/meeting_stage2_speaker_mappings.json" `
    --output-dir "./output"
```

### Workflow 2: Test Without AI (Faster)

Skip AI speaker identification:

```powershell
# 1. Transcribe
python -m src.meeting_transcription_tool.cli_stages stage1 `
    --input "meeting.m4a" `
    --output-dir "./output"

# 2. Create files directly (no speaker ID)
python -m src.meeting_transcription_tool.cli_stages stage3 `
    --transcript "./output/meeting_stage1_transcript.json" `
    --output-dir "./output"

# Output: Only generic labels (SPEAKER_00, SPEAKER_01)
```

### Workflow 3: Test Different AI Models

Compare GPT-4o vs Gemini:

```powershell
# Test GPT-4o
python -m src.meeting_transcription_tool.cli_stages stage2 `
    --input "./output/meeting_stage1_transcript.json" `
    --output-dir "./output/gpt4o" `
    --ai-model gpt-4o

# Test Gemini
python -m src.meeting_transcription_tool.cli_stages stage2 `
    --input "./output/meeting_stage1_transcript.json" `
    --output-dir "./output/gemini" `
    --ai-model gemini-2.0-flash

# Compare results!
```

---

## List Intermediate Files

```powershell
python -m src.meeting_transcription_tool.cli_stages list-intermediate `
    --directory "./output"
```

**Output:**
```
Intermediate Files in: ./output

Stage 1 Transcripts:
  • meeting_stage1_transcript.json
  • interview_stage1_transcript.json

Stage 2 Speaker Mappings:
  • meeting_stage2_speaker_mappings.json
  • interview_stage2_speaker_mappings.json
```

---

## Intermediate File Format

### Stage 1: `_stage1_transcript.json`

```json
{
  "audio_file": "F:\\Meetings\\meeting.m4a",
  "segments": [
    {
      "start_ms": 0,
      "end_ms": 15000,
      "speaker": "SPEAKER_00",
      "text": "Hello everyone, welcome to the meeting."
    },
    {
      "start_ms": 15000,
      "end_ms": 30000,
      "speaker": "SPEAKER_01",
      "text": "Thanks for having me."
    }
  ],
  "metadata": {
    "audio_file": "F:\\Meetings\\meeting.m4a",
    "model": "whisper-1",
    "speakers_detected": 2,
    "total_segments": 42
  }
}
```

### Stage 2: `_stage2_speaker_mappings.json`

```json
{
  "source_file": "./output/meeting_stage1_transcript.json",
  "audio_file": "F:\\Meetings\\meeting.m4a",
  "ai_model": "gpt-4o",
  "speaker_context": "1-on-1 interview",
  "mappings": {
    "SPEAKER_00": "Ian",
    "SPEAKER_01": "Candidate"
  }
}
```

---

## Benefits

### ✅ **Faster Development**
- Test AI prompts in 2-5 seconds instead of 10 minutes
- Iterate quickly on speaker identification logic

### ✅ **Cost Savings**
- Don't re-run expensive Whisper API calls
- Test different AI models cheaply

### ✅ **Better Testing**
- Test each stage independently
- Debug issues faster
- Compare results easily

### ✅ **Flexible Workflow**
- Skip stages you don't need
- Run stages in different orders
- Reuse intermediate files

---

## Original CLI Still Works!

The original full-pipeline CLI is unchanged:

```powershell
# Full pipeline (all stages automatically)
python -m src.meeting_transcription_tool.cli transcribe `
    --input "meeting.m4a"
```

Use the modular stages CLI (`cli_stages`) for testing and development!

---

## Time Comparison

| Workflow | Old Way | New Way |
|----------|---------|---------|
| Test AI prompt changes | 10 min × N tests | 10 min (once) + 3 sec × N tests |
| Test without speaker ID | 10 min | 8 min (skip stage 2) |
| Compare AI models | 10 min × 2 = 20 min | 10 min (once) + 3 sec × 2 |
| Fix export bug | 10 min × N iterations | 10 min (once) + instant |

**Savings: 90%+ time during development!** 🚀

---

## Quick Reference

```powershell
# List all commands
python -m src.meeting_transcription_tool.cli_stages --help

# Stage 1: Transcribe & Diarize
python -m src.meeting_transcription_tool.cli_stages stage1 --help

# Stage 2: Identify Speakers
python -m src.meeting_transcription_tool.cli_stages stage2 --help

# Stage 3: Create Files
python -m src.meeting_transcription_tool.cli_stages stage3 --help

# List intermediate files
python -m src.meeting_transcription_tool.cli_stages list-intermediate --help
```

