"""
AI-powered speaker identification module.

Uses OpenAI GPT-5 Mini (default), GPT-4o, or Gemini 2.0 Flash to analyze
transcripts and identify speakers by their actual names or descriptive roles.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Optional, Literal, Any, Iterable, Mapping
import json
from dataclasses import dataclass, field

from openai import OpenAI


@dataclass
class SpeakerMapping:
    """Mapping from generic speaker label to actual name."""
    generic_label: str  # e.g., "SPEAKER_00"
    actual_name: str  # e.g., "Ian" or "Interviewer"
    confidence: str     # e.g., "high", "medium", "low"
    reasoning: str      # Why the AI thinks this is correct


@dataclass
class SpeakerIdentificationResult:
    """Structured result for AI-based speaker identification."""

    mappings: Dict[str, str] = field(default_factory=dict)
    model: str = ""
    provider: str = ""
    request_metadata: Dict[str, str] = field(default_factory=dict)
    response_metadata: Dict[str, str] = field(default_factory=dict)
    raw_response: Optional[Dict] = None
    audio_file_id: Optional[str] = None
    audio_upload_bytes: int = 0

    def as_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "provider": self.provider,
            "model": self.model,
            "mappings": self.mappings,
            "request": self.request_metadata,
            "response": self.response_metadata,
            "audio_file_id": self.audio_file_id,
            "audio_bytes_uploaded": self.audio_upload_bytes,
        }


def identify_speakers(
    transcript_text: str,
    num_speakers: Optional[int] = None,
    participant_names: Optional[List[str]] = None,
    participant_context: Optional[str] = None,
    filename: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Literal["gpt-5-mini", "gpt-4o", "gemini-2.0-flash"] = "gpt-5-mini",
    upload_audio: bool = True,
 ) -> SpeakerIdentificationResult:
    """
    Use AI to identify speakers in a transcript and map generic labels to actual names.
    
    Args:
        transcript_text: The full transcript with generic speaker labels
        num_speakers: Number of speakers in the conversation (optional)
        participant_names: List of known participant names (optional, rarely needed)
        participant_context: Additional context about the meeting/participants (optional)
        filename: Name of the audio file (optional, often contains participant names)
        api_key: OpenAI API key (optional, will use env var if not provided)
        model: AI model to use - "gpt-5-mini" (default), "gpt-4o", or "gemini-2.0-flash"
    
    Returns:
        SpeakerIdentificationResult containing mappings and metadata.
    """
    if model in {"gpt-5-mini", "gpt-4o"}:
        return _identify_with_openai(
            transcript_text,
            num_speakers,
            participant_names,
            participant_context,
            filename,
            api_key,
            model_name=model,
            upload_audio=upload_audio,
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
    model_name: str,
    upload_audio: bool,
 ) -> SpeakerIdentificationResult:
    """Identify speakers using OpenAI GPT family (GPT-5 Mini/GPT-4o)."""
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
    system_instruction = """You are an expert conversation analyst specializing in accurate speaker identification and timeline alignment.

Your responsibilities:
- Map each diarization label to the real-world participant name whenever possible.
- Leverage uploaded audio, filename hints, conversation context, and explicit mentions.
- Preserve the chronological order and ensure every segment is assigned to exactly one mapped speaker.

Core directives:
1. **Filename first** — Extract potential participant names from the audio filename (e.g., "Alice_Bob_sync.m4a" implies Alice and Bob).
2. **Uploaded audio** — Compare voices within the provided audio attachment to resolve ambiguous cases or confirm role changes.
3. **Transcript evidence** — Use self-introductions (“Hi, this is Alice”), references (“Thanks, Bob”), or descriptions (titles, departments).
4. **Context inference** — Apply best-judgement roles when names are absent (Interviewer, Candidate, Host, Manager, Support Engineer, etc.).
5. **Timeline fidelity** — Never merge speakers. Maintain unique labels for distinct voices across the entire timeline.
6. **Transparency** — Provide reasoning describing the exact clues (time, quote, filename, context) that justify each mapping.

