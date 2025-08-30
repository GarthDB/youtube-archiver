"""Main CLI interface for YouTube Archiver."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from youtube_archiver.domain.exceptions import (
    AuthenticationError,
    ConfigurationError,
    YouTubeArchiverError,
)
from youtube_archiver.infrastructure.container import (
    create_container,
    get_configuration_provider,
    get_video_repository,
    get_visibility_manager,
    get_youtube_auth_manager,
)

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="YouTube Archiver")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config/config.yml",
    help="Path to configuration file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.pass_context
def cli(ctx: click.Context, config: Path, verbose: bool) -> None:
    """
    YouTube Archiver - Automated tool for managing YouTube live stream visibility.
    
    This tool helps LDS stake tech specialists automatically change the visibility
    of sacrament meeting live streams from public to unlisted after the 24-hour
    church policy window.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["verbose"] = verbose
    
    # Set up console for verbose mode
    if verbose:
        console.print(f"[dim]Using configuration: {config}[/dim]")


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be processed without making changes",
)
@click.option(
    "--channels",
    multiple=True,
    help="Process only specific channel IDs (can be used multiple times)",
)
@click.pass_context
def process(ctx: click.Context, dry_run: bool, channels: tuple[str, ...]) -> None:
    """Process videos according to configuration settings."""
    config_path = ctx.obj["config_path"]
    verbose = ctx.obj["verbose"]
    
    if dry_run:
        console.print(Panel(
            "[yellow]🔍 DRY RUN MODE[/yellow]\n"
            "No actual changes will be made to videos.\n"
            "This will show you what would be processed.",
            title="Dry Run",
            border_style="yellow"
        ))
    
    try:
        # Create container and get services
        container = create_container(config_path)
        config_provider = get_configuration_provider(container)
        
        # Run the processing
        asyncio.run(_process_videos(
            container=container,
            config_provider=config_provider,
            dry_run=dry_run,
            specific_channels=list(channels) if channels else None,
            verbose=verbose
        ))
        
    except ConfigurationError as e:
        console.print(f"[red]❌ Configuration Error:[/red] {e}")
        sys.exit(1)
    except AuthenticationError as e:
        console.print(f"[red]❌ Authentication Error:[/red] {e}")
        console.print("\n[yellow]💡 Tip:[/yellow] Run 'youtube-archiver auth setup' to configure authentication.")
        sys.exit(1)
    except YouTubeArchiverError as e:
        console.print(f"[red]❌ Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected Error:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.group()
def auth() -> None:
    """Authentication management commands."""
    pass


@auth.command()
@click.pass_context
def setup(ctx: click.Context) -> None:
    """Set up YouTube API authentication."""
    config_path = ctx.obj["config_path"]
    verbose = ctx.obj["verbose"]
    
    console.print(Panel(
        "[blue]🔐 YouTube API Authentication Setup[/blue]\n\n"
        "This will guide you through setting up authentication with the YouTube API.\n"
        "You'll need your credentials.json file from Google Cloud Console.",
        title="Authentication Setup",
        border_style="blue"
    ))
    
    try:
        container = create_container(config_path)
        auth_manager = get_youtube_auth_manager(container)
        
        # Test authentication
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Setting up authentication...", total=None)
            
            # This will trigger the OAuth flow if needed
            user_info = auth_manager.get_user_info()
            progress.update(task, description="Authentication successful!")
        
        # Display user info
        _display_user_info(user_info)
        
        console.print("\n[green]✅ Authentication setup complete![/green]")
        
    except ConfigurationError as e:
        console.print(f"\n[red]❌ Configuration Error:[/red] {e}")
        _show_auth_help()
        sys.exit(1)
    except AuthenticationError as e:
        console.print(f"\n[red]❌ Authentication Error:[/red] {e}")
        _show_auth_help()
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected Error:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


@auth.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check authentication status."""
    config_path = ctx.obj["config_path"]
    verbose = ctx.obj["verbose"]
    
    try:
        container = create_container(config_path)
        auth_manager = get_youtube_auth_manager(container)
        
        if auth_manager.is_authenticated:
            console.print("[green]✅ Authenticated[/green]")
            
            # Get and display user info
            user_info = auth_manager.get_user_info()
            _display_user_info(user_info)
        else:
            console.print("[red]❌ Not authenticated[/red]")
            console.print("\n[yellow]💡 Tip:[/yellow] Run 'youtube-archiver auth setup' to authenticate.")
            
    except Exception as e:
        console.print(f"[red]❌ Error checking authentication:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


@auth.command()
@click.confirmation_option(prompt="Are you sure you want to reset authentication?")
@click.pass_context
def reset(ctx: click.Context) -> None:
    """Reset authentication (remove stored tokens)."""
    config_path = ctx.obj["config_path"]
    
    try:
        container = create_container(config_path)
        auth_manager = get_youtube_auth_manager(container)
        
        auth_manager.revoke_credentials()
        console.print("[green]✅ Authentication reset successfully[/green]")
        console.print("\n[yellow]💡 Tip:[/yellow] Run 'youtube-archiver auth setup' to re-authenticate.")
        
    except Exception as e:
        console.print(f"[red]❌ Error resetting authentication:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate configuration and check channel access."""
    config_path = ctx.obj["config_path"]
    verbose = ctx.obj["verbose"]
    
    console.print(Panel(
        "[blue]🔍 Configuration Validation[/blue]\n"
        "Checking configuration file, authentication, and channel access...",
        title="Validation",
        border_style="blue"
    ))
    
    try:
        container = create_container(config_path)
        config_provider = get_configuration_provider(container)
        auth_manager = get_youtube_auth_manager(container)
        
        # Validate configuration
        console.print("\n[cyan]📋 Configuration Check[/cyan]")
        channels = config_provider.get_channels()
        console.print(f"✅ Found {len(channels)} configured channels")
        console.print(f"✅ Age threshold: {config_provider.get_age_threshold_hours()} hours")
        console.print(f"✅ Target visibility: {config_provider.get_target_visibility()}")
        console.print(f"✅ Dry run mode: {config_provider.get_dry_run_mode()}")
        
        # Check authentication
        console.print("\n[cyan]🔐 Authentication Check[/cyan]")
        if auth_manager.is_authenticated:
            console.print("✅ Authentication valid")
            user_info = auth_manager.get_user_info()
            if user_info.get("has_channel"):
                console.print(f"✅ YouTube channel: {user_info.get('channel_title', 'Unknown')}")
            else:
                console.print("[yellow]⚠️  No YouTube channel found for authenticated account[/yellow]")
        else:
            console.print("[red]❌ Not authenticated[/red]")
            return
        
        # Check channel access
        console.print("\n[cyan]📺 Channel Access Check[/cyan]")
        
        # Run async channel validation
        asyncio.run(_validate_channel_access(container, channels, verbose))
        
        console.print("\n[green]✅ Validation complete![/green]")
        
    except Exception as e:
        console.print(f"\n[red]❌ Validation failed:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option(
    "--channels",
    multiple=True,
    help="Show summary for specific channel IDs only",
)
@click.pass_context
def summary(ctx: click.Context, channels: tuple[str, ...]) -> None:
    """Show a summary of videos eligible for processing."""
    config_path = ctx.obj["config_path"]
    verbose = ctx.obj["verbose"]
    
    console.print(Panel(
        "[blue]📊 Video Processing Summary[/blue]\n"
        "Analyzing channels for videos eligible for processing...",
        title="Summary",
        border_style="blue"
    ))
    
    try:
        container = create_container(config_path)
        
        asyncio.run(_show_summary(
            container=container,
            specific_channels=list(channels) if channels else None,
            verbose=verbose
        ))
        
    except Exception as e:
        console.print(f"\n[red]❌ Error generating summary:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


async def _validate_channel_access(
    container: Any,
    channels: list[Any],
    verbose: bool,
) -> None:
    """Validate access to configured channels."""
    video_repo = get_video_repository(container)
    
    for channel_config in channels:
        if not channel_config.enabled:
            console.print(f"⏭️  {channel_config.name}: Disabled")
            continue
            
        try:
            # Try to get a few videos to test access
            channel = channel_config.to_domain()
            videos = await video_repo.get_channel_videos(channel, max_results=5)
            console.print(f"✅ {channel_config.name}: {len(videos)} videos accessible")
        except Exception as e:
            console.print(f"[red]❌ {channel_config.name}: {e}[/red]")


async def _process_videos(
    container: Any,
    config_provider: Any,
    dry_run: bool,
    specific_channels: list[str] | None,
    verbose: bool,
) -> None:
    """Process videos with progress tracking."""
    # This is a placeholder - we'll implement the full processing logic
    # when we create the ArchivingService
    console.print("\n[yellow]🚧 Processing functionality coming soon![/yellow]")
    console.print("This will be implemented with the ArchivingService.")


async def _show_summary(
    container: Any,
    specific_channels: list[str] | None,
    verbose: bool,
) -> None:
    """Show summary of eligible videos."""
    config_provider = get_configuration_provider(container)
    video_repo = get_video_repository(container)
    
    channels = config_provider.get_channels()
    if specific_channels:
        channels = [c for c in channels if c.channel_id in specific_channels]
    
    table = Table(title="Video Summary")
    table.add_column("Channel", style="cyan")
    table.add_column("Total Videos", justify="right")
    table.add_column("Eligible Videos", justify="right", style="yellow")
    table.add_column("Status", justify="center")
    
    total_videos = 0
    total_eligible = 0
    
    for channel_config in channels:
        if not channel_config.enabled:
            table.add_row(
                channel_config.name,
                "-",
                "-",
                "[dim]Disabled[/dim]"
            )
            continue
        
        try:
            channel = channel_config.to_domain()
            videos = await video_repo.get_channel_videos(
                channel, 
                max_results=channel_config.max_videos_to_check
            )
            
            eligible_videos = [v for v in videos if v.is_eligible_for_archiving]
            
            total_videos += len(videos)
            total_eligible += len(eligible_videos)
            
            status = "✅ Ready" if eligible_videos else "✅ Up to date"
            
            table.add_row(
                channel_config.name,
                str(len(videos)),
                str(len(eligible_videos)),
                status
            )
            
        except Exception as e:
            table.add_row(
                channel_config.name,
                "-",
                "-",
                f"[red]❌ Error[/red]"
            )
            if verbose:
                console.print(f"[dim]Error for {channel_config.name}: {e}[/dim]")
    
    console.print(table)
    
    # Summary totals
    console.print(f"\n[bold]Total Summary:[/bold]")
    console.print(f"📺 Total videos checked: {total_videos}")
    console.print(f"🎯 Videos eligible for processing: {total_eligible}")
    
    if total_eligible > 0:
        console.print(f"\n[yellow]💡 Tip:[/yellow] Run with --dry-run first to see what would be changed.")


def _display_user_info(user_info: dict[str, Any]) -> None:
    """Display user authentication information."""
    table = Table(title="Authentication Info")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Authenticated", "✅ Yes" if user_info.get("authenticated") else "❌ No")
    
    if user_info.get("has_channel"):
        table.add_row("Channel", user_info.get("channel_title", "Unknown"))
        table.add_row("Channel ID", user_info.get("channel_id", "Unknown"))
        table.add_row("Subscribers", user_info.get("subscriber_count", "0"))
        table.add_row("Videos", user_info.get("video_count", "0"))
    else:
        table.add_row("Channel", "❌ No YouTube channel found")
    
    console.print(table)


def _show_auth_help() -> None:
    """Show authentication help information."""
    console.print(Panel(
        "[yellow]🔧 Authentication Setup Help[/yellow]\n\n"
        "To set up authentication:\n\n"
        "1. Go to Google Cloud Console (console.cloud.google.com)\n"
        "2. Create a new project or select existing project\n"
        "3. Enable the YouTube Data API v3\n"
        "4. Create OAuth2 credentials (Desktop application)\n"
        "5. Download the credentials.json file\n"
        "6. Place it in your project directory\n"
        "7. Update your config.yml with the correct path\n\n"
        "For detailed instructions, see: docs/youtube-api-setup.md",
        title="Setup Help",
        border_style="yellow"
    ))


def main() -> None:
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
