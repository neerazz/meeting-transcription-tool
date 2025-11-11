# Install FFmpeg for Audio Format Support

## Why FFmpeg?

FFmpeg is needed to handle M4A and other audio formats for speaker diarization. While OpenAI Whisper API can handle M4A files directly, the local speaker diarization library (pyannote.audio) needs FFmpeg to process certain audio formats.

## Quick Install (Windows)

### Option 1: Using Chocolatey (Recommended)

```powershell
# Install Chocolatey if you don't have it
# Run PowerShell as Administrator

# Install FFmpeg
choco install ffmpeg

# Verify installation
ffmpeg -version
```

###Option 2: Manual Download

1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Download the "ffmpeg-release-essentials.zip"
3. Extract to `C:\ffmpeg`
4. Add to PATH:
   - Open System Properties → Environment Variables
   - Edit "Path" variable
   - Add `C:\ffmpeg\bin`
   - Click OK
5. Restart PowerShell
6. Verify: `ffmpeg -version`

### Option 3: Using winget

```powershell
winget install --id=Gyan.FFmpeg -e
```

## Quick Install (Mac)

```bash
# Using Homebrew
brew install ffmpeg

# Verify
ffmpeg -version
```

## Quick Install (Linux)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Verify
ffmpeg -version
```

## After Installation

Once FFmpeg is installed, restart your terminal and run your transcription command again:

```powershell
python -m src.meeting_transcription_tool.cli transcribe --input "your-audio.m4a"
```

## Alternative: Convert Audio First

If you can't install FFmpeg, you can convert your M4A file to WAV using an online converter or another tool, then use the WAV file:

```powershell
python -m src.meeting_transcription_tool.cli transcribe --input "your-audio.wav"
```

