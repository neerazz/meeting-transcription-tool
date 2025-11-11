from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Optional, List
import asyncio
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from dotenv import load_dotenv

from .audio_processor import validate_audio_file, bytes_to_readable, get_audio_duration
from .transcriber import run_transcription_pipeline
from .exporter import export_txt, export_txt_with_speakers, export_json, export_srt, export_docx
from .summary_report import (
    ProcessingMetrics, generate_summary_report, save_summary_report,
    save_batch_summary_report, calculate_whisper_cost, calculate_gpt4o_cost, 
    calculate_gemini_cost, estimate_tokens
)
from .context_extractor import extract_full_context, format_context_for_display

# Load environment variables from .env file
load_dotenv()


console = Console()


def _get_optimal_parallel_workers() -> int:
	"""
	Calculate optimal number of parallel workers based on CPU capacity.
	
	Returns:
		Number of workers (CPU count - 1, minimum 1, maximum 8)
	"""
	try:
		cpu_count = multiprocessing.cpu_count()
		# Use CPU count - 1 to leave one core free for system tasks
		# Cap at 8 to avoid overwhelming the system with too many threads
		optimal = max(1, min(cpu_count - 1, 8))
		return optimal
	except Exception:
		# Fallback to 3 if CPU count detection fails
		return 3


def _default_base_name(input_path: str) -> str:
	name = os.path.basename(input_path)
	return os.path.splitext(name)[0]


@click.group(help="Meeting Transcription Tool CLI")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output except for errors.")
def cli(verbose: bool, quiet: bool) -> None:
	if verbose:
		logging.basicConfig(level=logging.DEBUG)
	elif quiet:
		logging.basicConfig(level=logging.CRITICAL)
		console.quiet = True
	else:
		logging.basicConfig(level=logging.INFO)


@cli.command("transcribe", help="Transcribe audio file(s) with Whisper and export outputs.")
@click.option("-i", "--input", "input_path", required=True, type=click.Path(exists=True, readable=True), help="Path to audio file OR directory for batch processing.")
@click.option("-o", "--output-dir", default=None, type=click.Path(file_okay=False), help="Directory to write outputs. Defaults to same directory as input file.")
@click.option("--api-key", default=None, help="OpenAI API Key (overrides OPENAI_API_KEY env var).")
@click.option("--hf-token", default=None, help="Hugging Face API Token (overrides HUGGING_FACE_TOKEN env var).")
@click.option("--model", default="whisper-1", show_default=True, help="OpenAI model for transcription.")
@click.option("--formats", multiple=True, type=click.Choice(["txt", "json", "srt", "docx"]), default=["txt", "json", "srt"], show_default=True, help="Output formats to export.")
@click.option("--language", default=None, help="Hint language code (e.g., en).")
@click.option("--temperature", default=0.0, show_default=True, type=float, help="Sampling temperature for Whisper.")
@click.option("--identify-speakers/--no-identify-speakers", default=True, help="Use AI to identify speakers by their actual names. Enabled by default.")
@click.option("--speaker-context", default=None, help="Context about the meeting/participants (e.g., '1-on-1 interview'). If not provided, will extract from filename.")
@click.option("--ai-model", type=click.Choice(["gpt-4o", "gemini-2.0-flash"]), default="gpt-4o", help="AI model for speaker identification.")
@click.option("--file-filter", default="*.m4a", help="File pattern for batch processing (e.g., '*.m4a', '*.mp3'). Only used when input is a directory.")
@click.option("--overwrite", is_flag=True, default=True, help="Overwrite existing output files.")
@click.option("--parallel", "-p", default=None, type=int, help="Number of files to process in parallel for batch mode. Default: Auto-detected based on CPU cores (CPU count - 1)")
def transcribe_cmd(
	input_path: str,
	output_dir: Optional[str],
	api_key: Optional[str],
	hf_token: Optional[str],
	model: str,
	formats: List[str],
	language: Optional[str],
	temperature: float,
	identify_speakers: bool,
	speaker_context: Optional[str],
	ai_model: str,
	file_filter: str,
	overwrite: bool,
	parallel: Optional[int],
) -> None:
	"""Main transcribe command that handles both single files and batch processing."""
	
	# Auto-detect optimal parallel workers if not specified
	if parallel is None:
		parallel = _get_optimal_parallel_workers()
		console.print(f"[dim]Auto-detected optimal parallel workers: {parallel} (CPU cores: {multiprocessing.cpu_count()})[/dim]")
	
	# Check if input is directory or file
	input_path_obj = Path(input_path)
	
	if input_path_obj.is_dir():
		# Batch processing
		_batch_transcribe(
			input_dir=input_path,
			output_dir=output_dir,
			api_key=api_key,
			hf_token=hf_token,
			model=model,
			formats=list(formats),
			language=language,
			temperature=temperature,
			identify_speakers=identify_speakers,
			speaker_context=speaker_context,
			ai_model=ai_model,
			file_filter=file_filter,
			overwrite=overwrite,
			max_workers=parallel,
		)
	else:
		# Single file processing
		_process_single_file(
			input_path=input_path,
			output_dir=output_dir,
			api_key=api_key,
			hf_token=hf_token,
			model=model,
			formats=list(formats),
			language=language,
			temperature=temperature,
			identify_speakers=identify_speakers,
			speaker_context=speaker_context,
			ai_model=ai_model,
			overwrite=overwrite,
		)


