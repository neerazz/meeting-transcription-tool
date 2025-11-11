# Pipeline Stages

The transcription workflow is split into three modular stages. Each stage is idempotent and produces intermediate artefacts you can re-use.

## Stage 1 – Transcribe & Diarize
- Command: `cli_stages stage1`
- Output: `<basename>_stage1_transcript.json`
- Contents: Whisper transcript, diarization labels, timing (milliseconds), metadata.

### Responsibilities
- Upload audio to Whisper (OpenAI) for transcription.
- Run diarization to get initial `SPEAKER_XX` labels.
- Persist an intermediate JSON compatible with later stages.

## Stage 2 – AI Speaker Identification
- Command: `cli_stages stage2`
- Inputs: Stage 1 JSON.
- Outputs:
  - `<basename>_stage2_speaker_mappings.json`
  - Console preview of AI request/response metadata.

### Highlights
- Uses GPT-5 Mini with reasoning by default (`--ai-model gpt-5-mini`).
- Uploads the **original audio** to the OpenAI Responses API for voice-aware reasoning.
- Supplies timeline-aware transcript segments: `[index] SPEAKER | 00.00s → 05.23s`.
- Stores request/response metadata and uploaded audio file id for auditing.

### Mapping JSON
```json
{
  "source_file": "meeting_stage1_transcript.json",
  "audio_file": "/records/meeting.m4a",
  "ai_model": "gpt-5-mini",
  "speaker_context": "Panel interview",
  "mappings": {
    "SPEAKER_00": "Interviewer (Dana Chen)",
    "SPEAKER_01": "Candidate (Ravi Patel)"
  },
  "ai_request_metadata": {
    "api_method": "responses",
    "audio_file_id": "file-abc123"
  },
  "ai_response_metadata": {
    "prompt_tokens": "1824",
    "completion_tokens": "620"
  }
}
```

## Stage 3 – Apply Speaker Names & Export
- Command: `cli_stages stage3`
- Inputs: Stage 1 transcript + optional Stage 2 mappings.
- Outputs: TXT, TXT (speaker names), JSON, SRT, DOCX plus summary reports.

### Behaviour
- Applies the mappings to every segment while preserving timeline.
- Generates human-friendly and machine-friendly exports.

## Full Pipeline
Use the umbrella CLI to orchestrate all stages:
```bash
python -m src.meeting_transcription_tool.cli transcribe \
    --input "/audio/standup.m4a" \
    --output-dir "./output"
```

The CLI:
1. Runs Stage 1 in-process.
2. Optionally runs Stage 2 (default enabled; use `--no-identify-speakers` to skip).
3. Runs Stage 3 with the latest mappings.
4. Produces per-run summary reports, including token usage and cost estimates.

## Troubleshooting
- **Speaker mapping empty** – ensure the filename contains participant hints or provide `--speaker-context`.
- **API failures** – confirm your OpenAI key has access to GPT-5 Mini and Responses API.
- **Docs mismatch** – consult this documentation only; root Markdown files are pointers back here.

Next: dive deeper into [speaker identification specifics](./speaker-identification.md).