JSON contract:
- Always return a JSON object with `speaker_mappings`, `analysis`, and `confidence_notes`.
- `speaker_mappings` is an array of objects with `generic_label`, `actual_name`, `confidence`, and `reasoning`.
- Confidence must be one of: high, medium, low.
- Reasoning must cite time ranges or transcript snippets (referenced by timeline markers).
"""

    audio_upload = _maybe_upload_audio(client, filename) if upload_audio else None

    request_metadata = _build_request_metadata(
        provider="openai",
        model=model_name,
        temperature=0.2,
        system_instruction=system_instruction,
        prompt=prompt,
        audio_metadata=audio_upload,
    )

    user_content: List[Dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    if audio_upload:
        user_content.append({
            "type": "input_audio",
            "audio": {
                "file_id": audio_upload["file_id"],
            }
        })

    api_method_used = "responses"
    request_metadata["api_method"] = api_method_used
    try:
        response = client.responses.create(
            model=model_name,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_instruction}]},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = _extract_response_text(response)
    except Exception:
        # Fallback to chat completions for environments without Responses API support
        api_method_used = "chat-completions"
        request_metadata["api_method"] = api_method_used
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
    
    # Parse response
    result = json.loads(content)
    
    # Extract mappings
    mappings = {}
    for mapping in result.get("speaker_mappings", []):
        generic_label = mapping.get("generic_label", "")
        actual_name = mapping.get("actual_name", "")
        if generic_label and actual_name:
            mappings[generic_label] = actual_name

    response_metadata = _build_response_metadata(
        provider="openai",
        model=model_name,
        response=response,
        raw_json=result,
    )
    response_metadata["api_method"] = api_method_used
    if audio_upload:
        response_metadata["audio_file_id"] = audio_upload["file_id"]
        response_metadata["audio_bytes_uploaded"] = str(audio_upload["bytes"])
    
    return SpeakerIdentificationResult(
        mappings=mappings,
        model=model_name,
        provider="openai",
        request_metadata=request_metadata,
        response_metadata=response_metadata,
        raw_response=result,
        audio_file_id=audio_upload["file_id"] if audio_upload else None,
        audio_upload_bytes=audio_upload["bytes"] if audio_upload else 0,
    )


def _identify_with_gemini(
    transcript_text: str,
    num_speakers: Optional[int],
    participant_names: Optional[List[str]],
    participant_context: Optional[str],
    filename: Optional[str],
    api_key: Optional[str],
 ) -> SpeakerIdentificationResult:
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

    request_metadata = _build_request_metadata(
        provider="google",
        model="gemini-2.0-flash-exp",
        temperature=0.2,
        system_instruction=system_instruction,
        prompt=prompt,
    )

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
    
    response_metadata = {
        "provider": "google",
        "model": "gemini-2.0-flash-exp",
    }
    if hasattr(response, "usage_metadata"):
        usage = response.usage_metadata
        response_metadata.update({
            "prompt_token_count": getattr(usage, "prompt_token_count", None),
            "candidates_token_count": getattr(usage, "candidates_token_count", None),
        })
    
    return SpeakerIdentificationResult(
        mappings=mappings,
        model="gemini-2.0-flash",
        provider="google",
        request_metadata=request_metadata,
        response_metadata={k: v for k, v in response_metadata.items() if v is not None},
        raw_response=result,
    )


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

TRANSCRIPT SEGMENTS (chronological with timeline markers):
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

4. Use speech patterns and timeline alignment:
   - Formal vs casual language
   - Technical vs general topics
   - Decision-making authority
   - Relationship indicators
   - Track consistent voices using the time ranges provided
   - Reference the uploaded audio (if present) to resolve ambiguity

5. Naming priority:
   a) Filename names (if match transcript) -> "Ian", "Laiks"
   b) Actual name if clearly mentioned -> "Sarah"
   c) Role if no name but clear -> "Interviewer"
   d) Descriptive role if ambiguous -> "Manager"

REQUIREMENTS:
✓ Be decisive - choose best available label
✓ Be consistent - same person = same label
✓ Be specific - avoid generic labels when possible
✓ Provide reasoning that cites timeline evidence (e.g., "00:05s reference to 'Ian'")
✓ Note when audio cues influenced the decision (voice match, tone, etc.)

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


def _build_request_metadata(
    provider: str,
    model: str,
    temperature: float,
    system_instruction: str,
    prompt: str,
    max_preview_chars: int = 280,
    audio_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Create a sanitized preview of the AI request for logging/display."""

    def _preview(text: str) -> str:
        sanitized = " ".join(text.strip().split())
        if len(sanitized) > max_preview_chars:
            return sanitized[:max_preview_chars - 1] + "…"
        return sanitized

    metadata: Dict[str, str] = {
        "provider": provider,
        "model": model,
        "temperature": f"{temperature:.2f}",
        "system_instruction_preview": _preview(system_instruction),
        "user_prompt_preview": _preview(prompt),
        "prompt_char_count": str(len(prompt)),
    }
    if audio_metadata:
        metadata.update({
            "audio_filename": audio_metadata.get("filename", ""),
            "audio_file_id": audio_metadata.get("file_id", ""),
            "audio_bytes": str(audio_metadata.get("bytes", "")),
        })
    return metadata


