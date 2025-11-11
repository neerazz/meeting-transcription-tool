#!/usr/bin/env python3
"""
Process all stage1 transcript files in a directory through stage 2 (speaker identification).
This script processes files in parallel with timeout protection.
"""
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from meeting_transcription_tool.pipeline_stages import stage2_identify_speakers

console = Console()


def process_stage2_file(stage1_file: Path, output_dir: str, ai_model: str, api_key: str, timeout: int = 300):
    """Process a single stage1 file through stage2 with timeout."""
    try:
        console.print(f"[cyan]Processing:[/cyan] {stage1_file.name}")
        result = stage2_identify_speakers(
            intermediate_file=str(stage1_file),
            output_dir=output_dir,
            speaker_context=None,
            ai_model=ai_model,
            api_key=api_key,
        )
        console.print(f"[green]✓ Completed:[/green] {stage1_file.name}")
        return {"file": stage1_file.name, "status": "success", "output": result}
    except Exception as e:
        console.print(f"[red]✗ Failed:[/red] {stage1_file.name} - {str(e)}")
        return {"file": stage1_file.name, "status": "error", "error": str(e)}


@click.command()
@click.option("-d", "--directory", required=True, type=click.Path(exists=True, file_okay=False), 
              help="Directory containing stage1 transcript files")
@click.option("-o", "--output-dir", required=True, type=click.Path(file_okay=False), 
              help="Output directory for stage2 mappings")
@click.option("--ai-model", type=click.Choice(["gpt-5-mini", "gpt-4o", "gemini-2.0-flash"]), 
              default="gpt-5-mini", help="AI model for speaker identification")
@click.option("--api-key", default=None, help="OpenAI/Google API key")
@click.option("--parallel", "-p", default=3, type=int, help="Number of parallel workers (default: 3)")
@click.option("--timeout", default=300, type=int, help="Timeout per file in seconds (default: 300)")
def main(directory, output_dir, ai_model, api_key, parallel, timeout):
    """Process all stage1 transcript files in a directory through stage2."""
    
    directory = Path(directory)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all stage1 transcript files
    stage1_files = list(directory.glob("*_stage1_transcript.json"))
    
    if not stage1_files:
        console.print(f"[yellow]No stage1 transcript files found in {directory}[/yellow]")
        return
    
    console.print(f"[bold]Found {len(stage1_files)} stage1 transcript files[/bold]")
    console.print(f"[bold]Output directory:[/bold] {output_dir}")
    console.print(f"[bold]AI Model:[/bold] {ai_model}")
    console.print(f"[bold]Parallel workers:[/bold] {parallel}")
    console.print(f"[bold]Timeout per file:[/bold] {timeout}s\n")
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing files...", total=len(stage1_files))
        
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            # Submit all tasks
            futures = {
                executor.submit(process_stage2_file, f, str(output_dir), ai_model, api_key, timeout): f
                for f in stage1_files
            }
            
            # Process completed tasks
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                progress.update(task, advance=1)
    
    # Summary
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]
    
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  [green]Successful:[/green] {len(successful)}")
    if failed:
        console.print(f"  [red]Failed:[/red] {len(failed)}")
        for f in failed:
            console.print(f"    - {f['file']}: {f.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
