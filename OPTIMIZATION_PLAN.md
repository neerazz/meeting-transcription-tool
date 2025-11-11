# Comprehensive Optimization Plan

## Executive Summary

**Goal**: Improve named label identification quality, especially for 1-on-1 meetings where 2-3 people are incorrectly identified.

**Priority Order**:
1. Named Label Quality (HIGHEST) - Fix 1-on-1 issue, better validation
2. Timestamp Accuracy - Already good, verify preservation
3. Transcript Quality - Already good, no changes needed

## Current Flow Analysis

### Complete Execution Flow

```
User Command
    │
    ▼
cli.py: transcribe()
    │
    ├─► _process_single_file()
    │   │
    │   ├─► validate_audio_file() [audio_processor.py]
    │   │
    │   ├─► extract_full_context() [context_extractor.py]
    │   │
    │   └─► pipeline_stages.py functions
    │       │
    │       ├─► STAGE 1: stage1_transcribe_and_diarize()
    │       │   │
    │       │   ├─► is_stage1_cached() [cache_manager.py]
    │       │   │   └─► Returns cached file if exists
    │       │   │
    │       │   ├─► run_transcription_pipeline() [transcriber.py]
    │       │   │   │
    │       │   │   ├─► run_diarization() [diarization.py]
    │       │   │   │   └─► pyannote.audio → List[SpeakerSegment]
    │       │   │   │
    │       │   │   ├─► transcribe_with_whisper_async() [transcriber.py]
    │       │   │   │   └─► OpenAI Whisper → TranscriptionResult
    │       │   │   │
    │       │   │   └─► find_speaker_for_segment() [transcriber.py]
    │       │   │       └─► Maps diarization to transcription
    │       │   │
    │       │   └─► Saves: <basename>_stage1_transcript.json
    │       │
    │       ├─► STAGE 2: stage2_identify_speakers()
    │       │   │
    │       │   ├─► is_stage2_cached() [cache_manager.py]
    │       │   │   └─► Returns cached mappings if exist
    │       │   │
    │       │   ├─► format_segments_for_prompt() [speaker_identifier.py]
    │       │   │   └─► Converts to timeline format
    │       │   │
    │       │   ├─► extract_full_context() [context_extractor.py]
    │       │   │   └─► Extracts names/context
    │       │   │
    │       │   ├─► identify_speakers() [speaker_identifier.py]
    │       │   │   │
    │       │   │   ├─► _build_optimized_prompt()
    │       │   │   │   └─► Builds prompt with instructions
    │       │   │   │
    │       │   │   ├─► _maybe_upload_audio()
    │       │   │   │   └─► Uploads audio file
    │       │   │   │
    │       │   │   ├─► OpenAI API Call
    │       │   │   │   └─► Returns JSON with mappings
    │       │   │   │
    │       │   │   └─► Returns: SpeakerIdentificationResult
    │       │   │
    │       │   └─► Saves: <basename>_stage2_speaker_mappings.json
    │       │
    │       └─► STAGE 3: stage3_apply_speaker_names()
    │           │
    │           ├─► Loads stage1 and stage2 files
    │           │
    │           └─► Exports: txt, json, srt, docx
    │
    └─► Returns: ProcessingMetrics
```

## Identified Issues

### Issue 1: 1-on-1 Meetings Showing 2-3 People ❌
**Problem**: AI counts names MENTIONED in conversation as speakers
**Example**: "Thanks, Sarah" → AI thinks Sarah is a speaker
**Root Cause**: 
- No pre-validation of actual speaker count
- Weak enforcement in prompt
- No post-processing validation

### Issue 2: Named Label Quality ❌
**Problems**:
- Too many "Unknown" labels
- Inconsistent naming
- Not using filename effectively
- Not validating against diarization speaker count

### Issue 3: Caching Not Fully Utilized ⚠️
**Status**: Caching exists but may not be working optimally
**Action**: Verify and enhance

## Solution Architecture

### New Components to Create

1. **speaker_quality_analyzer.py**
   - Pre-analyzes transcript
   - Identifies actual speakers vs mentioned names
   - Validates speaker count
   - Provides quality metrics

2. **speaker_validator.py**
   - Post-processes AI responses
   - Validates against diarization
   - Enforces 1-on-1 rules
   - Triggers refinement if needed

3. **Enhanced speaker_identifier.py**
   - Multi-pass identification
   - Better validation
   - Quality-aware processing

### Enhanced Components

1. **context_extractor.py**
   - Better name extraction
   - Improved 1-on-1 detection
   - More accurate parsing

2. **speaker_identifier.py**
   - Stronger prompt validation
   - Multi-pass approach
   - Post-processing validation

## Implementation Tasks

### Task 1: Create Speaker Quality Analyzer
**File**: `src/meeting_transcription_tool/speaker_quality_analyzer.py`

**Functions**:
- `analyze_transcript_speakers()`: Pre-analyzes who actually speaks
- `identify_mentioned_names()`: Finds names mentioned but not speaking
- `validate_speaker_count()`: Validates against diarization
- `detect_meeting_type()`: Detects 1-on-1, interview, etc.

### Task 2: Create Speaker Validator
**File**: `src/meeting_transcription_tool/speaker_validator.py`

**Functions**:
- `validate_mappings()`: Validates AI response
- `enforce_one_on_one()`: Enforces 2-speaker rule
- `filter_mentioned_names()`: Removes non-speaker mappings
- `trigger_refinement()`: Decides if refinement needed

### Task 3: Enhance Speaker Identification
**File**: `src/meeting_transcription_tool/speaker_identifier.py`

**Changes**:
- Add multi-pass identification
- Integrate quality analyzer
- Add post-validation
- Improve 1-on-1 handling

### Task 4: Improve Context Extraction
**File**: `src/meeting_transcription_tool/context_extractor.py`

**Changes**:
- Better name extraction patterns
- Improved 1-on-1 detection
- More filename format support

### Task 5: Verify Caching
**File**: `src/meeting_transcription_tool/cache_manager.py`

**Changes**:
- Verify cache invalidation
- Add cache status display
- Improve cache key generation

## Implementation Order

1. ✅ Create execution flow diagram (DONE)
2. ⏳ Create speaker_quality_analyzer.py
3. ⏳ Create speaker_validator.py
4. ⏳ Enhance speaker_identifier.py with multi-pass
5. ⏳ Improve context_extractor.py
6. ⏳ Verify caching works
7. ⏳ Test on sample file
8. ⏳ Update documentation

## Quality Metrics

### Success Criteria
- 1-on-1 meetings: Exactly 2 speakers identified
- Named labels: < 10% "Unknown" labels
- Filename names: > 80% match rate
- Timestamp accuracy: 100% preservation

## Testing Plan

1. Test on 1-on-1 meeting file
2. Verify exactly 2 speakers
3. Check no "Unknown" labels if filename has names
4. Verify timestamps preserved
5. Check caching works
