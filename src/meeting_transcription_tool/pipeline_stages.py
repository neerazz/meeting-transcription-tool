"""
Modular pipeline stages for meeting transcription.

Breaks down the full pipeline into discrete, testable stages with intermediate outputs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class IntermediateTranscript:
    """Intermediate transcript data structure."""
    audio_file: str
    segments: List[Dict]  # List of {start_ms, end_ms, speaker, text}
    metadata: Dict
    
    def save(self, output_path: str) -> None:
        """Save intermediate transcript to JSON file."""
        data = {
            "audio_file": self.audio_file,
            "segments": self.segments,
            "metadata": self.metadata
        }
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load(input_path: str) -> 'IntermediateTranscript':
        """Load intermediate transcript from JSON file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return IntermediateTranscript(
            audio_file=data["audio_file"],
            segments=data["segments"],
            metadata=data["metadata"]
        )


def stage1_transcribe_and_diarize(
    audio_path: str,
    output_dir: str,
    hf_token: Optional[str] = None,
    whisper_model: str = "whisper-1",
    api_key: Optional[str] = None,
    language: Optional[str] = None,
    temperature: float = 0.0,
    use_cache: bool = True,
) -> str:
    """
    Stage 1: Transcribe audio and perform speaker diarization.
    
    Creates: <basename>_stage1_transcript.json
    
    Args:
        use_cache: If True, check for existing cache file before running
    
    Returns: Path to intermediate file
    """
    import asyncio
    from .transcriber import run_transcription_pipeline
    from .cache_manager import is_stage1_cached
    
    base_name = Path(audio_path).stem
    output_file = os.path.join(output_dir, f"{base_name}_stage1_transcript.json")
    
    # Check cache first
    if use_cache:
        is_cached, cache_path = is_stage1_cached(
            audio_path=audio_path,
            output_dir=output_dir,
            whisper_model=whisper_model,
            language=language,
            temperature=temperature,
        )
        if is_cached and cache_path:
            print(f"[Stage 1] [CACHED] Using cached result: {os.path.basename(cache_path)}")
            return cache_path
    
    print(f"[Stage 1] Transcribing and diarizing: {audio_path}")
    
    # Run transcription pipeline
    result = asyncio.run(run_transcription_pipeline(
        audio_path=audio_path,
        hf_token=hf_token,
        model=whisper_model,
        api_key=api_key,
        language=language,
        temperature=temperature,
    ))
    
    # Convert to intermediate format
    segments = [
        {
            "start_ms": seg.start_ms,
            "end_ms": seg.end_ms,
            "speaker": seg.speaker,
            "text": seg.text
        }
        for seg in result.segments
    ]
    
    metadata = {
        "audio_file": os.path.abspath(audio_path),
        "model": whisper_model,
        "speakers_detected": len(set(seg.speaker for seg in result.segments)),
        "total_segments": len(result.segments),
    }
    
    # Save intermediate file
    intermediate = IntermediateTranscript(
        audio_file=audio_path,
        segments=segments,
        metadata=metadata
    )
    os.makedirs(output_dir, exist_ok=True)
    intermediate.save(output_file)
    
    print(f"[Stage 1] [COMPLETE] Saved: {output_file}")
    print(f"[Stage 1] Speakers: {metadata['speakers_detected']}, Segments: {metadata['total_segments']}")
    
    return output_file


