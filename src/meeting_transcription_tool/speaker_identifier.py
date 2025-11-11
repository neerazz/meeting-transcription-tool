"""
AI-powered speaker identification module.

Uses GPT-4o with reasoning or Gemini 2.0 Flash to analyze transcripts 
and identify speakers by their actual names or descriptive roles.
"""
from __future__ import annotations

import os
from typing import List, Dict, Optional, Literal
import json
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class SpeakerMapping:
    """Mapping from generic speaker label to actual name."""
    generic_label: str  # e.g., "SPEAKER_00"
    actual_name: str    # e.g., "Ian" or "Interviewer"
    confidence: str     # e.g., "high", "medium", "low"
    reasoning: str      # Why the AI thinks this is correct


def identify_speakers(
    transcript_text: str,
    num_speakers: Optional[int] = None,
    participant_names: Optional[List[str]] = None,
    participant_context: Optional[str] = None,
    filename: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Literal["gpt-4o", "gemini-2.0-flash"] = "gpt-4o",
) -> Dict[str, str]:
    """
    Use AI to identify speakers in a transcript and map generic labels to actual names.
    
    Args:
        transcript_text: The full transcript with generic speaker labels
        num_speakers: Number of speakers in the conversation (optional)
        participant_names: List of known participant names (optional, rarely needed)
        participant_context: Additional context about the meeting/participants (optional)
        filename: Name of the audio file (optional, often contains participant names)
        api_key: OpenAI API key (optional, will use env var if not provided)
        model: AI model to use - "gpt-4o" (with reasoning) or "gemini-2.0-flash"
    
    Returns:
        Dictionary mapping generic labels to actual names/roles, e.g.:
        {"SPEAKER_00": "Ian", "SPEAKER_01": "Candidate"}
    """
    if model == "gpt-4o":
        return _identify_with_openai(
            transcript_text, num_speakers, participant_names, 
            participant_context, filename, api_key
        )
    elif model == "gemini-2.0-flash":
        return _identify_with_gemini(
            transcript_text, num_speakers, participant_names,
            participant_context, filename, api_key
        )
    else:
        raise ValueError(f"Unsupported model: {model}")


