"""
CLI commands for running individual pipeline stages.

Allows testing each stage independently:
- Stage 1: Transcribe & Diarize
- Stage 2: Identify Speakers with AI
- Stage 3: Apply Names & Create Final Files
"""
from __future__ import annotations

import click
from rich.console import Console
from dotenv import load_dotenv

from .pipeline_stages import (
    stage1_transcribe_and_diarize,
    stage2_identify_speakers,
    stage3_apply_speaker_names,
)

load_dotenv()
console = Console()


@click.group(help="Pipeline Stages CLI - Run individual stages for testing")
def stages_cli():
    """CLI for running individual pipeline stages."""
    pass


@stages_cli.command("stage1", help="Stage 1: Transcribe audio and perform speaker diarization")
@click.option("-i", "--input", "input_path", required=True, type=click.Path(exists=True), help="Audio file path")
@click.option("-o", "--output-dir", required=True, type=click.Path(file_okay=False), help="Output directory")
@click.option("--hf-token", default=None, help="Hugging Face token")
@click.option("--model", default="whisper-1", help="Whisper model")
@click.option("--api-key", default=None, help="OpenAI API key")
@click.option("--language", default=None, help="Audio language")
@click.option("--temperature", default=0.0, type=float, help="Whisper temperature")
def run_stage1(input_path, output_dir, hf_token, model, api_key, language, temperature):
    """Run Stage 1: Transcription + Diarization"""
    console.print("[bold cyan]Stage 1: Transcribe & Diarize[/bold cyan]\n")
    
    try:
        output_file = stage1_transcribe_and_diarize(
            audio_path=input_path,
            output_dir=output_dir,
            hf_token=hf_token,
            whisper_model=model,
            api_key=api_key,
            language=language,
            temperature=temperature,
        )
        console.print(f"\n[green]✓ Stage 1 Complete![/green]")
        console.print(f"[green]Intermediate file:[/green] {output_file}")
        console.print(f"\n[yellow]Next step:[/yellow] Run stage2 with: --input {output_file}")
    except Exception as e:
        console.print(f"[red]✗ Stage 1 Failed:[/red] {e}")
        raise click.ClickException(str(e))


@stages_cli.command("stage2", help="Stage 2: Identify speakers with AI")
@click.option("-i", "--input", "input_path", required=True, type=click.Path(exists=True), help="Stage 1 intermediate file (_stage1_transcript.json)")
@click.option("-o", "--output-dir", required=True, type=click.Path(file_okay=False), help="Output directory")
@click.option("--speaker-context", default=None, help="Meeting context (e.g., '1-on-1 interview')")
@click.option("--ai-model", type=click.Choice(["gpt-4o", "gemini-2.0-flash"]), default="gpt-4o", help="AI model")
@click.option("--api-key", default=None, help="OpenAI/Google API key")
def run_stage2(input_path, output_dir, speaker_context, ai_model, api_key):
    """Run Stage 2: AI Speaker Identification"""
    console.print("[bold cyan]Stage 2: Identify Speakers with AI[/bold cyan]\n")
    
    try:
        output_file = stage2_identify_speakers(
            intermediate_file=input_path,
            output_dir=output_dir,
            speaker_context=speaker_context,
            ai_model=ai_model,
            api_key=api_key,
        )
        console.print(f"\n[green]✓ Stage 2 Complete![/green]")
        console.print(f"[green]Speaker mappings:[/green] {output_file}")
        console.print(f"\n[yellow]Next step:[/yellow] Run stage3 with:")
        console.print(f"  --transcript {input_path}")
        console.print(f"  --mappings {output_file}")
    except Exception as e:
        console.print(f"[red]✗ Stage 2 Failed:[/red] {e}")
        raise click.ClickException(str(e))


@stages_cli.command("stage3", help="Stage 3: Apply speaker names and create final files")
@click.option("--transcript", "transcript_file", required=True, type=click.Path(exists=True), help="Stage 1 transcript file")
@click.option("--mappings", "mapping_file", default=None, type=click.Path(exists=True), help="Stage 2 mapping file (optional)")
@click.option("-o", "--output-dir", required=True, type=click.Path(file_okay=False), help="Output directory")
@click.option("--formats", multiple=True, type=click.Choice(["txt", "json", "srt", "docx"]), default=["txt", "json", "srt"], help="Output formats")
def run_stage3(transcript_file, mapping_file, output_dir, formats):
    """Run Stage 3: Apply Names & Create Final Files"""
    console.print("[bold cyan]Stage 3: Apply Names & Create Files[/bold cyan]\n")
    
    try:
        output_files = stage3_apply_speaker_names(
            intermediate_file=transcript_file,
            speaker_mapping_file=mapping_file,
            output_dir=output_dir,
            formats=list(formats),
        )
        console.print(f"\n[green]✓ Stage 3 Complete![/green]")
        console.print(f"[green]Created {len(output_files)} files in:[/green] {output_dir}")
    except Exception as e:
        console.print(f"[red]✗ Stage 3 Failed:[/red] {e}")
        raise click.ClickException(str(e))


@stages_cli.command("list-intermediate", help="List intermediate files in a directory")
@click.option("-d", "--directory", required=True, type=click.Path(exists=True), help="Directory to scan")
def list_intermediate(directory):
    """List all intermediate files."""
    import os
    from pathlib import Path
    
    console.print(f"[bold cyan]Intermediate Files in:[/bold cyan] {directory}\n")
    
    stage1_files = list(Path(directory).glob("*_stage1_transcript.json"))
    stage2_files = list(Path(directory).glob("*_stage2_speaker_mappings.json"))
    
    if stage1_files:
        console.print("[yellow]Stage 1 Transcripts:[/yellow]")
        for f in stage1_files:
            console.print(f"  • {f.name}")
    
    if stage2_files:
        console.print("\n[yellow]Stage 2 Speaker Mappings:[/yellow]")
        for f in stage2_files:
            console.print(f"  • {f.name}")
    
    if not stage1_files and not stage2_files:
        console.print("[dim]No intermediate files found[/dim]")


if __name__ == "__main__":
    stages_cli()

