"""
Post-processing validator for speaker identification results.

Validates AI responses, enforces rules (especially 1-on-1), and triggers refinement if needed.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of speaker mapping validation."""
    is_valid: bool
    issues: List[str]
    needs_refinement: bool
    corrected_mappings: Optional[Dict[str, str]] = None
    confidence: str = "high"  # high, medium, low


def validate_mappings(
    mappings: Dict[str, str],
    diarization_speaker_count: int,
    meeting_type: Optional[str],
    filename: Optional[str] = None,
    analysis: Optional[object] = None,  # SpeakerAnalysis
) -> ValidationResult:
    """
    Validate speaker mappings against diarization and meeting type.
    
    Args:
        mappings: AI-generated mappings {generic_label: actual_name}
        diarization_speaker_count: Number of unique speakers from diarization
        meeting_type: Detected meeting type ("1-on-1", "interview", etc.)
        filename: Audio filename for context
        analysis: Pre-analysis results (optional)
    
    Returns:
        ValidationResult with validation status and issues
    """
    issues = []
    needs_refinement = False
    corrected_mappings = mappings.copy()
    
    # Check 1: Speaker count validation
    mapped_count = len(mappings)
    
    if meeting_type == "1-on-1":
        if mapped_count != 2:
            issues.append(f"1-on-1 meeting: Expected 2 speakers, but {mapped_count} mapped")
            needs_refinement = True
            
            # Auto-correct: Keep only first 2 mappings
            if mapped_count > 2:
                keys = list(mappings.keys())[:2]
                corrected_mappings = {k: mappings[k] for k in keys}
                issues.append(f"Auto-corrected: Kept only first 2 speakers")
    
    # Check 2: Diarization count validation
    if mapped_count != diarization_speaker_count:
        issues.append(
            f"Speaker count mismatch: Diarization detected {diarization_speaker_count}, "
            f"but {mapped_count} mapped"
        )
        if abs(mapped_count - diarization_speaker_count) > 1:
            needs_refinement = True
    
    # Check 3: "Unknown" labels validation
    unknown_count = sum(1 for v in mappings.values() if "unknown" in v.lower())
    if unknown_count > 0:
        if filename:
            # If filename has names, we shouldn't have Unknown
            from .context_extractor import extract_context_from_filename
            _, names = extract_context_from_filename(filename)
            if names:
                issues.append(f"Found {unknown_count} 'Unknown' labels despite filename having names")
                needs_refinement = True
    
    # Check 4: Check for mentioned names being mapped as speakers
    if analysis and hasattr(analysis, 'mentioned_names'):
        mentioned_only = getattr(analysis, 'mentioned_only', set())
        for label, name in mappings.items():
            if name in mentioned_only:
                issues.append(f"Warning: '{name}' is mapped as speaker but may only be mentioned")
                # Don't auto-correct, but flag for review
    
    # Determine confidence
    if len(issues) == 0:
        confidence = "high"
    elif len(issues) <= 2 and not needs_refinement:
        confidence = "medium"
    else:
        confidence = "low"
    
    return ValidationResult(
        is_valid=len(issues) == 0 or (len(issues) <= 1 and not needs_refinement),
        issues=issues,
        needs_refinement=needs_refinement,
        corrected_mappings=corrected_mappings if corrected_mappings != mappings else None,
        confidence=confidence,
    )


def enforce_one_on_one(
    mappings: Dict[str, str],
    diarization_labels: List[str],
) -> Dict[str, str]:
    """
    Enforce strict 2-speaker rule for 1-on-1 meetings.
    
    Args:
        mappings: Current mappings
        diarization_labels: All speaker labels from diarization
    
    Returns:
        Corrected mappings with exactly 2 speakers
    """
    unique_labels = set(diarization_labels)
    
    if len(unique_labels) <= 2:
        # Already correct, return as-is
        return mappings
    
    # More than 2 labels - need to consolidate
    # Strategy: Keep the 2 most frequent speakers
    from collections import Counter
    label_counts = Counter(diarization_labels)
    top_2_labels = [label for label, _ in label_counts.most_common(2)]
    
    # Create new mappings with only top 2
    corrected = {}
    for label in top_2_labels:
        if label in mappings:
            corrected[label] = mappings[label]
        else:
            # If not in mappings, use generic name
            corrected[label] = f"Speaker_{label.split('_')[-1]}"
    
    return corrected


def filter_mentioned_names(
    mappings: Dict[str, str],
    mentioned_only_names: Set[str],
) -> Dict[str, str]:
    """
    Remove mappings for names that are only mentioned, not actual speakers.
    
    Args:
        mappings: Current mappings
        mentioned_only_names: Names that are mentioned but don't speak
    
    Returns:
        Filtered mappings
    """
    filtered = {}
    for label, name in mappings.items():
        # Check if name is in mentioned-only set
        if name not in mentioned_only_names:
            filtered[label] = name
        else:
            # Replace with generic label
            filtered[label] = f"Speaker_{label.split('_')[-1]}"
    
    return filtered


def should_trigger_refinement(
    validation_result: ValidationResult,
    quality_score: float,
) -> bool:
    """
    Decide if refinement pass is needed.
    
    Args:
        validation_result: Validation results
        quality_score: Pre-analysis quality score (0.0-1.0)
    
    Returns:
        True if refinement should be triggered
    """
    # Trigger if validation failed
    if not validation_result.is_valid:
        return True
    
    # Trigger if quality score is low
    if quality_score < 0.6:
        return True
    
    # Trigger if needs_refinement flag is set
    if validation_result.needs_refinement:
        return True
    
    return False
