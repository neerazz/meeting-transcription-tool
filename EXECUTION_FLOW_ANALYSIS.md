# Execution Flow Analysis & Optimization Plan

## Current Execution Flow

### High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ CLI Command: transcribe --input "file.m4a"                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ cli.py: _process_single_file()                                   │
│ - Validates audio file                                           │
│ - Extracts context from filename                                 │
│ - Calls pipeline_stages functions                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: Transcription & Diarization                             │
│ pipeline_stages.py: stage1_transcribe_and_diarize()             │
│   │                                                               │
│   ├─► cache_manager.py: is_stage1_cached()                       │
│   │   └─► Check if cached file exists                            │
│   │                                                               │
│   ├─► transcriber.py: run_transcription_pipeline()                │
│   │   │                                                           │
│   │   ├─► diarization.py: run_diarization()                      │
│   │   │   └─► pyannote.audio Pipeline                             │
│   │   │       └─► Returns: List[SpeakerSegment]                  │
│   │   │                                                           │
│   │   ├─► transcriber.py: transcribe_with_whisper_async()        │
│   │   │   └─► OpenAI Whisper API                                 │
│   │   │       └─► Returns: TranscriptionResult                  │
│   │   │                                                           │
│   │   └─► transcriber.py: find_speaker_for_segment()              │
│   │       └─► Maps diarization to transcription segments        │
│   │                                                               │
│   └─► Saves: <basename>_stage1_transcript.json                   │
│       └─► IntermediateTranscript format                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: Speaker Identification                                   │
│ pipeline_stages.py: stage2_identify_speakers()                   │
│   │                                                               │
│   ├─► cache_manager.py: is_stage2_cached()                       │
│   │   └─► Check if cached mappings exist                         │
│   │                                                               │
│   ├─► Loads: <basename>_stage1_transcript.json                   │
│   │                                                               │
│   ├─► speaker_identifier.py: format_segments_for_prompt()        │
│   │   └─► Converts segments to timeline format                    │
│   │                                                               │
│   ├─► context_extractor.py: extract_full_context()                │
│   │   └─► Extracts names/context from filename                   │
│   │                                                               │
│   ├─► speaker_identifier.py: identify_speakers()                  │
│   │   │                                                           │
│   │   ├─► _build_optimized_prompt()                              │
│   │   │   ├─► Checks filename context                            │
│   │   │   ├─► Truncates or uses full transcript                  │
│   │   │   └─► Builds prompt with instructions                    │
│   │   │                                                           │
│   │   ├─► _maybe_upload_audio()                                  │
│   │   │   └─► Uploads audio to OpenAI                            │
│   │   │                                                           │
│   │   ├─► ai_logger.py: log_request()                           │
│   │   │   └─► Logs full request to ./ai_logs/                   │
│   │   │                                                           │
│   │   ├─► OpenAI API Call                                        │
│   │   │   └─► gpt-5-mini → o1-mini (reasoning)                   │
│   │   │                                                           │
│   │   ├─► ai_logger.py: log_response()                           │
│   │   │   └─► Logs response with cost                            │
│   │   │                                                           │
│   │   └─► Returns: SpeakerIdentificationResult                   │
│   │                                                               │
│   └─► Saves: <basename>_stage2_speaker_mappings.json             │
│       └─► Includes mappings + AI metadata                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: Export Files                                            │
│ pipeline_stages.py: stage3_apply_speaker_names()                 │
│   │                                                               │
│   ├─► Loads: <basename>_stage1_transcript.json                   │
│   ├─► Loads: <basename>_stage2_speaker_mappings.json (optional) │
│   │                                                               │
│   ├─► exporter.py: export_txt()                                  │
│   ├─► exporter.py: export_txt_with_speakers()                    │
│   ├─► exporter.py: export_json()                                 │
│   ├─► exporter.py: export_srt()                                  │
│   └─► exporter.py: export_docx()                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### Smallest Independent Components

1. **Audio Validation** (`audio_processor.py: validate_audio_file()`)
   - Input: file path
   - Output: (is_valid, reason)
   - Independent: ✅

2. **Diarization** (`diarization.py: run_diarization()`)
   - Input: audio_path, hf_token
   - Output: List[SpeakerSegment]
   - Independent: ✅
   - Cacheable: ✅ (Stage 1)

3. **Transcription** (`transcriber.py: transcribe_with_whisper_async()`)
   - Input: audio_path, model, language, temperature
   - Output: TranscriptionResult
   - Independent: ✅
   - Cacheable: ✅ (Stage 1)

4. **Speaker Mapping** (`transcriber.py: find_speaker_for_segment()`)
   - Input: whisper_segment, diarization_segments
   - Output: speaker_label
   - Independent: ✅ (pure function)

5. **Context Extraction** (`context_extractor.py: extract_full_context()`)
   - Input: file_path
   - Output: context_string
   - Independent: ✅

6. **Filename Parsing** (`context_extractor.py: extract_context_from_filename()`)
   - Input: filename
   - Output: (context, names)
   - Independent: ✅

7. **Prompt Building** (`speaker_identifier.py: _build_optimized_prompt()`)
   - Input: transcript_text, num_speakers, participant_names, context, filename
   - Output: prompt_string
   - Independent: ✅