def _identify_with_openai(
    transcript_text: str,
    num_speakers: Optional[int],
    participant_names: Optional[List[str]],
    participant_context: Optional[str],
    filename: Optional[str],
    api_key: Optional[str],
) -> Dict[str, str]:
    """Identify speakers using GPT-4o with reasoning."""
    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
    
    # Build optimized prompt
    prompt = _build_optimized_prompt(
        transcript_text,
        num_speakers,
        participant_names,
        participant_context,
        filename
    )
    
    # System instruction optimized for speaker identification
    system_instruction = """You are an expert conversation analyst specializing in speaker identification.

Your task: Analyze meeting transcripts to identify who each speaker is by their actual name or descriptive role.

Key abilities:
1. **PRIORITIZE FILENAME** - Extract names from the audio filename first (most reliable source)
2. Detect names from self-introductions, mentions, or context
3. Infer roles from conversation dynamics (interviewer/candidate, manager/employee, host/guest)
4. Use speech patterns, topics discussed, and power dynamics
5. Provide clear, consistent naming throughout

Guidelines:
- **ALWAYS check the filename first** - it often contains participant names (e.g., "John Smith Meeting" -> look for "John" and "Smith")
- Match filename names to speakers in the transcript
- Use actual names when clearly mentioned or obvious from context
- Use descriptive roles when names aren't clear (Interviewer, Manager, Host, etc.)
- Be consistent - same person = same label throughout
- High confidence when names match filename or are explicitly mentioned
- Medium confidence when inferred from strong context clues
- Low confidence when purely speculative

Output valid JSON only."""

    # Call GPT-4o with reasoning
    response = client.chat.completions.create(
        model="gpt-4o",  # GPT-4o with reasoning capabilities
        messages=[
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,  # Low temperature for consistency
        response_format={"type": "json_object"},
        # Enable reasoning (if available in API)
    )
    
    # Parse response
    result = json.loads(response.choices[0].message.content)
    
    # Extract mappings
    mappings = {}
    for mapping in result.get("speaker_mappings", []):
        generic_label = mapping.get("generic_label", "")
        actual_name = mapping.get("actual_name", "")
        if generic_label and actual_name:
            mappings[generic_label] = actual_name
    
    return mappings


def _identify_with_gemini(
    transcript_text: str,
    num_speakers: Optional[int],
    participant_names: Optional[List[str]],
    participant_context: Optional[str],
    filename: Optional[str],
    api_key: Optional[str],
) -> Dict[str, str]:
    """Identify speakers using Gemini 2.0 Flash."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "Google Generative AI package not installed. "
            "Install with: pip install google-generativeai"
        )
    
    # Configure Gemini
    genai.configure(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    # Build prompt
    prompt = _build_optimized_prompt(
        transcript_text,
        num_speakers,
        participant_names,
        participant_context,
        filename
    )
    
    # System instruction for Gemini
    system_instruction = """You are an expert at analyzing conversations and identifying speakers.

Analyze the transcript and identify each speaker by:
1. **FILENAME FIRST** - Extract names from the audio filename (most reliable source)
2. Their actual name (if mentioned or obvious from transcript)
3. Their role (Interviewer, Manager, Host, etc.) if name isn't clear

**IMPORTANT**: Always check the filename for participant names first, then match them to speakers in the transcript.

Be consistent and confident. Output valid JSON only."""
    
    # Generate response
    full_prompt = f"{system_instruction}\n\n{prompt}"
    response = model.generate_content(
        full_prompt,
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        }
    )
    
    # Parse response
    result = json.loads(response.text)
    
    # Extract mappings
    mappings = {}
    for mapping in result.get("speaker_mappings", []):
        generic_label = mapping.get("generic_label", "")
        actual_name = mapping.get("actual_name", "")
        if generic_label and actual_name:
            mappings[generic_label] = actual_name
    
    return mappings


def _build_optimized_prompt(
    transcript_text: str,
    num_speakers: Optional[int],
    participant_names: Optional[List[str]],
    participant_context: Optional[str],
    filename: Optional[str] = None
) -> str:
    """Build optimized prompt for speaker identification."""
    
    # Intelligent truncation: keep beginning (introductions) and sample middle
    max_chars = 4000
    if len(transcript_text) > max_chars:
        # Keep first 2500 chars (usually has introductions)
        start_part = transcript_text[:2500]
        # Sample from middle to get conversation flow
        middle_start = len(transcript_text) // 2 - 750
        middle_part = transcript_text[middle_start:middle_start + 1500]
        transcript_sample = start_part + "\n\n[... middle section ...]\n\n" + middle_part
    else:
        transcript_sample = transcript_text
    
    # Build context section - FILENAME IS HIGH PRIORITY
    context_parts = []
    if filename:
        # Extract just the filename without extension for cleaner display
        from pathlib import Path
        filename_clean = Path(filename).stem
        context_parts.append(f"• FILENAME (IMPORTANT - often contains participant names): {filename_clean}")
    if num_speakers:
        context_parts.append(f"• Number of speakers: {num_speakers}")
    if participant_names:
        context_parts.append(f"• Known names: {', '.join(participant_names)}")
    if participant_context:
        context_parts.append(f"• Meeting context: {participant_context}")
    
    context_section = "\n".join(context_parts) if context_parts else "• No additional context provided"
    
    # Optimized prompt with clear structure - emphasize filename usage
    filename_instruction = ""
    if filename:
        filename_instruction = """
⚠️ CRITICAL: The FILENAME above often contains participant names!
- Extract names from the filename (e.g., "John Smith Interview" -> look for "John" and "Smith")
- Match these names to speakers in the transcript
- Filename names should be your PRIMARY source when available
- Only use generic roles if filename names don't match any speakers
"""
    
    prompt = f"""TASK: Identify each speaker in this transcript by their actual name or role.

TRANSCRIPT:
{transcript_sample}

CONTEXT:
{context_section}
{filename_instruction}

ANALYSIS STRATEGY (in priority order):
1. **FILENAME FIRST** (if provided):
   - Extract participant names from the filename
   - Match these names to speakers in the transcript
   - Filename is often the most reliable source of names
   - Example: "Ian Laiks 1on1" -> look for "Ian" and "Laiks" in transcript

2. Scan transcript for explicit names:
   - Self-introductions: "I'm X", "My name is X", "This is X"
   - References: "Thanks X", "Hi X", "X mentioned..."
   - Email signatures, titles mentioned

3. Infer from roles/dynamics:
   - Who asks questions? (Interviewer, Host, Manager)
   - Who answers? (Candidate, Guest, Employee)  
   - Who leads? (Chair, Facilitator, Senior)
   - Who reports? (Team member, Junior, Presenter)

4. Use speech patterns:
   - Formal vs casual language
   - Technical vs general topics
   - Decision-making authority
   - Relationship indicators

5. Naming priority:
   a) Filename names (if match transcript) -> "Ian", "Laiks"
   b) Actual name if clearly mentioned -> "Sarah"
   c) Role if no name but clear -> "Interviewer"
   d) Descriptive role if ambiguous -> "Manager"

REQUIREMENTS:
✓ Be decisive - choose best available label
✓ Be consistent - same person = same label
✓ Be specific - avoid generic labels when possible
✓ Provide reasoning - explain your identification

OUTPUT (JSON):
{{
  "speaker_mappings": [
    {{
      "generic_label": "SPEAKER_00",
      "actual_name": "Ian",
      "confidence": "high",
      "reasoning": "Self-introduces as 'Ian' at 00:00:05, leads meeting, asks most questions"
    }},
    {{
      "generic_label": "SPEAKER_01",
      "actual_name": "Candidate",
      "confidence": "medium",
      "reasoning": "Responds to questions, no name mentioned, interview context suggests candidate role"
    }}
  ],
  "analysis": "1-on-1 interview format. Ian is interviewer (asks questions, controls flow). Other speaker is candidate (answers, discusses experience).",
  "confidence_notes": "Ian's name explicitly mentioned. Other speaker's name not found in transcript."
}}

Analyze now and provide JSON:"""
    
    return prompt


def apply_speaker_mappings(
    segments: List,
    mappings: Dict[str, str]
) -> List:
    """
    Apply speaker name mappings to transcript segments.
    
    Args:
        segments: List of TranscriptSegment objects
        mappings: Dictionary mapping generic labels to actual names
    
    Returns:
        Updated list of segments with real speaker names
    """
    for segment in segments:
        if segment.speaker in mappings:
            segment.speaker = mappings[segment.speaker]
    
    return segments


def format_speaker_summary(mappings: Dict[str, str]) -> str:
    """Format speaker mappings for display."""
    if not mappings:
        return "No speaker mappings applied"
    
    lines = ["Speaker Identification:"]
    for generic, actual in sorted(mappings.items()):
        lines.append(f"  {generic} -> {actual}")
    
    return "\n".join(lines)

