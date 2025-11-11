#!/usr/bin/env python3
"""
View AI call costs and token usage summary.
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from meeting_transcription_tool.ai_logger import get_ai_logger
from rich.console import Console
from rich.table import Table

console = Console()


def main():
    """Display AI cost summary."""
    ai_logger = get_ai_logger()
    
    # Get summary for all time
    summary = ai_logger.get_cost_summary()
    
    # Also get last 24 hours
    yesterday = datetime.now() - timedelta(days=1)
    daily_summary = ai_logger.get_cost_summary(start_date=yesterday)
    
    console.print("\n[bold cyan]AI Usage Summary[/bold cyan]\n")
    
    # Overall summary table
    table = Table(title="Overall Summary (All Time)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    
    table.add_row("Total API Calls", f"{summary['total_calls']:,}")
    table.add_row("Total Cost", f"${summary['total_cost_usd']:.6f}")
    table.add_row("Total Input Tokens", f"{summary['total_input_tokens']:,}")
    table.add_row("Total Output Tokens", f"{summary['total_output_tokens']:,}")
    table.add_row("Total Tokens", f"{summary['total_tokens']:,}")
    
    if summary['total_calls'] > 0:
        avg_cost = summary['total_cost_usd'] / summary['total_calls']
        table.add_row("Avg Cost per Call", f"${avg_cost:.6f}")
    
    console.print(table)
    
    # Daily summary
    if daily_summary['total_calls'] > 0:
        console.print("\n[bold cyan]Last 24 Hours[/bold cyan]\n")
        daily_table = Table()
        daily_table.add_column("Metric", style="cyan")
        daily_table.add_column("Value", style="yellow", justify="right")
        
        daily_table.add_row("API Calls", f"{daily_summary['total_calls']:,}")
        daily_table.add_row("Cost", f"${daily_summary['total_cost_usd']:.6f}")
        daily_table.add_row("Tokens", f"{daily_summary['total_tokens']:,}")
        
        console.print(daily_table)
    
    console.print(f"\n[dim]Log files location: {ai_logger.log_dir}[/dim]\n")


if __name__ == "__main__":
    main()
