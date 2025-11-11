"""
Summary report generation for transcription processing.

Tracks metrics and generates detailed reports for each transcription.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import timedelta


@dataclass
class ProcessingMetrics:
    """Metrics tracked during transcription processing."""
    
    # File info
    input_file: str = ""
    file_size_bytes: int = 0
    audio_format: str = ""
    audio_duration_seconds: float = 0
    
    # Processing times
    start_time: float = 0
    diarization_time: float = 0
    transcription_time: float = 0
    speaker_identification_time: float = 0
    export_time: float = 0
    total_time: float = 0
    
    # Transcription results
    speakers_detected: int = 0
    speaker_segments: int = 0
    transcript_segments: int = 0
    total_words: int = 0
    
    # Speaker identification
    speaker_id_enabled: bool = False
    speaker_id_model: str = "N/A"
    speaker_mappings: Dict[str, str] = field(default_factory=dict)
    speaker_id_tokens_input: int = 0
    speaker_id_tokens_output: int = 0
    speaker_id_api_calls: int = 0
    
    # Models used
    transcription_model: str = ""
    
    # Costs
    whisper_audio_minutes: float = 0
    whisper_cost_usd: float = 0
    speaker_id_cost_usd: float = 0
    total_cost_usd: float = 0
    
    # Output files
    output_files: List[str] = field(default_factory=list)
    output_directory: str = ""
    
    # Errors/warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def calculate_whisper_cost(audio_minutes: float) -> float:
    """Calculate Whisper API cost ($0.006 per minute)."""
    return audio_minutes * 0.006


def calculate_gpt4o_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate GPT-4o cost ($2.50/1M input, $10/1M output)."""
    input_cost = (input_tokens / 1_000_000) * 2.50
    output_cost = (output_tokens / 1_000_000) * 10.00
    return input_cost + output_cost


def calculate_gemini_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate Gemini 2.0 Flash cost ($0.075/1M input, $0.30/1M output)."""
    input_cost = (input_tokens / 1_000_000) * 0.075
    output_cost = (output_tokens / 1_000_000) * 0.30
    return input_cost + output_cost


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: 1 token ≈ 4 chars)."""
    return len(text) // 4