def _batch_transcribe(
	input_dir: str,
	output_dir: Optional[str],
	api_key: Optional[str],
	hf_token: Optional[str],
	model: str,
	formats: List[str],
	language: Optional[str],
	temperature: float,
	identify_speakers: bool,
	speaker_context: Optional[str],
	ai_model: str,
	file_filter: str,
	overwrite: bool,
	max_workers: int,
) -> None:
	"""Process all matching files in a directory with parallel execution."""
	
	input_dir_path = Path(input_dir)
	audio_files = list(input_dir_path.glob(file_filter))
	
	if not audio_files:
		console.print(f"[yellow]No files matching '{file_filter}' found in {input_dir}[/yellow]")
		return
	
	cpu_count = multiprocessing.cpu_count()
	console.print(f"[bold cyan]Batch Processing Mode (Parallel)[/bold cyan]")
	console.print(f"Found {len(audio_files)} file(s) matching '{file_filter}'")
	console.print(f"Processing {max_workers} files in parallel (CPU cores: {cpu_count})")
	console.print(f"Directory: {input_dir}\n")
	
	success_count = 0
	failed_files = []
	completed = 0
	
	all_metrics = []  # Collect metrics from all files
	
	def process_file(audio_file: Path) -> tuple[str, bool, Optional[str], Optional[ProcessingMetrics]]:
		"""Process a single file and return results."""
		import threading
		thread_id = threading.current_thread().name
		console.print(f"[cyan][{thread_id}] Starting: {audio_file.name}[/cyan]")
		try:
			metrics = _process_single_file(
				input_path=str(audio_file),
				output_dir=output_dir,
				api_key=api_key,
				hf_token=hf_token,
				model=model,
				formats=formats,
				language=language,
				temperature=temperature,
				identify_speakers=identify_speakers,
				speaker_context=speaker_context,
				ai_model=ai_model,
				overwrite=overwrite,
				return_metrics=True,
			)
			return (audio_file.name, True, None, metrics)
		except Exception as e:
			console.print(f"[red][{thread_id}] Failed: {audio_file.name} - {e}[/red]")
			return (audio_file.name, False, str(e), None)
	
	# Process files in parallel
	with ThreadPoolExecutor(max_workers=max_workers) as executor:
		# Submit all tasks
		future_to_file = {executor.submit(process_file, audio_file): audio_file for audio_file in audio_files}
		
		# Process completed tasks
		for future in as_completed(future_to_file):
			audio_file = future_to_file[future]
			completed += 1
			
			try:
				filename, success, error, metrics = future.result()
				if success and metrics:
					all_metrics.append(metrics)
					success_count += 1
					console.print(f"[green]✓ [{completed}/{len(audio_files)}] {filename} - Complete[/green]")
				else:
					failed_files.append(filename)
					console.print(f"[red]✗ [{completed}/{len(audio_files)}] {filename} - Failed: {error}[/red]")
			except Exception as e:
				failed_files.append(audio_file.name)
				console.print(f"[red]✗ [{completed}/{len(audio_files)}] {audio_file.name} - Error: {e}[/red]")
	
	# Batch summary
	console.print(f"\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
	console.print(f"[bold]Batch Processing Complete[/bold]")
	console.print(f"  ✓ Successful: {success_count}/{len(audio_files)}")
	if failed_files:
		console.print(f"  ✗ Failed: {len(failed_files)}")
		for filename in failed_files:
			console.print(f"    • {filename}")
	
	# Generate and save consolidated batch summary
	if all_metrics:
		batch_output_dir = output_dir if output_dir else input_dir
		summary_file = save_batch_summary_report(all_metrics, batch_output_dir)
		console.print(f"\n[green]✓ Batch summary saved:[/green] {os.path.basename(summary_file)}")


def _process_single_file(
	input_path: str,
	output_dir: Optional[str],
	api_key: Optional[str],
	hf_token: Optional[str],
	model: str,
	formats: List[str],
	language: Optional[str],
	temperature: float,
	identify_speakers: bool,
	speaker_context: Optional[str],
	ai_model: str,
	overwrite: bool,
	return_metrics: bool = False,
) -> Optional[ProcessingMetrics]:
	"""Process a single audio file."""
	
	# Initialize metrics tracking
	metrics = ProcessingMetrics()
	metrics.start_time = time.time()
	metrics.input_file = os.path.basename(input_path)
	metrics.transcription_model = model
	metrics.speaker_id_enabled = identify_speakers
	metrics.speaker_id_model = ai_model if identify_speakers else "N/A"
	
	# Get file info
	try:
		metrics.file_size_bytes = os.path.getsize(input_path)
		metrics.audio_format = os.path.splitext(input_path)[1][1:].upper()
		metrics.audio_duration_seconds = get_audio_duration(input_path)
	except Exception:
		pass
	
	ok, reason = validate_audio_file(input_path)
	if not ok:
		console.print(f"[red]Invalid input:[/red] {reason}")
		raise click.ClickException(reason)

	# If no output directory specified, use the same directory as the input file
	if output_dir is None:
		output_dir = os.path.dirname(os.path.abspath(input_path))
		console.print(f"[dim]Output directory not specified, using input file directory[/dim]")

	file_size = os.path.getsize(input_path)
	console.print(f"[bold]Input:[/bold] {input_path} ({bytes_to_readable(file_size)})")
	console.print(f"[bold]Output:[/bold] {output_dir}")
	
	# Extract and display context
	if not speaker_context and identify_speakers:
		speaker_context = extract_full_context(input_path)
		console.print(f"\n{format_context_for_display(input_path)}")

	with Progress(
		SpinnerColumn(),
		TextColumn("[progress.description]{task.description}"),
		TimeElapsedColumn(),
		transient=True,
		console=console,
	) as progress:
		progress.add_task("Running transcription pipeline...", total=None)
		try:
			pipeline_start = time.time()
			whisper_kwargs = {
				"model": model,
				"api_key": api_key,
				"language": language,
				"temperature": temperature,
			}
			# Use thread-safe async execution for parallel processing
			# Each thread needs its own event loop to avoid conflicts
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)
			try:
				result = loop.run_until_complete(run_transcription_pipeline(
					audio_path=input_path,
					hf_token=hf_token,
					**whisper_kwargs
				))
			finally:
				loop.close()
			pipeline_end = time.time()
			
			# Track timing (approximate split)
			total_pipeline_time = pipeline_end - pipeline_start
			metrics.diarization_time = total_pipeline_time * 0.6  # ~60% is diarization
			metrics.transcription_time = total_pipeline_time * 0.4  # ~40% is transcription
			
			# Track results
			metrics.speakers_detected = len(set(seg.speaker for seg in result.segments))
			metrics.speaker_segments = len(result.segments)
			metrics.transcript_segments = len(result.segments)
			metrics.total_words = sum(len(seg.text.split()) for seg in result.segments)
			
		except Exception as e:
			console.print(f"[red]Pipeline failed:[/red] {e}")
			metrics.errors.append(f"Pipeline failed: {str(e)}")
			raise click.ClickException(str(e))

	# AI-powered speaker identification (optional)
	if identify_speakers:
		console.print(f"\n[bold cyan]Identifying speakers with AI ({ai_model})...[/bold cyan]")
		try:
			speaker_id_start = time.time()
			from .speaker_identifier import identify_speakers, apply_speaker_mappings, format_speaker_summary
			
			# Build transcript text for analysis
			transcript_text = "\n\n".join([
				f"[{seg.speaker}]\n{seg.text}" for seg in result.segments
			])
			
			# Estimate tokens for cost calculation
			metrics.speaker_id_tokens_input = estimate_tokens(transcript_text)
			
			# Identify speakers - pass filename so AI can extract names from it
			mappings = identify_speakers(
				transcript_text=transcript_text,
				num_speakers=len(set(seg.speaker for seg in result.segments)),
				participant_names=None,  # Let AI figure out names from context and filename
				participant_context=speaker_context,
				filename=input_path,  # Pass filename so AI can extract names from it
				api_key=api_key,
				model=ai_model,
			)
			
			speaker_id_end = time.time()
			metrics.speaker_identification_time = speaker_id_end - speaker_id_start
			metrics.speaker_id_api_calls = 1
			
			# Estimate output tokens (typically smaller than input)
			metrics.speaker_id_tokens_output = 200  # Typical JSON response size
			
			# Apply mappings
			if mappings:
				apply_speaker_mappings(result.segments, mappings)
				metrics.speaker_mappings = mappings
				console.print(f"\n[green]{format_speaker_summary(mappings)}[/green]")
			else:
				console.print("[yellow]Could not identify speakers, using generic labels[/yellow]")
				metrics.warnings.append("Speaker identification returned no mappings")
		except Exception as e:
			console.print(f"[yellow]Speaker identification failed: {e}[/yellow]")
			console.print("[yellow]Continuing with generic speaker labels[/yellow]")
			metrics.warnings.append(f"Speaker identification failed: {str(e)}")

	base_name = _default_base_name(input_path)
	written = []
	metadata = {
		"source_file": os.path.abspath(input_path),
		"model": model,
		"generated_at": datetime.utcnow().isoformat() + "Z",
		"speaker_identification": identify_speakers,
	}

	export_start = time.time()
	if "txt" in formats:
		written.append(export_txt(result.segments, output_dir, base_name))
		# If speaker identification was done, also create _speakers.txt file
		if identify_speakers and metrics.speaker_mappings:
			written.append(export_txt_with_speakers(result.segments, output_dir, base_name))
	if "json" in formats:
		written.append(export_json(result.segments, output_dir, base_name, metadata=metadata))
	if "srt" in formats:
		written.append(export_srt(result.segments, output_dir, base_name))
	if "docx" in formats:
		try:
			written.append(export_docx(result.segments, output_dir, base_name))
		except Exception as e:
			console.print(f"[yellow]DOCX export skipped:[/yellow] {e}")
			metrics.warnings.append(f"DOCX export failed: {str(e)}")
	export_end = time.time()
	
	metrics.export_time = export_end - export_start
	metrics.output_files = [os.path.basename(f) for f in written]
	metrics.output_directory = output_dir
	
	# Calculate costs
	metrics.whisper_audio_minutes = metrics.audio_duration_seconds / 60.0 if metrics.audio_duration_seconds > 0 else 0
	metrics.whisper_cost_usd = calculate_whisper_cost(metrics.whisper_audio_minutes)
	
	if metrics.speaker_id_enabled and metrics.speaker_id_api_calls > 0:
		if ai_model == "gpt-4o":
			metrics.speaker_id_cost_usd = calculate_gpt4o_cost(
				metrics.speaker_id_tokens_input,
				metrics.speaker_id_tokens_output
			)
		elif ai_model == "gemini-2.0-flash":
			metrics.speaker_id_cost_usd = calculate_gemini_cost(
				metrics.speaker_id_tokens_input,
				metrics.speaker_id_tokens_output
			)
	
	metrics.total_cost_usd = metrics.whisper_cost_usd + metrics.speaker_id_cost_usd
	metrics.total_time = time.time() - metrics.start_time

	console.print("[green]Transcription complete![/green]")
	for path in written:
		console.print(f"  • {os.path.basename(path)}")
	
	# Only show detailed summary and save for single file mode (not batch)
	if not return_metrics:
		console.print("\n[bold cyan]Summary Report:[/bold cyan]")
		summary_report = generate_summary_report(metrics)
		print(summary_report)
		
		# Save individual summary file only for single file mode
		summary_file = os.path.join(output_dir, f"{base_name}_SUMMARY.txt")
		save_summary_report(metrics, summary_file)
		console.print(f"[green]✓ Summary saved:[/green] {os.path.basename(summary_file)}")
	
	# Return metrics for batch processing
	if return_metrics:
		return metrics
	return None


if __name__ == "__main__":
	cli()
