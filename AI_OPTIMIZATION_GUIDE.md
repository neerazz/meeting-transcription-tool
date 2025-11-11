# AI Optimization & Logging Guide

## Overview
This guide explains the AI optimization features, comprehensive logging, and quality improvements implemented for maximum transcript quality.

## Key Features

### 1. Comprehensive AI Request/Response Logging
All AI calls are logged with:
- **Full request data**: Model, messages, parameters, estimated tokens
- **Full response data**: Content, parsed results, actual token usage
- **Cost tracking**: Automatic cost calculation per call
- **Log location**: `./ai_logs/` directory

**View costs:**
```bash
python view_ai_costs.py
```

### 2. Intelligent Prompt Optimization
The system automatically optimizes prompts based on filename context:

- **If filename has names/context**: Uses truncated transcript (8000 chars) to save tokens
- **If filename doesn't help**: Uses FULL conversation for maximum quality

This balances cost optimization with quality.

### 3. Enhanced Filename Parsing
Improved extraction of:
- Participant names (up to 4 names)
- Meeting types (1-on-1, interview, review, etc.)
- Dates and times
- Context descriptions

### 4. Parallel Processing Optimization
- **Auto-detects CPU cores**
- **Uses 50% of CPU** for maximum parallelization without hanging
- **Default**: `(CPU cores + 1) // 2`, max 16 workers
- **Prevents system overload**

### 5. Timeout Protection
- **300-second timeout** per AI call
- **Prevents infinite hangs**
- **Graceful fallback** if model unavailable

## Flow Optimization

### Speaker Identification Flow

1. **Filename Analysis** (automatic)
   - Extracts names, context, meeting type
   - If helpful → use truncated transcript (cost optimization)
   - If not helpful → use full transcript (quality optimization)

2. **Context Extraction**
   - Uses filename first
   - Falls back to file metadata
   - Passes to AI for better identification

3. **AI Call Strategy**
   - GPT-5 Mini → maps to o1-mini (reasoning model)
   - Falls back to gpt-4o if needed
   - Full request/response logging

4. **Quality Validation**
   - Checks for "Unknown" labels
   - Validates all speakers mapped
   - Can trigger refinement if needed

## Timestamp & Name Tagging

### Timeline Format
Segments are formatted with precise timestamps:
```
[01] SPEAKER_00 | 0.00s → 5.23s
Text content here...
```

### Name Tagging Priority
1. **Filename names** (highest priority)
2. **Explicit mentions** in transcript
3. **Role inference** from context
4. **Descriptive roles** as fallback

## Usage Examples

### Process Directory from Stage 2
```bash
python process_stage2_directory.py \
    -d "/path/to/stage1/files" \
    -o "/path/to/output" \
    --ai-model gpt-5-mini \
    --parallel 8  # Optional: override auto-detection
```

### View AI Costs
```bash
python view_ai_costs.py
```

### Check Logs
```bash
ls -lh ./ai_logs/
cat ./ai_logs/ai_request_*.json  # View requests
cat ./ai_logs/ai_request_*_response.json  # View responses
```

## Cost Optimization Tips

1. **Use descriptive filenames**: Include participant names
   - Good: `Alice_Bob_1on1_2024-01-15.m4a`
   - Bad: `meeting.m4a`

2. **Monitor costs**: Run `view_ai_costs.py` regularly

3. **Review logs**: Check `./ai_logs/` to see what's being sent

4. **Adjust truncation**: If filename has context, system auto-truncates to save tokens

## Quality Optimization Tips

1. **Provide context**: Use `--speaker-context` if filename doesn't help
2. **Full transcript mode**: System automatically uses full transcript if filename lacks context
3. **Review mappings**: Check `_stage2_speaker_mappings.json` for reasoning

## Troubleshooting

### High Costs
- Check `./ai_logs/` for large requests
- Ensure filenames have participant names
- Review token usage in logs

### Poor Quality
- Ensure filenames are descriptive
- Provide `--speaker-context` manually
- Check if full transcript is being used (see logs)

### Processing Hangs
- Check timeout settings (300s default)
- Reduce parallel workers if CPU overloaded
- Check network connectivity

## Log File Structure

### Request Log (`ai_request_*.json`)
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "provider": "openai",
  "model": "gpt-5-mini",
  "request": {
    "model": "o1-mini",
    "messages": [...],
    "temperature": 0.2
  },
  "estimated_tokens": 1500
}
```

### Response Log (`ai_request_*_response.json`)
```json
{
  "timestamp": "2024-01-15T10:30:05",
  "request_log": "./ai_logs/ai_request_...json",
  "response": {
    "mappings": {...},
    "parsed_result": {...}
  },
  "token_usage": {
    "input": 1200,
    "output": 300,
    "total": 1500
  },
  "cost_estimate_usd": 0.000225
}
```

## Next Steps

1. Run your transcription with the new optimizations
2. Monitor costs with `view_ai_costs.py`
3. Review logs in `./ai_logs/` to optimize further
4. Adjust parallel workers based on your system