def stage2_identify_speakers(
    intermediate_file: str,
    output_dir: str,
    speaker_context: Optional[str] = None,
    ai_model: str = "gpt-5-mini",
    api_key: Optional[str] = None,
    use_cache: bool = True,
) -> str:
    """
    Stage 2: Use AI to identify speakers from intermediate transcript.
    
    Input: <basename>_stage1_transcript.json
    Creates: <basename>_stage2_speaker_mappings.json
    
    Args:
        use_cache: If True, check for existing cache file before running
    
    Returns: Path to speaker mappings file
    """
    from .speaker_identifier import identify_speakers, format_segments_for_prompt
    from .context_extractor import extract_full_context
    from .cache_manager import is_stage2_cached
    
    # Load intermediate transcript
    intermediate = IntermediateTranscript.load(intermediate_file)
    base_name = Path(intermediate.audio_file).stem
    output_file = os.path.join(output_dir, f"{base_name}_stage2_speaker_mappings.json")
    
    # Check cache first
    if use_cache:
        is_cached, cache_path = is_stage2_cached(
            stage1_file=intermediate_file,
            audio_path=intermediate.audio_file,
            output_dir=output_dir,
            ai_model=ai_model,
            speaker_context=speaker_context,
        )
        if is_cached and cache_path:
            print(f"[Stage 2] [CACHED] Using cached result: {os.path.basename(cache_path)}")
            return cache_path
    
    print(f"[Stage 2] Identifying speakers with AI ({ai_model})...")
    
    # Pre-analyze transcript for quality
    from .speaker_quality_analyzer import analyze_transcript_speakers, identify_actual_speakers_vs_mentioned
    from .speaker_validator import validate_mappings, should_trigger_refinement
    
    analysis = analyze_transcript_speakers(
        segments=intermediate.segments,
        filename=intermediate.audio_file,
        context=speaker_context,
    )
    
    print(f"[Stage 2] Pre-analysis: {analysis.speaker_count} speakers detected, "
          f"meeting type: {analysis.meeting_type or 'unknown'}, "
          f"quality score: {analysis.quality_score:.2f}")
    if analysis.issues:
        for issue in analysis.issues:
            print(f"[Stage 2] ⚠️  {issue}")
    
    # Identify actual speakers vs mentioned names
    speaker_analysis = identify_actual_speakers_vs_mentioned(intermediate.segments, analysis)
    if speaker_analysis['mentioned_only']:
        print(f"[Stage 2] Names mentioned but not speaking: {', '.join(speaker_analysis['mentioned_only'])}")
    
    # Build transcript text
    transcript_text = format_segments_for_prompt(intermediate.segments)
    
    # Extract context if not provided
    if not speaker_context:
        speaker_context = extract_full_context(intermediate.audio_file)
        print(f"[Stage 2] Extracted context: {speaker_context}")
    
    # Identify speakers - pass segments for better analysis
    num_speakers = analysis.speaker_count
    result = identify_speakers(
        transcript_text=transcript_text,
        num_speakers=num_speakers,
        participant_names=list(speaker_analysis['actual_speakers']) if speaker_analysis['actual_speakers'] else None,
        participant_context=speaker_context,
        filename=intermediate.audio_file,
        api_key=api_key,
        model=ai_model,
        segments=intermediate.segments,  # Pass segments for analysis
        pre_analysis=analysis,  # Pass pre-analysis
    )
    mappings = result.mappings
    
    # Post-validate mappings
    validation = validate_mappings(
        mappings=mappings,
        diarization_speaker_count=num_speakers,
        meeting_type=analysis.meeting_type,
        filename=intermediate.audio_file,
        analysis=analysis,
    )
    
    if validation.issues:
        print(f"[Stage 2] Validation issues:")
        for issue in validation.issues:
            print(f"  ⚠️  {issue}")
    
    # Apply corrections if needed
    if validation.corrected_mappings:
        print(f"[Stage 2] Applied corrections to mappings")
        mappings = validation.corrected_mappings
    
    # Trigger refinement if needed
    if should_trigger_refinement(validation, analysis.quality_score):
        print(f"[Stage 2] Quality issues detected, triggering refinement pass...")
        # Refinement will be handled in identify_speakers if needed
    
    if result.request_metadata:
        print("[Stage 2] AI speaker-label request metadata:")
        print(json.dumps(result.request_metadata, indent=2))
    if result.response_metadata:
        print("[Stage 2] AI speaker-label response metadata:")
        print(json.dumps(result.response_metadata, indent=2))
    if result.audio_file_id:
        print(f"[Stage 2] Uploaded audio file id: {result.audio_file_id} "
              f"({result.audio_upload_bytes:,} bytes)")
    
    # Save mappings (use validated/corrected mappings)
    mapping_data = {
        "source_file": intermediate_file,
        "audio_file": intermediate.audio_file,
        "ai_model": ai_model,
        "speaker_context": speaker_context,
        "mappings": mappings,  # Already corrected by validation
        "pre_analysis": {
            "speaker_count": analysis.speaker_count,
            "meeting_type": analysis.meeting_type,
            "quality_score": analysis.quality_score,
            "issues": analysis.issues,
        } if analysis else None,
        "validation": {
            "is_valid": validation.is_valid,
            "confidence": validation.confidence,
            "issues": validation.issues,
        } if validation else None,
        "ai_request_metadata": result.request_metadata,
        "ai_response_metadata": result.response_metadata,
        "ai_audio_file_id": result.audio_file_id,
        "ai_audio_bytes_uploaded": result.audio_upload_bytes,
    }
    
    os.makedirs(output_dir, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f, ensure_ascii=False, indent=2)
    
    print(f"[Stage 2] [COMPLETE] Saved: {output_file}")
    print(f"[Stage 2] Speaker mappings:")
    for generic, actual in mappings.items():
        print(f"  {generic} -> {actual}")
    
    return output_file


