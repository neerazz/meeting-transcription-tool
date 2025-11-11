# Execution Flow Diagram - Meeting Transcription Tool

## Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLI Entry Point                                  │
│                    cli.py::transcribe_cmd()                              │
└────────────────────────────┬────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────┴─────────────────────┐
        │  Is input a directory?                    │
        └─────┬───────────────────────┬─────────────┘
              │                       │
         YES  │                       │  NO
              ▼                       ▼
    ┌──────────────────┐    ┌──────────────────────┐
    │ Batch Processing │    │ Single File Processing│
    │ _batch_transcribe│    │ _process_single_file  │
    └────────┬─────────┘    └──────────┬────────────┘
             │                         │
             │                         │
             └──────────┬──────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────────────┐
        │  Stage 1: Transcription & Diarization       │
        │  ─────────────────────────────────────────  │
        │                                              │
        │  Function: run_transcription_pipeline()      │
        │  File: transcriber.py                        │
        │                                              │
        │  Inputs:                                     │
        │    - audio_path: str                         │
        │    - hf_token: str                           │
        │    - whisper_kwargs: dict                    │
        │                                              │
        │  Steps:                                      │
        │  1. run_diarization()                       │
        │     ├─ File: diarization.py                 │
        │     ├─ Uses: pyannote.audio Pipeline        │
        │     ├─ Model: pyannote/speaker-diarization  │
        │     └─ Returns: List[SpeakerSegment]         │
        │                                              │
        │  2. transcribe_with_whisper_async()         │
        │     ├─ File: transcriber.py                │
        │     ├─ Uses: OpenAI Whisper API             │
        │     ├─ Model: whisper-1 (default)           │
        │     └─ Returns: TranscriptionResult          │
        │                                              │
        │  3. find_speaker_for_segment()              │
        │     ├─ Maps diarization segments to         │
        │     │  transcription segments               │
        │     └─ Returns: TranscriptionResult with    │
        │        speaker labels (SPEAKER_00, etc.)    │
        │                                              │
        │  Output: TranscriptionResult                 │
        │    - text: str                               │
        │    - segments: List[TranscriptSegment]       │
        │      - start_ms: int                         │
        │      - end_ms: int                           │
        │      - text: str                             │
        │      - speaker: str (SPEAKER_00, etc.)      │
        └──────────────────┬──────────────────────────┘
                           │
                           ▼
        ┌───────────────────────────────────────────────┐
        │  Stage 2: AI Speaker Identification          │
        │  ─────────────────────────────────────────   │
        │                                              │
        │  Function: identify_speakers()               │
        │  File: speaker_identifier.py                 │
        │                                              │
        │  Inputs:                                     │
        │    - transcript_text: str                    │
        │    - num_speakers: int                       │
        │    - participant_names: List[str] (optional)│
        │    - participant_context: str (optional)    │
        │    - filename: str (optional)                 │
        │    - api_key: str                            │
        │    - model: str (gpt-5-mini, gpt-4o, etc.)   │
        │                                              │
        │  Steps:                                      │
        │  1. extract_full_context()                  │
        │     ├─ File: context_extractor.py           │
        │     ├─ Extracts names from filename         │
        │     ├─ Extracts meeting type                │
        │     └─ Returns: context string               │
        │                                              │
        │  2. format_segments_for_prompt()            │
        │     ├─ File: speaker_identifier.py          │
        │     ├─ Formats segments with timeline       │
        │     └─ Returns: formatted transcript text   │
        │                                              │
        │  3. _build_optimized_prompt()               │
        │     ├─ Checks if filename has context       │
        │     ├─ If yes: truncates transcript (8K)    │
        │     ├─ If no: uses FULL transcript          │
        │     └─ Returns: optimized prompt            │
        │                                              │
        │  4. _identify_with_openai()                 │
        │     ├─ Uploads audio file (optional)        │
        │     ├─ Calls OpenAI API                    │
        │     ├─ Model: o1-mini (gpt-5-mini)         │
        │     └─ Returns: SpeakerIdentificationResult │
        │                                              │
        │  Output: SpeakerIdentificationResult         │
        │    - mappings: Dict[str, str]                │
        │      { "SPEAKER_00": "Alice", ... }         │
        │    - model: str                              │
        │    - request_metadata: Dict                 │
        │    - response_metadata: Dict                 │
        └──────────────────┬──────────────────────────┘
                           │
                           ▼
        ┌───────────────────────────────────────────────┐
        │  Stage 3: Apply Mappings & Export           │
        │  ─────────────────────────────────────────   │
        │                                              │
        │  Function: apply_speaker_mappings()          │
        │  File: exporter.py                           │
        │                                              │
        │  Steps:                                      │
        │  1. Apply mappings to segments              │
        │     - Replace SPEAKER_00 with actual names   │
        │                                              │
        │  2. Export files:                           │
        │     - export_txt() → filename.txt           │
        │     - export_txt_with_speakers()            │
        │       → filename_speakers.txt               │
        │     - export_json() → filename.json         │
        │     - export_srt() → filename.srt           │
        │     - export_docx() → filename.docx         │
        │                                              │
        │  Output: List of file paths                  │
        └───────────────────────────────────────────────┘
