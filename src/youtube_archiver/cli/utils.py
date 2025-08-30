"""Utility functions for CLI operations."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()


def create_progress() -> Progress:
    """Create a Rich progress bar for operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )


def display_processing_results(results: dict[str, Any]) -> None:
    """Display the results of video processing in a nice format."""
    # This will be implemented when we have the ArchivingService
    console.print("[yellow]🚧 Results display coming soon![/yellow]")


def display_error_summary(errors: list[str]) -> None:
    """Display configuration or processing errors."""
    if not errors:
        return
    
    console.print(Panel(
        "\n".join(f"• {error}" for error in errors),
        title="[red]❌ Errors Found[/red]",
        border_style="red"
    ))


def display_success_message(message: str) -> None:
    """Display a success message."""
    console.print(Panel(
        f"[green]{message}[/green]",
        title="[green]✅ Success[/green]",
        border_style="green"
    ))


def display_warning_message(message: str) -> None:
    """Display a warning message."""
    console.print(Panel(
        f"[yellow]{message}[/yellow]",
        title="[yellow]⚠️ Warning[/yellow]",
        border_style="yellow"
    ))


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask user for confirmation."""
    import click
    return click.confirm(message, default=default)


def format_duration(seconds: int | None) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds is None:
        return "Unknown"
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_view_count(count: int | None) -> str:
    """Format view count in human-readable format."""
    if count is None:
        return "0"
    
    if count < 1000:
        return str(count)
    elif count < 1000000:
        return f"{count / 1000:.1f}K"
    else:
        return f"{count / 1000000:.1f}M"


def create_video_table(videos: list[Any], title: str = "Videos") -> Table:
    """Create a table displaying video information."""
    table = Table(title=title)
    table.add_column("Title", style="cyan", max_width=40)
    table.add_column("Published", style="dim")
    table.add_column("Duration", justify="right")
    table.add_column("Views", justify="right")
    table.add_column("Visibility", justify="center")
    table.add_column("Eligible", justify="center")
    
    for video in videos:
        # Format published date
        published = video.published_at.strftime("%Y-%m-%d")
        
        # Format eligibility
        eligible = "✅ Yes" if video.is_eligible_for_archiving else "❌ No"
        
        # Format visibility with colors
        visibility_colors = {
            "public": "[red]Public[/red]",
            "unlisted": "[yellow]Unlisted[/yellow]",
            "private": "[green]Private[/green]",
        }
        visibility = visibility_colors.get(
            video.visibility.value, 
            video.visibility.value
        )
        
        table.add_row(
            video.title[:37] + "..." if len(video.title) > 40 else video.title,
            published,
            format_duration(video.duration_seconds),
            format_view_count(video.view_count),
            visibility,
            eligible
        )
    
    return table


def display_channel_summary(channel_name: str, stats: dict[str, Any]) -> None:
    """Display summary statistics for a channel."""
    table = Table(title=f"📺 {channel_name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    table.add_row("Total Videos", str(stats.get("total_videos", 0)))
    table.add_row("Eligible Videos", str(stats.get("eligible_videos", 0)))
    table.add_row("Public Videos", str(stats.get("public_videos", 0)))
    table.add_row("Live Content", str(stats.get("live_videos", 0)))
    
    console.print(table)
