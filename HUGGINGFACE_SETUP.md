# Hugging Face Setup for Speaker Diarization

## ⚠️ IMPORTANT: Required Steps Before Running

The speaker diarization model (`pyannote/speaker-diarization-3.1`) is **gated**, which means you must accept the user agreements before you can use it.

## 📋 Step-by-Step Setup

### 1. Create Hugging Face Account (if you don't have one)
- Go to: https://huggingface.co/join
- Sign up with your email

### 2. Accept Model User Agreements

You need to accept the agreements for TWO models:

#### Model 1: Speaker Diarization
1. Go to: https://huggingface.co/pyannote/speaker-diarization-3.1
2. Scroll down and click the **"Agree and access repository"** button
3. Wait for confirmation

#### Model 2: Segmentation (required by diarization)
1. Go to: https://huggingface.co/pyannote/segmentation-3.0
2. Scroll down and click the **"Agree and access repository"** button
3. Wait for confirmation

### 3. Create Access Token

1. Go to: https://huggingface.co/settings/tokens
2. Click **"New token"**
3. Give it a name (e.g., "meeting-transcription-tool")
4. Select **"Read"** access
5. Click **"Generate token"**
6. Copy the token (starts with `hf_...`)

### 4. Add Token to .env File

Open your `.env` file and add:

```
HUGGING_FACE_TOKEN=hf_your_token_here
```

### 5. Verify Setup

Run this command to verify:

```powershell
python tests/test_real_audio.py --audio-file "your-audio-file.m4a"
```

If you see errors about "gated" or "private" models, make sure you:
- ✅ Accepted BOTH model agreements (steps above)
- ✅ Waited a few minutes for the permissions to propagate
- ✅ Used the correct token in your .env file

## 🔍 Troubleshooting

### "Cannot access pyannote/speaker-diarization-3.1"

**Solution:** Accept the user agreements (see Step 2 above)

### "Token not found"

**Solution:** Check your `.env` file has:
```
HUGGING_FACE_TOKEN=hf_your_actual_token
```

### "Still getting access errors after accepting"

**Solution:** 
1. Wait 2-3 minutes for permissions to sync
2. Try logging out and back in to Hugging Face
3. Regenerate your token
4. Make sure you're logged in with the same account that accepted the agreements

## 📝 Why Is This Required?

pyannote.audio models are research models that require users to:
- Accept the license terms
- Acknowledge proper usage guidelines
- Comply with research ethics

This is a one-time setup per Hugging Face account.

## ✅ Once Setup is Complete

After accepting the agreements and setting your token, you can run the transcription tool normally:

```powershell
python tests/test_real_audio.py --audio-file "path/to/audio.m4a"
```

The tool will:
1. Identify speakers (diarization) ✅
2. Transcribe speech to text ✅
3. Map text to speakers ✅
4. Export in multiple formats ✅

