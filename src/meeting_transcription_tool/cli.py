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

	# Use pipeline_stages module with caching support
	from .pipeline_stages import (
		stage1_transcribe_and_diarize,
		stage2_identify_speakers,
		stage3_apply_speaker_names,
		IntermediateTranscript,
	)
	from .exporter import TranscriptSegment
	
	try:
		# Stage 1: Transcribe and Diarize (with caching)
		with Progress(
			SpinnerColumn(),
			TextColumn("[progress.description]{task.description}"),
			TimeElapsedColumn(),
			transient=True,
			console=console,
		) as progress:
			progress.add_task("Stage 1: Transcribing and diarizing...", total=None)
			pipeline_start = time.time()
			
			stage1_file = stage1_transcribe_and_diarize(
				audio_path=input_path,
				output_dir=output_dir,
				hf_token=hf_token,
				whisper_model=model,
				api_key=api_key,
				language=language,
				temperature=temperature,
				use_cache=True,  # Enable caching
			)
			
			pipeline_end = time.time()
			metrics.diarization_time = (pipeline_end - pipeline_start) * 0.6
			metrics.transcription_time = (pipeline_end - pipeline_start) * 0.4
		
		# Load intermediate transcript for metrics
		intermediate = IntermediateTranscript.load(stage1_file)
		transcription_result_segments = [
			TranscriptSegment(
				start_ms=seg['start_ms'],
				end_ms=seg['end_ms'],
				text=seg['text'],
				speaker=seg['speaker']
			)
			for seg in intermediate.segments
		]
		
		metrics.speakers_detected = intermediate.metadata.get('speakers_detected', 0)
		metrics.speaker_segments = len(intermediate.segments)
		metrics.transcript_segments = len(intermediate.segments)
		metrics.total_words = sum(len(seg['text'].split()) for seg in intermediate.segments)
		
		# Stage 2: AI Speaker Identification (with caching)
		mappings = {}
		if speaker_id_enabled:
			console.print(f"\n[bold cyan]Stage 2: Identifying speakers with AI ({ai_model})...[/bold cyan]")
			try:
				speaker_id_start = time.time()
				
				stage2_file = stage2_identify_speakers(
					intermediate_file=stage1_file,
					output_dir=output_dir,
					speaker_context=speaker_context,
					ai_model=ai_model,
					api_key=api_key,
					use_cache=True,  # Enable caching
				)
				
				# Load mappings
				with open(stage2_file, 'r', encoding='utf-8') as f:
					mapping_data = json.load(f)
				mappings = mapping_data.get('mappings', {})
				
				speaker_id_end = time.time()
				metrics.speaker_identification_time = speaker_id_end - speaker_id_start
				metrics.speaker_id_api_calls = 1
				metrics.speaker_mappings = mappings
				
				# Extract metadata for display
				if mapping_data.get('ai_request_metadata'):
					metrics.speaker_id_request_preview = mapping_data['ai_request_metadata'].get("user_prompt_preview", "")
					console.print("\n[dim]AI speaker-label request metadata:[/dim]")
					console.print(json.dumps(mapping_data['ai_request_metadata'], indent=2))
				if mapping_data.get('ai_response_metadata'):
					console.print("[dim]AI speaker-label response metadata:[/dim]")
					console.print(json.dumps(mapping_data['ai_response_metadata'], indent=2))
				if mapping_data.get('ai_audio_file_id'):
					metrics.speaker_id_audio_file_id = mapping_data['ai_audio_file_id']
					console.print(f"[dim]AI audio upload:[/dim] file_id={mapping_data['ai_audio_file_id']} "
					              f"bytes={mapping_data.get('ai_audio_bytes_uploaded', 0):,}")
				
				# Estimate tokens (rough calculation)
				from .speaker_identifier import format_segments_for_prompt
				transcript_text = format_segments_for_prompt(intermediate.segments)
				metrics.speaker_id_tokens_input = estimate_tokens(transcript_text)
				metrics.speaker_id_tokens_output = 200  # Typical JSON response size
				
				# Apply mappings to segments
				from .speaker_identifier import apply_speaker_mappings
				apply_speaker_mappings(transcription_result_segments, mappings)
				
				if mappings:
					from .speaker_identifier import format_speaker_summary
					console.print(f"\n[green]{format_speaker_summary(mappings)}[/green]")
				else:
					console.print("[yellow]Could not identify speakers, using generic labels[/yellow]")
					metrics.warnings.append("Speaker identification returned no mappings")
			except Exception as e:
				console.print(f"[yellow]Speaker identification failed: {e}[/yellow]")
				console.print("[yellow]Continuing with generic speaker labels[/yellow]")
				metrics.warnings.append(f"Speaker identification failed: {str(e)}")
				logger.exception("Speaker identification failed for %s", input_path)
		
		# Stage 3: Export files
		stage2_file_path = None
		if speaker_id_enabled and mappings:
			base_name = _default_base_name(input_path)
			stage2_file_path = os.path.join(output_dir, f"{base_name}_stage2_speaker_mappings.json")
			if not os.path.exists(stage2_file_path):
				stage2_file_path = None
		
		written = stage3_apply_speaker_names(
			intermediate_file=stage1_file,
			speaker_mapping_file=stage2_file_path,
			output_dir=output_dir,
			formats=list(formats),
		)
		
		# Update transcription_result for compatibility with rest of code
		transcription_result = type('obj', (object,), {
			'segments': transcription_result_segments,
			'text': ' '.join(seg.text for seg in transcription_result_segments)
		})
		
	except Exception as e:
		console.print(f"[red]Pipeline failed:[/red] {e}")
		metrics.errors.append(f"Pipeline failed: {str(e)}")
		logger.exception("Pipeline failure for %s", input_path)
		raise click.ClickException(str(e))

	# Files are already written by stage3, just collect the paths
	base_name = _default_base_name(input_path)
	metrics.output_files = [os.path.basename(f) for f in written]
	metrics.output_directory = output_dir
	metrics.export_time = 0.1  # Stage 3 handles export, minimal time here
	logger.info(
		"Finished exports for %s (written=%s)",
		input_path,
		", ".join(os.path.basename(f) for f in written),
	)
	
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
		console.print(f"  - {os.path.basename(path)}")
	
	# Only show detailed summary and save for single file mode (not batch)
	if not return_metrics:
		console.print("\n[bold cyan]Summary Report:[/bold cyan]")
		summary_report = generate_summary_report(metrics)
		# Use console.print which handles Unicode better, or encode safely
		try:
			console.print(summary_report)
		except UnicodeEncodeError:
			# Fallback: print with safe encoding
			print(summary_report.encode('ascii', 'replace').decode('ascii'))
		
		# Save individual summary file only for single file mode
		summary_file = os.path.join(output_dir, f"{base_name}_SUMMARY.txt")
		save_summary_report(metrics, summary_file)
		try:
			console.print(f"[green]Summary saved:[/green] {os.path.basename(summary_file)}")
		except UnicodeEncodeError:
			print(f"[SUCCESS] Summary saved: {os.path.basename(summary_file)}")
	
	# Return metrics for batch processing
	if return_metrics:
		return metrics
	return None


if __name__ == "__main__":
	cli()
