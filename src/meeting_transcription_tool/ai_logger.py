"""
Comprehensive AI request/response logging for cost optimization and debugging.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("meeting_transcription_tool.ai_logger")


class AILogger:
    """Logs all AI API calls with full request/response details."""
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize AI logger.
        
        Args:
            log_dir: Directory to save logs. If None, uses ./ai_logs
        """
        self.log_dir = Path(log_dir) if log_dir else Path("./ai_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def log_request(
        self,
        provider: str,
        model: str,
        request_data: Dict[str, Any],
        estimated_tokens: Optional[int] = None,
    ) -> str:
        """
        Log an AI request.
        
        Returns:
            Log file path for this request
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        log_file = self.log_dir / f"ai_request_{timestamp}.json"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "request": request_data,
            "estimated_tokens": estimated_tokens,
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False)
        
        logger.info(f"AI request logged: {log_file}")
        return str(log_file)
    
    def log_response(
        self,
        request_log_file: str,
        response_data: Dict[str, Any],
        actual_tokens: Optional[Dict[str, int]] = None,
        cost_estimate: Optional[float] = None,
    ) -> str:
        """
        Log an AI response and link it to the request.
        
        Args:
            request_log_file: Path to the request log file
            response_data: Response data from AI
            actual_tokens: Token usage dict with 'input', 'output', 'total'
            cost_estimate: Estimated cost in USD
            
        Returns:
            Log file path for this response
        """
        request_path = Path(request_log_file)
        response_file = request_path.parent / f"{request_path.stem}_response.json"
        
        # Load request data
        with open(request_path, 'r', encoding='utf-8') as f:
            request_data = json.load(f)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_log": str(request_path),
            "request": request_data["request"],
            "response": response_data,
            "token_usage": actual_tokens or {},
            "cost_estimate_usd": cost_estimate,
            "provider": request_data["provider"],
            "model": request_data["model"],
        }
        
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False)
        
        logger.info(f"AI response logged: {response_file}")
        
        # Print cost summary
        if actual_tokens and cost_estimate:
            logger.info(
                f"AI call cost: ${cost_estimate:.6f} "
                f"(input: {actual_tokens.get('input', 0):,}, "
                f"output: {actual_tokens.get('output', 0):,} tokens)"
            )
        
        return str(response_file)
    
    def get_cost_summary(self, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get cost summary from all logged calls.
        
        Args:
            start_date: Only include logs after this date
            
        Returns:
            Summary dict with total cost, token usage, etc.
        """
        total_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        call_count = 0
        
        for log_file in self.log_dir.glob("*_response.json"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if start_date:
                    log_time = datetime.fromisoformat(data["timestamp"])
                    if log_time < start_date:
                        continue
                
                cost = data.get("cost_estimate_usd", 0)
                tokens = data.get("token_usage", {})
                
                total_cost += cost
                total_input_tokens += tokens.get("input", 0)
                total_output_tokens += tokens.get("output", 0)
                call_count += 1
            except Exception as e:
                logger.warning(f"Error reading log file {log_file}: {e}")
        
        return {
            "total_calls": call_count,
            "total_cost_usd": total_cost,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
        }


# Global logger instance
_global_logger: Optional[AILogger] = None


def get_ai_logger(log_dir: Optional[str] = None) -> AILogger:
    """Get or create global AI logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = AILogger(log_dir)
    return _global_logger
