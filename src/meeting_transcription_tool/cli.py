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
import threading

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
    calculate_gemini_cost, calculate_gpt5mini_cost, estimate_tokens
)
from .context_extractor import extract_full_context, format_context_for_display

# Load environment variables from .env file
load_dotenv()


console = Console()
logger = logging.getLogger("meeting_transcription_tool.cli")
LOG_FORMAT = "%(asctime)s [%(threadName)s] %(levelname)s %(name)s:%(funcName)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_optimal_parallel_workers() -> int:
	"""
	Calculate optimal number of parallel workers based on CPU capacity.
	Uses ~50% of CPU cores for maximum parallelization without hanging.
	
	Returns:
		Number of workers (50% of CPU cores, minimum 1, maximum 16)
	"""
	try:
		cpu_count = multiprocessing.cpu_count()
		# Use 50% of CPU cores, rounded up
		optimal = max(1, min((cpu_count + 1) // 2, 16))
		logger.info(f"CPU cores: {cpu_count}, optimal parallel workers: {optimal} (50% utilization)")
		return optimal
	except Exception:
		# Fallback to 2 if CPU count detection fails
		logger.warning("CPU count detection failed, using 2 workers")
		return 2


def _default_base_name(input_path: str) -> str:
	name = os.path.basename(input_path)
	return os.path.splitext(name)[0]

 
@click.group(help="Meeting Transcription Tool CLI")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output except for errors.")
def cli(verbose: bool, quiet: bool) -> None:
	if verbose:
		logging.basicConfig(
			level=logging.DEBUG,
			format=LOG_FORMAT,
			datefmt=LOG_DATE_FORMAT,
			force=True,
		)
	elif quiet:
		logging.basicConfig(
			level=logging.CRITICAL,
			format=LOG_FORMAT,
			datefmt=LOG_DATE_FORMAT,
			force=True,
		)
		console.quiet = True
	else:
		logging.basicConfig(
			level=logging.INFO,
			format=LOG_FORMAT,
			datefmt=LOG_DATE_FORMAT,
			force=True,
		)


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
@click.option("--ai-model", type=click.Choice(["gpt-5-mini", "gpt-4o", "gemini-2.0-flash"]), default="gpt-5-mini", help="AI model for speaker identification.")
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
		cpu_count = multiprocessing.cpu_count()
		message = f"Auto-detected optimal parallel workers: {parallel} (CPU cores: {cpu_count})"
		logger.info(message)
		console.print(f"[dim]{message}[/dim]")
	else:
		logger.info("Using user-specified parallel workers: %s", parallel)
	
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
	max_workers = max(1, min(max_workers, len(audio_files)))
	logger.info(
		"Discovered %s audio files in '%s' (max_workers=%s, cpu_cores=%s)",
		len(audio_files),
		input_dir,
		max_workers,
		cpu_count,
	)
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
		thread_id = threading.current_thread().name
		logger.info("Dispatching file for processing: %s", audio_file.name)
		console.print(f"[cyan]{audio_file.name}[/cyan] -> queued on [dim]{thread_id}[/dim]")
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
			logger.info(
				"Completed file %s in %.2fs (thread=%s)",
				audio_file.name,
				metrics.total_time,
				thread_id,
			)
			return (audio_file.name, True, None, metrics)
		except Exception as e:
			logger.exception("Failed processing file %s on thread %s", audio_file.name, thread_id)
			return (audio_file.name, False, str(e), None)
	
	# Process files in parallel
	with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="TranscribeWorker") as executor:
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
	speaker_id_enabled = identify_speakers
	metrics.speaker_id_model = ai_model if speaker_id_enabled else "N/A"
	
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
		logger.error("Validation failed for %s: %s", input_path, reason)
		raise click.ClickException(reason)

	# If no output directory specified, use the same directory as the input file
	if output_dir is None:
		output_dir = os.path.dirname(os.path.abspath(input_path))
		console.print(f"[dim]Output directory not specified, using input file directory[/dim]")

	file_size = os.path.getsize(input_path)
	logger.info("Starting processing for %s (size=%s bytes, output_dir=%s)", input_path, file_size, output_dir)
	console.print(f"[bold]Input:[/bold] {input_path} ({bytes_to_readable(file_size)})")
	console.print(f"[bold]Output:[/bold] {output_dir}")
	
	# Extract and display context
	if not speaker_context and speaker_id_enabled:
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
				transcription_result = loop.run_until_complete(run_transcription_pipeline(
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
			metrics.speakers_detected = len(set(seg.speaker for seg in transcription_result.segments))
			metrics.speaker_segments = len(transcription_result.segments)
			metrics.transcript_segments = len(transcription_result.segments)
			metrics.total_words = sum(len(seg.text.split()) for seg in transcription_result.segments)
			
		except Exception as e:
			console.print(f"[red]Pipeline failed:[/red] {e}")
			metrics.errors.append(f"Pipeline failed: {str(e)}")
			logger.exception("Pipeline failure for %s", input_path)
			raise click.ClickException(str(e))

	# AI-powered speaker identification (optional)
	if speaker_id_enabled:
		console.print(f"\n[bold cyan]Identifying speakers with AI ({ai_model})...[/bold cyan]")
		try:
			speaker_id_start = time.time()
			from .speaker_identifier import (
				identify_speakers as identify_speakers_ai,
				apply_speaker_mappings,
				format_speaker_summary,
				format_segments_for_prompt,
			)
			
			# Build transcript text for analysis
			transcript_text = format_segments_for_prompt([
				{
					"speaker": seg.speaker,
					"start_ms": seg.start_ms,
					"end_ms": seg.end_ms,
					"text": seg.text,
				}
				for seg in transcription_result.segments
			])
			
			# Estimate tokens for cost calculation
			metrics.speaker_id_tokens_input = estimate_tokens(transcript_text)
			
			# Identify speakers - pass filename so AI can extract names from it
			speaker_result = identify_speakers_ai(
				transcript_text=transcript_text,
				num_speakers=len(set(seg.speaker for seg in transcription_result.segments)),
				participant_names=None,  # Let AI figure out names from context and filename
				participant_context=speaker_context,
				filename=input_path,  # Pass filename so AI can extract names from it
				api_key=api_key,
				model=ai_model,
			)
			mappings = speaker_result.mappings
			
			speaker_id_end = time.time()
			metrics.speaker_identification_time = speaker_id_end - speaker_id_start
			metrics.speaker_id_api_calls = 1
			if speaker_result.request_metadata:
				metrics.speaker_id_request_preview = speaker_result.request_metadata.get("user_prompt_preview", "")
			if speaker_result.audio_file_id:
				metrics.speaker_id_audio_file_id = speaker_result.audio_file_id
			
			if speaker_result.request_metadata:
				console.print("\n[dim]AI speaker-label request metadata:[/dim]")
				console.print(json.dumps(speaker_result.request_metadata, indent=2))
			if speaker_result.response_metadata:
				console.print("[dim]AI speaker-label response metadata:[/dim]")
				console.print(json.dumps(speaker_result.response_metadata, indent=2))
			if speaker_result.audio_file_id:
				console.print(f"[dim]AI audio upload:[/dim] file_id={speaker_result.audio_file_id} "
				              f"bytes={speaker_result.audio_upload_bytes:,}")
			
			# Estimate output tokens (typically smaller than input)
			metrics.speaker_id_tokens_output = 200  # Typical JSON response size
			
			# Apply mappings
			if mappings:
				apply_speaker_mappings(transcription_result.segments, mappings)
				metrics.speaker_mappings = mappings
				console.print(f"\n[green]{format_speaker_summary(mappings)}[/green]")
			else:
				console.print("[yellow]Could not identify speakers, using generic labels[/yellow]")
				metrics.warnings.append("Speaker identification returned no mappings")
				logger.warning("Speaker identification returned no mappings for %s", input_path)
		except Exception as e:
			console.print(f"[yellow]Speaker identification failed: {e}[/yellow]")
			console.print("[yellow]Continuing with generic speaker labels[/yellow]")
			metrics.warnings.append(f"Speaker identification failed: {str(e)}")
			logger.exception("Speaker identification failed for %s", input_path)

	base_name = _default_base_name(input_path)
	written = []
	metadata = {
		"source_file": os.path.abspath(input_path),
		"model": model,
		"generated_at": datetime.utcnow().isoformat() + "Z",
		"speaker_identification": speaker_id_enabled,
	}

	export_start = time.time()
	if "txt" in formats:
		written.append(export_txt(transcription_result.segments, output_dir, base_name))
		# If speaker identification was done, also create _speakers.txt file
		if speaker_id_enabled and metrics.speaker_mappings:
			written.append(export_txt_with_speakers(transcription_result.segments, output_dir, base_name))
	if "json" in formats:
		written.append(export_json(transcription_result.segments, output_dir, base_name, metadata=metadata))
	if "srt" in formats:
		written.append(export_srt(transcription_result.segments, output_dir, base_name))
	if "docx" in formats:
		try:
			written.append(export_docx(transcription_result.segments, output_dir, base_name))
		except Exception as e:
			console.print(f"[yellow]DOCX export skipped:[/yellow] {e}")
			metrics.warnings.append(f"DOCX export failed: {str(e)}")
			logger.warning("DOCX export failed for %s: %s", input_path, e)
	export_end = time.time()
	
	metrics.export_time = export_end - export_start
	logger.info(
		"Finished exports for %s (written=%s)",
		input_path,
		", ".join(os.path.basename(f) for f in written),
	)
	metrics.output_files = [os.path.basename(f) for f in written]
	metrics.output_directory = output_dir
	
	# Calculate costs
	metrics.whisper_audio_minutes = metrics.audio_duration_seconds / 60.0 if metrics.audio_duration_seconds > 0 else 0
	metrics.whisper_cost_usd = calculate_whisper_cost(metrics.whisper_audio_minutes)
	
	if metrics.speaker_id_enabled and metrics.speaker_id_api_calls > 0:
		if ai_model == "gpt-5-mini":
			metrics.speaker_id_cost_usd = calculate_gpt5mini_cost(
				metrics.speaker_id_tokens_input,
				metrics.speaker_id_tokens_output
			)
		elif ai_model == "gpt-4o":
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
	logger.info(
		"Completed processing for %s (total_time=%.2fs, total_cost=$%.4f)",
		input_path,
		metrics.total_time,
		metrics.total_cost_usd,
	)

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