```

## Current Implementation Issues

### 1. No Caching
- **Problem**: Every run repeats Stage 1 (transcription + diarization) which takes minutes
- **Impact**: Slow iteration when testing speaker identification improvements
- **Solution**: Check for existing `_stage1_transcript.json` files before running

### 2. Speaker Identification Quality
- **Problem**: Identifying 2-3 people in 1-on-1 meetings (false positives)
- **Root Cause**: 
  - Prompt may not emphasize 1-on-1 context strongly enough
  - Not validating number of speakers matches expected count
  - May be picking up names mentioned in conversation vs actual speakers
- **Solution**: 
  - Strengthen prompt for 1-on-1 meetings
  - Add validation: if filename suggests 1-on-1, ensure only 2 speakers
  - Better filtering of mentioned names vs actual speakers

### 3. Main CLI Doesn't Use Pipeline Stages
- **Problem**: `cli.py::_process_single_file()` duplicates logic from `pipeline_stages.py`
- **Impact**: Two code paths, harder to maintain, no caching
- **Solution**: Refactor main CLI to use `pipeline_stages.py` functions

## Component Breakdown

### Smallest Executable Units

1. **Diarization** (`diarization.py::run_diarization()`)
   - Input: audio file path
   - Output: List[SpeakerSegment]
   - Can run independently

2. **Transcription** (`transcriber.py::transcribe_with_whisper_async()`)
   - Input: audio file path
   - Output: TranscriptionResult
   - Can run independently

3. **Speaker Mapping** (`transcriber.py::find_speaker_for_segment()`)
   - Input: TranscriptionResult + List[SpeakerSegment]
   - Output: TranscriptionResult with speaker labels
   - Can run independently

4. **Context Extraction** (`context_extractor.py::extract_full_context()`)
   - Input: file path
   - Output: context string
   - Can run independently

5. **AI Speaker Identification** (`speaker_identifier.py::identify_speakers()`)
   - Input: transcript text, context, filename
   - Output: SpeakerIdentificationResult
   - Can run independently

6. **Export** (`exporter.py::export_*()`)
   - Input: segments, output_dir, base_name
   - Output: file paths
   - Can run independently

## File Dependencies

```
cli.py
├── audio_processor.py (validation)
├── transcriber.py (Stage 1)
│   ├── diarization.py (diarization)
│   └── exporter.py (TranscriptSegment definition)
├── speaker_identifier.py (Stage 2)
│   ├── context_extractor.py (context extraction)
│   └── ai_logger.py (logging)
├── exporter.py (Stage 3)
└── summary_report.py (metrics)

pipeline_stages.py
├── transcriber.py (Stage 1)
├── speaker_identifier.py (Stage 2)
├── context_extractor.py (context)
└── exporter.py (Stage 3)
```

## Data Flow

```
Audio File
    │
    ├─→ [Stage 1] Transcription + Diarization
    │       │
    │       ├─→ Diarization (pyannote)
    │       │   └─→ SpeakerSegment[] (SPEAKER_00, SPEAKER_01, ...)
    │       │
    │       ├─→ Transcription (Whisper)
    │       │   └─→ TranscriptSegment[] (text, timestamps)
    │       │
    │       └─→ Mapping
    │           └─→ TranscriptSegment[] (with speaker labels)
    │
    ├─→ [Cache Check] _stage1_transcript.json
    │       │
    │       ├─→ EXISTS: Load from cache
    │       └─→ NOT EXISTS: Run Stage 1, save cache
    │
    ├─→ [Stage 2] AI Speaker Identification
    │       │
    │       ├─→ Context Extraction
    │       │   └─→ Extract names from filename
    │       │
    │       ├─→ Format Transcript
    │       │   └─→ Timeline-aware format
    │       │
    │       ├─→ Build Prompt
    │       │   ├─→ Check filename context
    │       │   ├─→ Truncate or use full transcript
    │       │   └─→ Optimize for quality
    │       │
    │       └─→ AI Call
    │           └─→ SpeakerIdentificationResult
    │
    ├─→ [Cache Check] _stage2_speaker_mappings.json
    │       │
    │       ├─→ EXISTS: Load from cache
    │       └─→ NOT EXISTS: Run Stage 2, save cache
    │
    └─→ [Stage 3] Export
            │
            ├─→ Apply Mappings
            │   └─→ Replace SPEAKER_XX with names
            │
            └─→ Export Files
                ├─→ filename.txt
                ├─→ filename_speakers.txt
                ├─→ filename.json
                ├─→ filename.srt
                └─→ filename.docx
```

## Optimization Priorities

1. **Named Label Identification** (HIGHEST PRIORITY)
   - Improve prompt quality
   - Add validation for 1-on-1 meetings
   - Better filtering of mentioned names vs speakers

2. **Timestamp Identification** (SECOND PRIORITY)
   - Already good, but ensure precision maintained
   - Verify timeline alignment

3. **Transcript Quality** (THIRD PRIORITY)
   - Already very good
   - Minor improvements possible

4. **Caching** (EFFICIENCY)
   - Implement stage-level caching
   - Use file hash for cache keys
   - Cache directory management

