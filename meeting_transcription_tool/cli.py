from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional, List

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from .utils import validate_audio_file, bytes_to_readable
from .transcriber import transcribe_with_whisper
from .exporters import export_txt, export_json, export_srt, export_docx


console = Console()


def _default_base_name(input_path: str) -> str:
	name = os.path.basename(input_path)
	return os.path.splitext(name)[0]


@click.group(help="Meeting Transcription Tool CLI")
def cli() -> None:
	pass


@cli.command("transcribe", help="Transcribe an audio file with Whisper and export outputs.")
@click.option("-i", "--input", "input_path", required=True, type=click.Path(exists=True, dir_okay=False, readable=True), help="Path to audio file (MP3, WAV, M4A, FLAC).")
@click.option("-o", "--output-dir", default="outputs", show_default=True, type=click.Path(file_okay=False), help="Directory to write outputs.")
@click.option("--api-key", default=None, help="OpenAI API Key (overrides OPENAI_API_KEY env var).")
@click.option("--model", default="whisper-1", show_default=True, help="OpenAI model for transcription.")
@click.option("--formats", multiple=True, type=click.Choice(["txt", "json", "srt", "docx"]), default=["txt", "json", "srt"], show_default=True, help="Output formats to export.")
@click.option("--language", default=None, help="Hint language code (e.g., en).")
@click.option("--temperature", default=0.0, show_default=True, type=float, help="Sampling temperature for Whisper.")
def transcribe_cmd(
	input_path: str,
	output_dir: str,
	api_key: Optional[str],
	model: str,
	formats: List[str],
	language: Optional[str],
	temperature: float,
) -> None:
	ok, reason = validate_audio_file(input_path)
	if not ok:
		console.print(f"[red]Invalid input:[/red] {reason}")
		raise click.ClickException(reason)

	file_size = os.path.getsize(input_path)
	console.print(f"[bold]Input:[/bold] {input_path} ({bytes_to_readable(file_size)})")

	with Progress(
		SpinnerColumn(),
		TextColumn("[progress.description]{task.description}"),
		BarColumn(),
		TimeElapsedColumn(),
		transient=True,
		console=console,
	) as progress:
		task = progress.add_task("Uploading and transcribing with Whisper…", total=None)
		try:
			result = transcribe_with_whisper(
				audio_path=input_path,
				model=model,
				api_key=api_key,
				language=language,
				temperature=temperature,
			)
		except Exception as e:
			progress.stop()
			console.print(f"[red]Transcription failed:[/red] {e}")
			raise click.ClickException(str(e))
		finally:
			progress.stop()

	base_name = _default_base_name(input_path)
	written = []
	metadata = {
		"source_file": os.path.abspath(input_path),
		"model": model,
		"generated_at": datetime.utcnow().isoformat() + "Z",
	}

	if "txt" in formats:
		written.append(export_txt(result.segments, output_dir, base_name))
	if "json" in formats:
		written.append(export_json(result.segments, output_dir, base_name, metadata=metadata))
	if "srt" in formats:
		written.append(export_srt(result.segments, output_dir, base_name))
	if "docx" in formats:
		try:
			written.append(export_docx(result.segments, output_dir, base_name))
		except Exception as e:
			console.print(f"[yellow]DOCX export skipped:[/yellow] {e}")

	console.print("[green]Transcription complete![/green]")
	for path in written:
		console.print(f"  • {path}")


if __name__ == "__main__":
	cli()