def stage3_apply_speaker_names(
    intermediate_file: str,
    speaker_mapping_file: Optional[str],
    output_dir: str,
    formats: List[str] = None,
) -> List[str]:
    """
    Stage 3: Apply speaker name mappings and create final output files.
    
    Input: 
      - <basename>_stage1_transcript.json
      - <basename>_stage2_speaker_mappings.json (optional)
    Creates: 
      - <basename>.txt (generic labels)
      - <basename>_speakers.txt (AI-identified names, if mappings provided)
      - <basename>.json, .srt, etc. (based on formats)
    
    Returns: List of created file paths
    """
    from .exporter import (
        TranscriptSegment, export_txt, export_txt_with_speakers,
        export_json, export_srt, export_docx
    )
    
    if formats is None:
        formats = ["txt", "json", "srt"]
    
    # Load intermediate transcript
    intermediate = IntermediateTranscript.load(intermediate_file)
    base_name = Path(intermediate.audio_file).stem
    
    # Load speaker mappings (if provided)
    mappings = {}
    if speaker_mapping_file and os.path.exists(speaker_mapping_file):
        with open(speaker_mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        mappings = mapping_data.get('mappings', {})
    
    print(f"[Stage 3] Applying speaker names and creating output files...")
    
    # Convert to TranscriptSegment objects (generic labels)
    segments_generic = [
        TranscriptSegment(
            start_ms=seg['start_ms'],
            end_ms=seg['end_ms'],
            text=seg['text'],
            speaker=seg['speaker']
        )
        for seg in intermediate.segments
    ]
    
    # Convert to TranscriptSegment objects (with AI names)
    segments_named = [
        TranscriptSegment(
            start_ms=seg['start_ms'],
            end_ms=seg['end_ms'],
            text=seg['text'],
            speaker=mappings.get(seg['speaker'], seg['speaker'])
        )
        for seg in intermediate.segments
    ]
    
    written_files = []
    
    # Export with generic labels
    if "txt" in formats:
        file_path = export_txt(segments_generic, output_dir, base_name)
        written_files.append(file_path)
        print(f"[Stage 3] [CREATED] {os.path.basename(file_path)}")
    
    # Export with AI-identified speaker names
    if "txt" in formats and mappings:
        file_path = export_txt_with_speakers(segments_named, output_dir, base_name)
        written_files.append(file_path)
        print(f"[Stage 3] [CREATED] {os.path.basename(file_path)}")
    
    # Other formats (use named speakers)
    metadata = {
        "source_file": intermediate.audio_file,
        "model": intermediate.metadata.get("model", "whisper-1"),
        "speaker_identification": True,
        "speaker_mappings": mappings
    }
    
    if "json" in formats:
        file_path = export_json(segments_named, output_dir, base_name, metadata=metadata)
        written_files.append(file_path)
        print(f"[Stage 3] [CREATED] {os.path.basename(file_path)}")
    
    if "srt" in formats:
        file_path = export_srt(segments_named, output_dir, base_name)
        written_files.append(file_path)
        print(f"[Stage 3] [CREATED] {os.path.basename(file_path)}")
    
    if "docx" in formats:
        try:
            file_path = export_docx(segments_named, output_dir, base_name)
            written_files.append(file_path)
            print(f"[Stage 3] [CREATED] {os.path.basename(file_path)}")
        except Exception as e:
            print(f"[Stage 3] [WARNING] DOCX export skipped: {e}")
    
    print(f"[Stage 3] [COMPLETE] Created {len(written_files)} files")
    
    return written_files


def run_full_pipeline(
    audio_path: str,
    output_dir: str,
    identify_speakers: bool = True,
    **kwargs
) -> Dict[str, str]:
    """
    Run the complete pipeline with all stages.
    
    Returns: Dictionary with paths to all intermediate and final files
    """
    results = {}
    
    # Stage 1: Transcribe and Diarize
    stage1_file = stage1_transcribe_and_diarize(
        audio_path=audio_path,
        output_dir=output_dir,
        hf_token=kwargs.get('hf_token'),
        whisper_model=kwargs.get('model', 'whisper-1'),
        api_key=kwargs.get('api_key'),
        language=kwargs.get('language'),
        temperature=kwargs.get('temperature', 0.0),
    )
    results['stage1_transcript'] = stage1_file
    
    # Stage 2: Identify Speakers (if enabled)
    if identify_speakers:
        stage2_file = stage2_identify_speakers(
            intermediate_file=stage1_file,
            output_dir=output_dir,
            speaker_context=kwargs.get('speaker_context'),
            ai_model=kwargs.get('ai_model', 'gpt-5-mini'),
            api_key=kwargs.get('api_key'),
        )
        results['stage2_mappings'] = stage2_file
    else:
        stage2_file = None
    
    # Stage 3: Create final outputs
    final_files = stage3_apply_speaker_names(
        intermediate_file=stage1_file,
        speaker_mapping_file=stage2_file if stage2_file else None,
        output_dir=output_dir,
        formats=kwargs.get('formats', ['txt', 'json', 'srt']),
    )
    results['final_files'] = final_files
    
    return results

