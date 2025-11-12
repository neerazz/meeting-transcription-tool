"""
Speaker quality analyzer.

Pre-analyzes transcripts to identify actual speakers vs mentioned names,
validates speaker counts, and provides quality metrics for better AI identification.
"""
from __future__ import annotations

import re
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import Counter


@dataclass
class SpeakerAnalysis:
    """Analysis of speakers in a transcript."""
    unique_speaker_labels: Set[str]
    speaker_count: int
    mentioned_names: Set[str]
    self_introductions: Dict[str, str]  # speaker_label -> name
    meeting_type: Optional[str]  # "1-on-1", "interview", etc.
    quality_score: float  # 0.0 to 1.0
    issues: List[str]


def analyze_transcript_speakers(
    segments: List[Dict],
    filename: Optional[str] = None,
    context: Optional[str] = None,
) -> SpeakerAnalysis:
    """
    Pre-analyze transcript to identify actual speakers and mentioned names.
    
    Args:
        segments: List of transcript segments with 'speaker' and 'text' keys
        filename: Audio filename for context
        context: Meeting context string
    
    Returns:
        SpeakerAnalysis with quality metrics
    """
    # Extract unique speaker labels from diarization
    unique_speakers = set(seg['speaker'] for seg in segments if seg.get('speaker'))
    speaker_count = len(unique_speakers)
    
    # Find mentioned names (people referenced but may not be speakers)
    mentioned_names = _extract_mentioned_names(segments)
    
    # Find self-introductions
    self_intros = _find_self_introductions(segments)
    
    # Detect meeting type
    meeting_type = _detect_meeting_type(filename, context, speaker_count)
    
    # Calculate quality score
    quality_score, issues = _calculate_quality_score(
        speaker_count=speaker_count,
        mentioned_names=mentioned_names,
        self_intros=self_intros,
        meeting_type=meeting_type,
        filename=filename,
    )
    
    return SpeakerAnalysis(
        unique_speaker_labels=unique_speakers,
        speaker_count=speaker_count,
        mentioned_names=mentioned_names,
        self_introductions=self_intros,
        meeting_type=meeting_type,
        quality_score=quality_score,
        issues=issues,
    )


def _extract_mentioned_names(segments: List[Dict]) -> Set[str]:
    """Extract names mentioned in the transcript (may not be speakers)."""
    mentioned = set()
    
    # Patterns for name mentions
    patterns = [
        r"(?:thanks|thank you|hi|hello|hey),?\s+([A-Z][a-z]+)",
        r"(?:this is|i'm|i am|my name is)\s+([A-Z][a-z]+)",
        r"([A-Z][a-z]+)\s+(?:said|mentioned|told|asked)",
        r"([A-Z][a-z]+)'s\s+(?:meeting|call|interview)",
    ]
    
    for seg in segments:
        text = seg.get('text', '').strip()
        if not text:
            continue
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Filter out common words
                if match.lower() not in ['the', 'this', 'that', 'there', 'here']:
                    mentioned.add(match)
    
    return mentioned


def _find_self_introductions(segments: List[Dict]) -> Dict[str, str]:
    """
    Find self-introductions in transcript.
    
    Returns:
        Dict mapping speaker_label -> name
    """
    intros = {}
    
    intro_patterns = [
        r"(?:hi|hello|hey),?\s*(?:this is|i'm|i am|my name is)\s+([A-Z][a-z]+)",
        r"(?:this is|i'm|i am)\s+([A-Z][a-z]+)",
        r"my name is\s+([A-Z][a-z]+)",
    ]
    
    for seg in segments:
        speaker = seg.get('speaker', '')
        text = seg.get('text', '').strip().lower()
        
        if not text or not speaker:
            continue
        
        for pattern in intro_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1)
                # Only add if this speaker hasn't been identified yet
                if speaker not in intros:
                    intros[speaker] = name
                break
    
    return intros


def _detect_meeting_type(
    filename: Optional[str],
    context: Optional[str],
    speaker_count: int,
) -> Optional[str]:
    """Detect meeting type from filename, context, and speaker count."""
    text_to_check = ""
    
    if filename:
        text_to_check += " " + filename.lower()
    if context:
        text_to_check += " " + context.lower()
    
    # 1-on-1 detection
    if any(term in text_to_check for term in ['1on1', '1-on-1', 'one-on-one', '1 on 1']):
        return "1-on-1"
    
    # Interview detection
    if 'interview' in text_to_check:
        return "interview"
    
    # Review detection
    if any(term in text_to_check for term in ['review', 'performance', 'quarterly']):
        return "review"
    
    # If speaker count is 2 and no other type detected, likely 1-on-1
    if speaker_count == 2 and not any(term in text_to_check for term in ['team', 'group', 'panel']):
        return "1-on-1"
    
    return None


def _calculate_quality_score(
    speaker_count: int,
    mentioned_names: Set[str],
    self_intros: Dict[str, str],
    meeting_type: Optional[str],
    filename: Optional[str],
) -> Tuple[float, List[str]]:
    """
    Calculate quality score and identify issues.
    
    Returns:
        Tuple of (quality_score, issues_list)
    """
    score = 1.0
    issues = []
    
    # Check 1-on-1 validation
    if meeting_type == "1-on-1":
        if speaker_count != 2:
            score -= 0.3
            issues.append(f"1-on-1 meeting but {speaker_count} speakers detected (expected 2)")
        elif speaker_count == 2:
            score += 0.1  # Bonus for correct count
    
    # Check if too many mentioned names (potential confusion)
    if len(mentioned_names) > speaker_count * 2:
        score -= 0.2
        issues.append(f"Many names mentioned ({len(mentioned_names)}) vs {speaker_count} speakers - may cause confusion")
    
    # Check if we have self-introductions
    if self_intros:
        score += 0.1  # Bonus for clear introductions
    
    # Check filename has names
    if filename:
        from .context_extractor import extract_context_from_filename
        _, names = extract_context_from_filename(filename)
        if names:
            score += 0.1  # Bonus for filename names
    
    # Normalize score
    score = max(0.0, min(1.0, score))
    
    return score, issues


def validate_speaker_count(
    detected_count: int,
    meeting_type: Optional[str],
    expected_count: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate speaker count against meeting type.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if meeting_type == "1-on-1":
        if detected_count != 2:
            return False, f"1-on-1 meeting requires exactly 2 speakers, but {detected_count} detected"
    
    if expected_count and detected_count != expected_count:
        return False, f"Expected {expected_count} speakers, but {detected_count} detected"
    
    return True, None


def identify_actual_speakers_vs_mentioned(
    segments: List[Dict],
    analysis: SpeakerAnalysis,
) -> Dict[str, Set[str]]:
    """
    Identify which names are actual speakers vs just mentioned.
    
    Returns:
        Dict with 'actual_speakers' and 'mentioned_only' sets
    """
    # Names that appear in self-introductions are likely actual speakers
    actual_speaker_names = set(analysis.self_introductions.values())
    
    # All mentioned names
    all_mentioned = analysis.mentioned_names.copy()
    
    # Remove actual speakers from mentioned-only
    mentioned_only = all_mentioned - actual_speaker_names
    
    return {
        'actual_speakers': actual_speaker_names,
        'mentioned_only': mentioned_only,
    }
