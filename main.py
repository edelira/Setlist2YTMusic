#!/usr/bin/env python3
"""
Setlist2YTMusic - Convert setlist.fm setlists to YouTube Music playlists

This application takes a setlist.fm URL and creates a YouTube playlist
with the best matching videos for each song in the setlist.
"""

import sys
import argparse
from typing import List, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from setlist_parser import get_setlist_from_url, SetlistInfo, Track
from youtube_client import YouTubeClient
from config import DEFAULT_PRIVACY


console = Console()


def create_playlist_title(setlist: SetlistInfo) -> str:
    """Generate a playlist title from setlist info."""
    return f"{setlist.artist} - {setlist.venue} ({setlist.date})"


def create_playlist_description(setlist: SetlistInfo) -> str:
    """Generate a playlist description."""
    return (
        f"Setlist from {setlist.artist} at {setlist.venue}, {setlist.city} on {setlist.date}\n\n"
        f"Generated from: {setlist.url}\n"
        f"Source: setlist.fm\n"
        f"Total tracks: {len(setlist.tracks)}"
    )


def display_setlist_info(setlist: SetlistInfo):
    """Display setlist information in a nice format."""
    info_text = Text()
    info_text.append(f"Artist: ", style="bold cyan")
    info_text.append(f"{setlist.artist}\n")
    info_text.append(f"Venue: ", style="bold cyan")
    info_text.append(f"{setlist.venue}, {setlist.city}\n")
    info_text.append(f"Date: ", style="bold cyan")
    info_text.append(f"{setlist.date}\n")
    info_text.append(f"Tracks: ", style="bold cyan")
    info_text.append(f"{len(setlist.tracks)}")
    
    console.print(Panel(info_text, title="Setlist Information", border_style="blue"))


def display_tracks_table(setlist: SetlistInfo):
    """Display tracks in a table format."""
    table = Table(title="Tracks in Setlist")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Song", style="white")
    table.add_column("Artist", style="green")
    table.add_column("Notes", style="yellow")
    
    for i, track in enumerate(setlist.tracks, 1):
        notes = []
        if track.is_cover:
            notes.append(f"Cover of {track.original_artist}")
        
        table.add_row(
            str(i),
            track.title,
            track.original_artist if track.is_cover else track.artist,
            ", ".join(notes) if notes else ""
        )
    
    console.print(table)


def process_playlist_creation(setlist: SetlistInfo, privacy: str, dry_run: bool = False) -> Tuple[str, List[Track], List[Track]]:
    """Process the playlist creation and return results."""
    
    if dry_run:
        console.print(Panel("[yellow]DRY RUN MODE - No playlist will be created[/yellow]"))
    
    youtube = YouTubeClient()
    
    # Check quota before starting
    quota_info = youtube.get_quota_usage()
    estimated_quota_needed = len(setlist.tracks) * 150  # 100 for search + 50 for add
    
    if not youtube.check_quota_limit(estimated_quota_needed):
        console.print(f"[red]⚠️  Warning: Estimated quota usage ({quota_info['quota_used'] + estimated_quota_needed}) may exceed daily limit![/red]")
        console.print(f"[yellow]Current usage: {quota_info['quota_used']}/10000 units[/yellow]")
        console.print(f"[yellow]Cache hits available: {quota_info['cache_hits']} songs[/yellow]")
    
    playlist_id = None
    playlist_url = ""
    
    if not dry_run:
        # Create the playlist
        title = create_playlist_title(setlist)
        description = create_playlist_description(setlist)
        
        with console.status("[bold green]Creating YouTube playlist..."):
            playlist_id = youtube.create_playlist(title, description, privacy)
            playlist_url = youtube.get_playlist_url(playlist_id)
        
        console.print(f"[green]✓[/green] Created playlist: [link={playlist_url}]{title}[/link]")
    
    # Process each track
    found_tracks = []
    not_found_tracks = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Processing tracks...", total=len(setlist.tracks))
        
        for i, track in enumerate(setlist.tracks, 1):
            progress.update(task, description=f"Searching for: {track.title}")
            
            # Check quota before each search
            if not youtube.check_quota_limit(150):  # 100 for search + 50 for add
                console.print(f"[red]⚠️  Quota limit reached! Stopping at track {i}[/red]")
                break
            
            # Find best match
            video_id = youtube.find_best_match(track)
            
            if video_id:
                if not dry_run:
                    # Add to playlist
                    success = youtube.add_video_to_playlist(playlist_id, video_id)
                    if success:
                        found_tracks.append(track)
                        console.print(f"[green]✓[/green] [{i:2d}] {track.title}")
                    else:
                        not_found_tracks.append(track)
                        console.print(f"[red]✗[/red] [{i:2d}] {track.title} (failed to add)")
                else:
                    found_tracks.append(track)
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    console.print(f"[green]✓[/green] [{i:2d}] {track.title} -> [link={video_url}]YouTube[/link]")
            else:
                not_found_tracks.append(track)
                console.print(f"[red]✗[/red] [{i:2d}] {track.title} (no match found)")
            
            progress.advance(task)
    
    return playlist_url, found_tracks, not_found_tracks


