"""
Agent-based speaker identification for maximum quality output.
Uses multi-step reasoning to ensure accurate speaker labeling.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import OpenAI

from .ai_logger import get_ai_logger


@dataclass
class AgentStep:
    """Represents a step in the agent reasoning process."""
    step_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning: str
    confidence: float


class SpeakerIdentificationAgent:
    """
    Agent-based approach for speaker identification.
    Uses iterative refinement to achieve maximum quality.
    """
    
    def __init__(self, client: OpenAI, model: str = "gpt-4o"):
        self.client = client
        self.model = model
        self.ai_logger = get_ai_logger()
        self.steps: List[AgentStep] = []
    
    def identify_speakers(
        self,
        transcript_text: str,
        filename: Optional[str] = None,
        participant_context: Optional[str] = None,
        num_speakers: Optional[int] = None,
    ) -> Dict[str, str]:
        """
        Multi-step agent process for speaker identification.
        
        Steps:
        1. Analyze filename for names/context
        2. Extract key conversation patterns
        3. Identify speakers with confidence scores
        4. Validate and refine mappings
        """
        
        # Step 1: Filename analysis
        filename_analysis = self._analyze_filename(filename)
        self.steps.append(AgentStep(
            step_name="filename_analysis",
            input_data={"filename": filename},
            output_data=filename_analysis,
            reasoning="Extracted names and context from filename",
            confidence=0.9 if filename_analysis.get("names") else 0.3
        ))
        
        # Step 2: Conversation pattern extraction
        patterns = self._extract_conversation_patterns(transcript_text)
        self.steps.append(AgentStep(
            step_name="pattern_extraction",
            input_data={"transcript_length": len(transcript_text)},
            output_data=patterns,
            reasoning="Identified conversation patterns and speaker characteristics",
            confidence=0.7
        ))
        
        # Step 3: Speaker identification
        initial_mappings = self._identify_speakers_step(
            transcript_text=transcript_text,
            filename_analysis=filename_analysis,
            patterns=patterns,
            participant_context=participant_context,
            num_speakers=num_speakers,
        )
        
        # Step 4: Validation and refinement (if needed)
        if len(initial_mappings) < num_speakers or any("Unknown" in v for v in initial_mappings.values()):
            refined_mappings = self._refine_mappings(
                transcript_text=transcript_text,
                initial_mappings=initial_mappings,
                filename_analysis=filename_analysis,
            )
            return refined_mappings
        
        return initial_mappings
    
    def _analyze_filename(self, filename: Optional[str]) -> Dict[str, Any]:
        """Analyze filename for participant names and context."""
        if not filename:
            return {"names": None, "context": None}
        
        from .context_extractor import extract_context_from_filename
        context, names = extract_context_from_filename(filename)
        
        return {
            "names": names.split(", ") if names else None,
            "context": context,
            "has_useful_info": bool(names or context),
        }
    
    def _extract_conversation_patterns(self, transcript_text: str) -> Dict[str, Any]:
        """Extract key patterns from conversation."""
        # Look for introductions, questions, responses
        intro_patterns = [
            r"(?:hi|hello|hey|this is|i'm|i am|my name is)",
            r"(?:thanks|thank you|appreciate)",
            r"(?:let's|let me|i'll|we'll)",
        ]
        
        patterns_found = []
        transcript_lower = transcript_text.lower()
        for pattern in intro_patterns:
            if re.search(pattern, transcript_lower):
                patterns_found.append(pattern)
        
        return {
            "has_introductions": any("i'm" in p or "name is" in p for p in patterns_found),
            "has_questions": "?" in transcript_text,
            "patterns": patterns_found,
        }
    
    def _identify_speakers_step(
        self,
        transcript_text: str,
        filename_analysis: Dict[str, Any],
        patterns: Dict[str, Any],
        participant_context: Optional[str],
        num_speakers: Optional[int],
    ) -> Dict[str, str]:
        """Core speaker identification step."""
        from .speaker_identifier import _build_optimized_prompt
        
        # Build context-aware prompt
        prompt = _build_optimized_prompt(
            transcript_text=transcript_text,
            num_speakers=num_speakers,
            participant_names=filename_analysis.get("names"),
            participant_context=participant_context or filename_analysis.get("context"),
            filename=None,  # Already extracted
        )
        
        system_instruction = """You are an expert at identifying speakers in conversations.
Analyze the transcript and map each generic speaker label to actual names or roles.
Be precise, consistent, and cite evidence for each mapping."""
        
        # Make API call with logging
        request_data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        
        request_log = self.ai_logger.log_request(
            provider="openai",
            model=self.model,
            request_data=request_data,
            estimated_tokens=len(system_instruction + prompt) // 4,
        )
        
        response = self.client.chat.completions.create(**request_data, timeout=300.0)
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Extract mappings
        mappings = {}
        for mapping in result.get("speaker_mappings", []):
            generic_label = mapping.get("generic_label", "")
            actual_name = mapping.get("actual_name", "")
            if generic_label and actual_name:
                mappings[generic_label] = actual_name
        
        # Log response
        token_usage = {}
        if hasattr(response, 'usage'):
            usage = response.usage
            token_usage = {
                "input": getattr(usage, 'prompt_tokens', 0),
                "output": getattr(usage, 'completion_tokens', 0),
                "total": getattr(usage, 'total_tokens', 0),
            }
        
        self.ai_logger.log_response(
            request_log_file=request_log,
            response_data={"mappings": mappings, "raw": result},
            actual_tokens=token_usage,
        )
        
        return mappings
    
    def _refine_mappings(
        self,
        transcript_text: str,
        initial_mappings: Dict[str, str],
        filename_analysis: Dict[str, Any],
    ) -> Dict[str, str]:
        """Refine mappings using full conversation context."""
        # Use full transcript for refinement
        refinement_prompt = f"""Refine speaker mappings using the FULL conversation context.

Current mappings:
{json.dumps(initial_mappings, indent=2)}

Filename analysis:
{json.dumps(filename_analysis, indent=2)}

FULL TRANSCRIPT:
{transcript_text}

Identify any missing or incorrect mappings. Return JSON with refined mappings."""
        
        system_instruction = """You are refining speaker identifications. Use the full conversation
to correct any errors and fill in missing speaker names."""
        
        request_data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": refinement_prompt},
            ],
            "temperature": 0.1,  # Lower temperature for refinement
            "response_format": {"type": "json_object"},
        }
        
        request_log = self.ai_logger.log_request(
            provider="openai",
            model=self.model,
            request_data=request_data,
            estimated_tokens=len(system_instruction + refinement_prompt) // 4,
        )
        
        response = self.client.chat.completions.create(**request_data, timeout=300.0)
        content = response.choices[0].message.content
        result = json.loads(content)
        
        refined = {}
        for mapping in result.get("speaker_mappings", []):
            generic_label = mapping.get("generic_label", "")
            actual_name = mapping.get("actual_name", "")
            if generic_label and actual_name:
                refined[generic_label] = actual_name
        
        # Log refinement
        token_usage = {}
        if hasattr(response, 'usage'):
            usage = response.usage
            token_usage = {
                "input": getattr(usage, 'prompt_tokens', 0),
                "output": getattr(usage, 'completion_tokens', 0),
            }
        
        self.ai_logger.log_response(
            request_log_file=request_log,
            response_data={"refined_mappings": refined},
            actual_tokens=token_usage,
        )
        
        return refined


# Import re for pattern matching
import re