def format_time(seconds: float) -> str:
    """Format seconds as human-readable time."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"


def format_bytes(bytes_val: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def generate_summary_report(metrics: ProcessingMetrics) -> str:
    """Generate a comprehensive summary report."""
    
    lines = []
    lines.append("=" * 80)
    lines.append("TRANSCRIPTION SUMMARY REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    # File Information
    lines.append("FILE INFORMATION")
    lines.append("-" * 80)
    lines.append(f"  Input File:     {metrics.input_file}")
    lines.append(f"  File Size:      {format_bytes(metrics.file_size_bytes)}")
    lines.append(f"  Audio Format:   {metrics.audio_format}")
    if metrics.audio_duration_seconds > 0:
        duration_mins = int(metrics.audio_duration_seconds // 60)
        duration_secs = int(metrics.audio_duration_seconds % 60)
        lines.append(f"  Duration:       {duration_mins}m {duration_secs}s")
    lines.append("")
    
    # Processing Details
    lines.append("PROCESSING DETAILS")
    lines.append("-" * 80)
    lines.append(f"  Transcription Model:  {metrics.transcription_model}")
    lines.append(f"  Speakers Detected:    {metrics.speakers_detected}")
    lines.append(f"  Speaker Segments:     {metrics.speaker_segments}")
    lines.append(f"  Total Words:          {metrics.total_words:,}")
    lines.append("")
    
    # Speaker Identification
    lines.append("SPEAKER IDENTIFICATION")
    lines.append("-" * 80)
    if metrics.speaker_id_enabled:
        lines.append(f"  Status:         Enabled")
        lines.append(f"  AI Model:       {metrics.speaker_id_model}")
        lines.append(f"  API Calls:      {metrics.speaker_id_api_calls}")
        lines.append(f"  Speakers Identified:")
        if metrics.speaker_mappings:
            for generic, actual in sorted(metrics.speaker_mappings.items()):
                lines.append(f"    • {generic} -> {actual}")
        else:
            lines.append(f"    (No mappings generated)")
    else:
        lines.append(f"  Status:         Disabled")
    lines.append("")
    
    # Processing Times
    lines.append("PROCESSING TIMES")
    lines.append("-" * 80)
    lines.append(f"  Diarization:           {format_time(metrics.diarization_time)}")
    lines.append(f"  Transcription:         {format_time(metrics.transcription_time)}")
    if metrics.speaker_identification_time > 0:
        lines.append(f"  Speaker ID (AI):       {format_time(metrics.speaker_identification_time)}")
    lines.append(f"  Export:                {format_time(metrics.export_time)}")
    lines.append(f"  Total:                 {format_time(metrics.total_time)}")
    lines.append("")
    
    # AI Usage & Costs
    lines.append("AI USAGE & COSTS")
    lines.append("-" * 80)
    
    # Whisper
    lines.append(f"  Whisper Transcription:")
    lines.append(f"    Audio Minutes:       {metrics.whisper_audio_minutes:.2f}")
    lines.append(f"    Cost:                ${metrics.whisper_cost_usd:.4f}")
    
    # Speaker ID
    if metrics.speaker_id_enabled and metrics.speaker_id_api_calls > 0:
        lines.append(f"  Speaker Identification ({metrics.speaker_id_model}):")
        lines.append(f"    Input Tokens:        {metrics.speaker_id_tokens_input:,}")
        lines.append(f"    Output Tokens:       {metrics.speaker_id_tokens_output:,}")
        lines.append(f"    Cost:                ${metrics.speaker_id_cost_usd:.4f}")
    
    lines.append(f"  TOTAL COST:            ${metrics.total_cost_usd:.4f}")
    lines.append("")
    
    # Output Files
    lines.append("OUTPUT FILES")
    lines.append("-" * 80)
    lines.append(f"  Directory:      {metrics.output_directory}")
    lines.append(f"  Files Created:")
    for output_file in metrics.output_files:
        lines.append(f"    • {output_file}")
    lines.append("")
    
    # Warnings/Errors
    if metrics.warnings or metrics.errors:
        lines.append("WARNINGS & ERRORS")
        lines.append("-" * 80)
        if metrics.warnings:
            lines.append("  Warnings:")
            for warning in metrics.warnings:
                lines.append(f"    ⚠ {warning}")
        if metrics.errors:
            lines.append("  Errors:")
            for error in metrics.errors:
                lines.append(f"    ✗ {error}")
        lines.append("")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)


def save_summary_report(metrics: ProcessingMetrics, output_path: str) -> None:
    """Save summary report to file."""
    report = generate_summary_report(metrics)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)


def generate_batch_summary_report(all_metrics: List[ProcessingMetrics]) -> str:
    """Generate a consolidated summary report for batch processing."""
    
    lines = []
    lines.append("=" * 80)
    lines.append("BATCH TRANSCRIPTION SUMMARY REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    # Overall statistics
    total_files = len(all_metrics)
    total_duration = sum(m.audio_duration_seconds for m in all_metrics if m.audio_duration_seconds > 0)
    total_processing_time = sum(m.total_time for m in all_metrics)
    total_cost = sum(m.total_cost_usd for m in all_metrics)
    total_words = sum(m.total_words for m in all_metrics)
    successful = len([m for m in all_metrics if not m.errors])
    failed = total_files - successful
    
    lines.append("BATCH OVERVIEW")
    lines.append("-" * 80)
    lines.append(f"  Total Files:           {total_files}")
    lines.append(f"  Successful:            {successful}")
    if failed > 0:
        lines.append(f"  Failed:                {failed}")
    lines.append(f"  Total Audio Duration:  {format_time(total_duration)}")
    lines.append(f"  Total Processing Time: {format_time(total_processing_time)}")
    lines.append(f"  Total Words:           {total_words:,}")
    lines.append(f"  Total Cost:            ${total_cost:.4f}")
    lines.append("")
    
    # Per-file details
    lines.append("FILE DETAILS")
    lines.append("-" * 80)
    for i, metrics in enumerate(all_metrics, 1):
        status = "[SUCCESS]" if not metrics.errors else "[FAILED]"
        lines.append(f"\n{i}. {status} {metrics.input_file}")
        lines.append(f"   Duration: {format_time(metrics.audio_duration_seconds)}")
        lines.append(f"   Processing Time: {format_time(metrics.total_time)}")
        lines.append(f"   Speakers: {metrics.speakers_detected}")
        lines.append(f"   Words: {metrics.total_words:,}")
        lines.append(f"   Cost: ${metrics.total_cost_usd:.4f}")
        
        if metrics.speaker_id_enabled and metrics.speaker_mappings:
            lines.append(f"   Speaker Identification:")
            for generic, actual in metrics.speaker_mappings.items():
                lines.append(f"     {generic} -> {actual}")
        
        if metrics.errors:
            lines.append(f"   Errors:")
            for error in metrics.errors:
                lines.append(f"     - {error}")
        
        if metrics.warnings:
            lines.append(f"   Warnings:")
            for warning in metrics.warnings:
                lines.append(f"     - {warning}")
    
    lines.append("")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def save_batch_summary_report(all_metrics: List[ProcessingMetrics], output_dir: str) -> str:
    """Save batch summary report with timestamp filename."""
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"batch_summary_{timestamp}.txt"
    output_path = os.path.join(output_dir, filename)
    
    report = generate_batch_summary_report(all_metrics)
    
    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return output_path