8. **Speaker Identification** (`speaker_identifier.py: identify_speakers()`)
   - Input: transcript_text, num_speakers, context, filename, model
   - Output: SpeakerIdentificationResult
   - Independent: ✅
   - Cacheable: ✅ (Stage 2)

9. **Mapping Application** (`speaker_identifier.py: apply_speaker_mappings()`)
   - Input: segments, mappings
   - Output: updated_segments
   - Independent: ✅ (pure function)

10. **Export Functions** (`exporter.py: export_*()`)
    - Input: segments, output_dir, base_name
    - Output: file_path
    - Independent: ✅

## Quality Issues Identified

### Issue 1: 1-on-1 Meetings Showing 2-3 People
**Root Cause Analysis:**
- AI is counting names MENTIONED in conversation as speakers
- Example: "Thanks, Sarah" → AI thinks Sarah is a speaker
- Not validating that mentioned names actually speak

**Current Prompt Issues:**
- Doesn't strongly enforce speaker count validation
- Doesn't distinguish between "speaker" vs "mentioned name"
- 1-on-1 detection exists but validation is weak

### Issue 2: Timestamp Accuracy
**Current State:**
- Timestamps are preserved from Whisper
- Diarization mapping preserves timing
- ✅ This is working well

### Issue 3: Named Label Quality
**Issues:**
- Too many "Unknown" labels
- Inconsistent naming (sometimes "Manager", sometimes "Unknown")
- Not using filename names effectively
- Not validating against actual speaker count

## Optimization Plan

### Phase 1: Enhanced Speaker Identification Quality

#### Task 1.1: Multi-Step Validation Process
**Goal**: Ensure only actual speakers are mapped, not mentioned names

**Implementation**:
1. **Pre-Analysis Step**: Count unique speaker labels from diarization
2. **Validation Step**: Enforce strict speaker count (especially for 1-on-1)
3. **Filtering Step**: Remove mappings for names that don't actually speak
4. **Refinement Step**: If quality is low, trigger refinement with full transcript

**New Components**:
- `speaker_validator.py`: Validates speaker count and mappings
- `speaker_analyzer.py`: Pre-analyzes transcript for speaker patterns
- Enhanced `_build_optimized_prompt()` with stronger validation

#### Task 1.2: Improved 1-on-1 Detection & Enforcement
**Goal**: Strictly enforce 2-speaker limit for 1-on-1 meetings

**Implementation**:
- Detect 1-on-1 from filename AND context
- Add explicit validation in prompt
- Post-process to remove any extra mappings
- Add validation step after AI response

#### Task 1.3: Multi-Pass Speaker Identification
**Goal**: Use multiple passes for better quality

**Implementation**:
1. **Pass 1**: Quick identification using filename + truncated transcript
2. **Pass 2**: If quality is low (Unknown labels), use full transcript
3. **Pass 3**: Validation and refinement if needed

### Phase 2: Component Isolation & Caching

#### Task 2.1: Enhanced Caching
**Goal**: Cache all stages properly

**Current State**: ✅ Caching exists but needs verification
**Action**: Verify caching works correctly, add cache invalidation

#### Task 2.2: Stage Independence
**Goal**: Each stage can run independently

**Current State**: ✅ Already modular
**Action**: Ensure stages can be run individually without dependencies

### Phase 3: Quality Improvements

#### Task 3.1: Better Filename Analysis
**Goal**: Extract names more accurately from filenames

**Implementation**:
- Improve regex patterns
- Handle more filename formats
- Better name extraction (e.g., "Jason 1on1" → extract "Jason")

#### Task 3.2: Transcript Analysis
**Goal**: Pre-analyze transcript to identify actual speakers vs mentioned names

**Implementation**:
- Scan transcript for self-introductions
- Identify who actually speaks vs who is mentioned
- Pass this analysis to AI

#### Task 3.3: Post-Processing Validation
**Goal**: Validate AI response before accepting it

**Implementation**:
- Check speaker count matches diarization
- Validate no "Unknown" labels if filename has names
- Trigger refinement if quality is low

## Detailed Implementation Plan

### Step 1: Create Execution Flow Diagram
- Document complete flow with file/function names
- Identify all inputs/outputs
- Map data transformations

### Step 2: Create Quality Analysis Module
- `speaker_quality_analyzer.py`: Analyzes transcript quality
- Pre-identifies speaker patterns
- Validates against expected speaker count

### Step 3: Enhance Speaker Identification
- Multi-pass approach
- Stronger validation
- Better 1-on-1 handling

### Step 4: Add Post-Processing
- Validate AI responses
- Refine if needed
- Ensure quality standards

### Step 5: Test & Verify
- Run on sample file
- Verify quality improvements
- Check caching works

## Priority Order

1. **Named Label Quality** (Highest Priority)
   - Fix 1-on-1 meeting issue
   - Better validation
   - Multi-pass approach

2. **Timestamp Accuracy** (Already Good)
   - Verify preservation
   - No changes needed

3. **Transcript Quality** (Already Good)
   - No changes needed

## Next Steps

1. Create detailed flow diagram
2. Implement quality analyzer
3. Enhance speaker identification
4. Add validation steps
5. Test end-to-end
