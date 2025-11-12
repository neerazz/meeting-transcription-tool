# Speaker Identification

Stage 2 converts diarization labels (`SPEAKER_00`, `SPEAKER_01`, …) into meaningful names or roles. This page explains how GPT-5 Mini is prompted, how audio evidence is shared, and where to inspect results.

## Model Strategy
- Default model: `gpt-5-mini` (with reasoning enabled).
- Alternate models: `gpt-4o`, `gemini-2.0-flash`.
- Timeline-aware prompts ensure every segment is uniquely mapped.
- Uploaded audio is attached to the Responses API call to assist disambiguation.

## Prompt Anatomy
- System prompt emphasises:
  - Filename-based name extraction.
  - Audio cross-check to confirm voice consistency.
  - Requirement to cite timeline markers in reasoning.
  - JSON schema with `speaker_mappings`, `analysis`, and `confidence_notes`.
- User prompt contains timeline formatted segments:  
  `[01] SPEAKER_00 | 00.00s → 05.21s`

## Audio Upload
- The original audio file is uploaded (purpose `assistants`) before the AI request.
- Metadata (file id + byte size) is saved to the mapping JSON.
- If upload fails, the request gracefully falls back to transcript-only reasoning.

## Auditing Metadata
Every Stage 2 run emits:
- Console printout of sanitized request and response metadata.
- `<basename>_stage2_speaker_mappings.json` fields:
  - `ai_request_metadata` (previews, audio file id, request method).
  - `ai_response_metadata` (token usage, analysis preview, audio file id echo).
  - `ai_audio_file_id` + `ai_audio_bytes_uploaded`.

## CLI Metrics
When running the combined CLI:
- `ProcessingMetrics.speaker_id_request_preview` captures the prompt summary.
- `ProcessingMetrics.speaker_id_audio_file_id` surfaces in the summary report.
- Token usage and cost calculations adjust based on the selected model.

## Best Practices
- Keep filenames descriptive: `Alice_Bob_quarterly_review.m4a`.
- Provide `--speaker-context` to give the model extra hints.
- Review reasoning in the mapping JSON to validate correctness.
- If unsure about mappings, re-run Stage 2 with added context or switch models.

## Fallback Workflow
- If GPT-5 Mini is unavailable, specify `--ai-model gpt-4o` or `--ai-model gemini-2.0-flash`.
- Gemini Flow skips audio upload (API limitation) but follows the same JSON contract.
- The Stage 2 outputs still include structured metadata for auditing.

Return to the [pipeline overview](./pipeline.md) or jump to [contributing guidelines](./contributing.md).