def _build_response_metadata(
    provider: str,
    model: str,
    response,
    raw_json: Dict,
) -> Dict[str, str]:
    """Create a sanitized summary of the AI response metadata."""
    metadata: Dict[str, str] = {
        "provider": provider,
        "model": model,
    }

    response_id = getattr(response, "id", None)
    if response_id:

        metadata["response_id"] = response_id

    usage = getattr(response, "usage", None)
    if usage:
        prompt_tokens = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        if prompt_tokens is not None:
            metadata["prompt_tokens"] = str(prompt_tokens)
        if completion_tokens is not None:
            metadata["completion_tokens"] = str(completion_tokens)
        if total_tokens is not None:
            metadata["total_tokens"] = str(total_tokens)

    if "analysis" in raw_json:
        metadata["analysis_preview"] = _trim_text(raw_json["analysis"])

    return {k: v for k, v in metadata.items() if v is not None}


def _trim_text(value: str, max_chars: int = 200) -> str:
    """Trim text for previews."""
    if not isinstance(value, str):
        return ""
    text = " ".join(value.strip().split())
    if len(text) > max_chars:
        return text[:max_chars - 1] + "…"
    return text


def _maybe_upload_audio(client: OpenAI, filename: Optional[str]) -> Optional[Dict[str, Any]]:
    """Upload the audio file to OpenAI Responses API for richer analysis."""
    if not filename:
        return None
    try:
        audio_path = Path(filename)
    except (TypeError, ValueError):
        return None

    if not audio_path.exists() or not audio_path.is_file():
        return None

    try:
        file_size = audio_path.stat().st_size
        with audio_path.open("rb") as file_handle:
            uploaded = client.files.create(
                file=file_handle,
                purpose="assistants",
            )
    except Exception as exc:  # pragma: no cover - network/API failure path
        print(f"[AI] Audio upload skipped: {exc}")
        return None

    return {
        "file_id": uploaded.id,
        "filename": audio_path.name,
        "bytes": file_size,
    }


def _extract_response_text(response: Any) -> str:
    """Extract assistant JSON text from the OpenAI Responses API reply."""
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text

    output = getattr(response, "output", None)
    if output:
        chunks: List[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if not content:
                continue
            for block in content:
                block_type = getattr(block, "type", None)
                if block_type in {"output_text", "text"}:
                    text_val = getattr(block, "text", "")
                    if text_val:
                        chunks.append(text_val)
        if chunks:
            return "".join(chunks)

    # Fallback for compatibility with chat completions style objects
    if hasattr(response, "choices"):
        return response.choices[0].message.content

    raise ValueError("Unable to extract response text from OpenAI response object.")


def _coerce_ms(value: Any) -> Optional[float]:
    """Convert a timestamp value to milliseconds as float."""
    if isinstance(value, (int, float)):
        return float(value)
    return None


def format_segments_for_prompt(segments: Iterable[Mapping[str, Any]]) -> str:
    """Build a timeline-aware transcript string for AI consumption."""
    formatted_segments: List[str] = []

    for index, segment in enumerate(segments, start=1):
        speaker = str(segment.get("speaker", "UNKNOWN")).strip() or "UNKNOWN"
        text = str(segment.get("text", "")).strip()
        start_ms = _coerce_ms(segment.get("start_ms"))
        end_ms = _coerce_ms(segment.get("end_ms"))

        if start_ms is not None and end_ms is not None:
            time_range = f"{start_ms/1000:.2f}s → {end_ms/1000:.2f}s"
        elif start_ms is not None:
            time_range = f"≥ {start_ms/1000:.2f}s"
        else:
            time_range = "unknown"

        header = f"[{index:02d}] {speaker} | {time_range}"
        if not text:
            text = "(no transcript text captured)"

        formatted_segments.append(f"{header}\n{text}")

    return "\n\n".join(formatted_segments)


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

