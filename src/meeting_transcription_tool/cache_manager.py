"""
Cache management for pipeline stages.

Provides caching functionality to avoid re-running expensive operations
when intermediate files already exist.
"""
from __future__ import annotations

import os
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file for cache key generation."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        # If file doesn't exist or can't be read, return empty hash
        return ""


def get_cache_key(audio_path: str, stage: str, **kwargs) -> str:
    """
    Generate a cache key for a pipeline stage.
    
    Args:
        audio_path: Path to the audio file
        stage: Stage identifier ("stage1", "stage2", etc.)
        **kwargs: Additional parameters that affect the stage output
    
    Returns:
        Cache key string
    """
    # Include file hash and modification time in key
    file_hash = compute_file_hash(audio_path)
    try:
        mtime = os.path.getmtime(audio_path)
    except Exception:
        mtime = 0
    
    # Include relevant kwargs in hash
    relevant_params = {}
    if stage == "stage1":
        # Stage 1 depends on: model, language, temperature
        relevant_params = {
            "model": kwargs.get("whisper_model", "whisper-1"),
            "language": kwargs.get("language"),
            "temperature": kwargs.get("temperature", 0.0),
        }
    elif stage == "stage2":
        # Stage 2 depends on: ai_model, speaker_context
        relevant_params = {
            "ai_model": kwargs.get("ai_model", "gpt-5-mini"),
            "speaker_context": kwargs.get("speaker_context"),
        }
    
    # Create hash from all relevant parameters
    param_str = json.dumps(relevant_params, sort_keys=True)
    combined = f"{stage}:{file_hash}:{mtime}:{param_str}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def get_stage1_cache_path(audio_path: str, output_dir: str, **kwargs) -> str:
    """Get the cache path for Stage 1 output."""
    base_name = Path(audio_path).stem
    return os.path.join(output_dir, f"{base_name}_stage1_transcript.json")


def get_stage2_cache_path(audio_path: str, output_dir: str, **kwargs) -> str:
    """Get the cache path for Stage 2 output."""
    base_name = Path(audio_path).stem
    return os.path.join(output_dir, f"{base_name}_stage2_speaker_mappings.json")


def is_stage1_cached(audio_path: str, output_dir: str, **kwargs) -> tuple[bool, Optional[str]]:
    """
    Check if Stage 1 output is cached.
    
    Returns:
        Tuple of (is_cached, cache_file_path)
    """
    cache_path = get_stage1_cache_path(audio_path, output_dir, **kwargs)
    
    if os.path.exists(cache_path):
        # Verify the cache is for the same input file
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if audio file path matches (normalize paths)
            cached_audio = os.path.normpath(cache_data.get("audio_file", ""))
            current_audio = os.path.normpath(os.path.abspath(audio_path))
            
            if cached_audio == current_audio:
                # Check if model matches
                cached_model = cache_data.get("metadata", {}).get("model", "")
                current_model = kwargs.get("whisper_model", "whisper-1")
                
                if cached_model == current_model:
                    return True, cache_path
        
        except Exception:
            # If cache file is corrupted, treat as not cached
            pass
    
    return False, None


def is_stage2_cached(
    stage1_file: str,
    audio_path: str,
    output_dir: str,
    **kwargs
) -> tuple[bool, Optional[str]]:
    """
    Check if Stage 2 output is cached.
    
    Returns:
        Tuple of (is_cached, cache_file_path)
    """
    cache_path = get_stage2_cache_path(audio_path, output_dir, **kwargs)
    
    if os.path.exists(cache_path):
        # Verify the cache is for the same stage1 file
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if source file matches
            cached_source = os.path.normpath(cache_data.get("source_file", ""))
            current_source = os.path.normpath(os.path.abspath(stage1_file))
            
            if cached_source == current_source:
                # Check if AI model matches
                cached_model = cache_data.get("ai_model", "")
                current_model = kwargs.get("ai_model", "gpt-5-mini")
                
                # Check if speaker context matches (if provided)
                cached_context = cache_data.get("speaker_context")
                current_context = kwargs.get("speaker_context")
                
                if cached_model == current_model and cached_context == current_context:
                    return True, cache_path
        
        except Exception:
            # If cache file is corrupted, treat as not cached
            pass
    
    return False, None


def validate_cache_file(cache_path: str, expected_keys: list[str]) -> bool:
    """
    Validate that a cache file has the expected structure.
    
    Args:
        cache_path: Path to cache file
        expected_keys: List of keys that should be present
    
    Returns:
        True if cache is valid, False otherwise
    """
    if not os.path.exists(cache_path):
        return False
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if all expected keys are present
        for key in expected_keys:
            if key not in data:
                return False
        
        return True
    except Exception:
        return False

