# Meeting Transcription Tool

A Python-based CLI to transcribe audio files using OpenAI Whisper for transcription and `pyannote.audio` for speaker diarization.

## Disclaimer

This is a proof-of-concept project and is not intended for use in production environments. It is a demonstration of how to combine speech-to-text and speaker diarization technologies to create a meeting transcription tool. The accuracy of the transcription and diarization is dependent on the underlying models and the quality of the audio input.

## Features

- **Transcription**: High-quality speech-to-text conversion using OpenAI Whisper.
- **Speaker Diarization**: Identifies and labels different speakers in the audio using `pyannote.audio`.
- **Timestamps**: Provides precise timestamps for each spoken segment.
- **Export Options**: Export transcripts in multiple formats (TXT, DOCX, JSON, SRT).
- **CLI Interface**: A simple and easy-to-use command-line interface.

## Setup and Installation

### Prerequisites

- Python 3.9 or higher
- `pip` and `venv`

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/meeting-transcription-tool.git
    cd meeting-transcription-tool
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your API keys:**

    Create a `.env` file in the root of the project by copying the `.env.example` file:
    ```bash
    cp .env.example .env
    ```

    Now, edit the `.env` file with your API keys:

    -   `OPENAI_API_KEY`: Your API key for the OpenAI API.
    -   `HUGGING_FACE_TOKEN`: Your Hugging Face Hub API token. You can get one [here](https://huggingface.co/settings/tokens). This is required to download the `pyannote.audio` models.

## Usage

You can use the tool through the command-line interface.

```bash
python -m src.meeting_transcription_tool.cli transcribe \
    --input "path/to/your/audio.mp3" \
    --output-dir "output_directory"
```

### Command-Line Options

-   `--input`: (Required) The path to the audio file you want to transcribe.
-   `--output-dir`: The directory where the output files will be saved. Defaults to `outputs`.
-   `--api-key`: Your OpenAI API key. If not provided, it will be read from the `OPENAI_API_KEY` environment variable.
-   `--hf-token`: Your Hugging Face API token. If not provided, it will be read from the `HUGGING_FACE_TOKEN` environment variable.
-   `--model`: The Whisper model to use for transcription. Defaults to `whisper-1`.
-   `--formats`: The output formats to export. You can choose multiple formats. Defaults to `txt`, `json`, and `srt`.
-   `--language`: The language of the audio. If not provided, Whisper will automatically detect the language.
-   `--temperature`: The sampling temperature for the Whisper model. Defaults to `0.0`.

## Output Formats

The tool can export the transcript in the following formats:

-   **TXT**: A plain text file with timestamps and speaker labels.
-   **JSON**: A structured JSON file with the transcript and metadata.
-   **SRT**: A SubRip subtitle file.
-   **DOCX**: A Microsoft Word document.