def display_results(playlist_url: str, found_tracks: List[Track], not_found_tracks: List[Track], dry_run: bool = False, youtube_client=None):
    """Display the final results."""
    
    if not dry_run and playlist_url:
        console.print(Panel(
            f"[green]Playlist created successfully![/green]\n\n"
            f"[link={playlist_url}]{playlist_url}[/link]\n\n"
            f"Added {len(found_tracks)} out of {len(found_tracks) + len(not_found_tracks)} tracks",
            title="Success!",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[yellow]Dry run completed![/yellow]\n\n"
            f"Found matches for {len(found_tracks)} out of {len(found_tracks) + len(not_found_tracks)} tracks",
            title="Dry Run Results",
            border_style="yellow"
        ))
    
    # Show quota usage if available
    if youtube_client:
        quota_info = youtube_client.get_quota_usage()
        console.print(f"\n[cyan]Quota Usage: {quota_info['quota_used']}/10000 units used[/cyan]")
        console.print(f"[cyan]Cache hits: {quota_info['cache_hits']} songs cached[/cyan]")
    
    if not_found_tracks:
        console.print("\n[red]Tracks not found:[/red]")
        for track in not_found_tracks:
            console.print(f"  • {track.title}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a setlist.fm setlist to a YouTube Music playlist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py https://www.setlist.fm/setlist/artist/2025/venue-12345678.html
  python main.py --privacy unlisted --dry-run https://www.setlist.fm/setlist/...
        """
    )
    
    parser.add_argument("url", help="setlist.fm URL for the setlist to convert")
    parser.add_argument(
        "--privacy", 
        choices=["private", "unlisted", "public"], 
        default=DEFAULT_PRIVACY,
        help=f"Playlist privacy setting (default: {DEFAULT_PRIVACY})"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Preview matches without creating a playlist"
    )
    parser.add_argument(
        "--show-tracks", 
        action="store_true",
        help="Display the track list before processing"
    )
    parser.add_argument(
        "--clear-cache", 
        action="store_true",
        help="Clear the video cache before processing"
    )
    parser.add_argument(
        "--quota-status", 
        action="store_true",
        help="Show current quota usage and cache status"
    )
    
    args = parser.parse_args()
    
    try:
        console.print(Panel("[bold blue]Setlist2YTMusic[/bold blue]", subtitle="Converting setlist.fm to YouTube Music"))
        
        # Handle special commands
        if args.quota_status:
            youtube = YouTubeClient()
            quota_info = youtube.get_quota_usage()
            console.print(f"\n[cyan]Quota Usage: {quota_info['quota_used']}/10000 units used[/cyan]")
            console.print(f"[cyan]Cache entries: {quota_info['cache_hits']} songs cached[/cyan]")
            console.print(f"[cyan]Recent cache hits: {quota_info['recent_cache_hits']} in last 24h[/cyan]")
            return 0
        
        # Parse the setlist
        with console.status("[bold blue]Fetching setlist data..."):
            setlist = get_setlist_from_url(args.url)
        
        # Display setlist info
        display_setlist_info(setlist)
        
        if not setlist.tracks:
            console.print("[red]No tracks found in this setlist![/red]")
            return 1
        
        # Optionally show tracks table
        if args.show_tracks:
            display_tracks_table(setlist)
            
            if not args.dry_run:
                response = console.input("\nProceed with playlist creation? [Y/n]: ")
                if response.lower() in ['n', 'no']:
                    console.print("Cancelled.")
                    return 0
        
        # Create the playlist
        youtube = YouTubeClient()
        
        # Clear cache if requested
        if args.clear_cache:
            youtube.clear_cache()
        
        playlist_url, found_tracks, not_found_tracks = process_playlist_creation(
            setlist, args.privacy, args.dry_run
        )
        
        # Display results
        display_results(playlist_url, found_tracks, not_found_tracks, args.dry_run, youtube)
        
        return 0
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
