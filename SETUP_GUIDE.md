# Setup Guide for Testing Real Audio

## Step 1: Install Dependencies

```powershell
# Make sure you're in the project directory
cd d:\Projects\meeting-transcription-tool

# Install all dependencies
pip install -r requirements.txt
```

## Step 2: Set Up API Keys

You need two API keys to run the transcription tool:

### OpenAI API Key (for Whisper transcription)

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key

### Hugging Face Token (for speaker diarization)

1. Go to https://huggingface.co/settings/tokens
2. Create a new access token (read access is sufficient)
3. Copy the token

### Set Environment Variables (Windows PowerShell)

```powershell
# Option 1: Set for current session
$env:OPENAI_API_KEY = "sk-your-openai-api-key-here"
$env:HUGGING_FACE_TOKEN = "hf_your-huggingface-token-here"

# Option 2: Create a .env file (recommended)
# Copy .env.example to .env and edit it:
Copy-Item .env.example .env
# Then edit .env file with your actual keys
```

### Set Environment Variables (Windows CMD)

```cmd
set OPENAI_API_KEY=sk-your-openai-api-key-here
set HUGGING_FACE_TOKEN=hf_your-huggingface-token-here
```

### Set Environment Variables (Linux/Mac)

```bash
export OPENAI_API_KEY="sk-your-openai-api-key-here"
export HUGGING_FACE_TOKEN="hf_your-huggingface-token-here"
```

## Step 3: Test Your Audio File

Once your API keys are set, run:

```powershell
python tests/test_real_audio.py --audio-file "F:\Meta\Final Proof With Audio and Transcript\Ian Laiks 1on1 10-30 12-10.m4a" --output-dir "F:\Meta\Final Proof With Audio and Transcript\outputs"
```

### What the Tool Will Do

1. **Validate** your audio file (format, size, duration)
2. **Speaker Diarization** - Identify who spoke when (using pyannote.audio)
3. **Transcription** - Convert speech to text (using OpenAI Whisper)
4. **Speaker Mapping** - Match transcribed text to speakers
5. **Export** - Generate transcript files in multiple formats:
   - TXT: `[00:01:23 - 00:01:45] SPEAKER_00: Hello everyone...`
   - JSON: Structured data with metadata
   - SRT: Subtitle format
   - DOCX: Word document (optional)

## Expected Output

After processing, you'll find in the output directory:

```
outputs/
├── Ian Laiks 1on1 10-30 12-10.txt    # Plain text transcript
├── Ian Laiks 1on1 10-30 12-10.json   # Structured JSON
├── Ian Laiks 1on1 10-30 12-10.srt    # Subtitle format
└── Ian Laiks 1on1 10-30 12-10.docx   # Word document
```

## Processing Time

- A 30-minute audio file typically takes **5-10 minutes** to process
- Speaker diarization: ~2-5 minutes
- Transcription (API call): ~1-3 minutes
- Post-processing: ~10-30 seconds

## Costs

- **OpenAI Whisper API**: ~$0.006 per minute of audio
  - Example: 30-minute audio ≈ $0.18
- **Hugging Face**: Free (models run locally)

## Troubleshooting

### "Module not found" errors
```powershell
pip install -r requirements.txt
```

### "API key not found" errors
Make sure you've set the environment variables in the same terminal/session where you're running the script.

### "File not found" errors
Check the audio file path is correct. Use full path with proper escaping:
```powershell
# Correct
"F:\path\to\file.m4a"

# Also correct
'F:\path\to\file.m4a'
```

### Out of memory errors
If you have a very long audio file (>2 hours), you might need more RAM. Consider:
- Splitting the audio into smaller chunks
- Increasing available system memory
- Using a machine with more RAM

## Quick Start (All-in-One)

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API keys (replace with your actual keys)
$env:OPENAI_API_KEY = "sk-..."
$env:HUGGING_FACE_TOKEN = "hf_..."

# 3. Run transcription
python tests/test_real_audio.py --audio-file "your-file.m4a"

# 4. Check outputs folder
ls outputs\
```

## Support

If you encounter issues:
1. Check the error message carefully
2. Verify API keys are set correctly
3. Ensure audio file is in supported format (MP3, WAV, M4A, FLAC)
4. Check file isn't corrupted by playing it first
5. Review logs for detailed error information

