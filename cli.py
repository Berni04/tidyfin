"""TidyFin CLI - Command Line Interface for Jellyfin Media Organizer."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from tidyfin.scanner import FileScanner
from tidyfin.organizer import FileOrganizer
from tidyfin.tmdb_client import TMDBClient
from tidyfin.models import MediaType, Confidence


# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def save_config(config_path: Path, config: dict):
    """Save configuration to JSON file."""
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def print_banner():
    """Print the TidyFin banner."""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════╗
║  {Colors.BOLD}TidyFin{Colors.RESET}{Colors.CYAN} - Jellyfin Media Organizer                      ║
║  Automatically organize your media library               ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def print_progress(current: int, total: int, media_file):
    """Print progress for file processing."""
    pct = (current / total) * 100
    bar_width = 30
    filled = int(bar_width * current / total)
    bar = "█" * filled + "░" * (bar_width - filled)
    
    filename = media_file.filename[:40] + "..." if len(media_file.filename) > 40 else media_file.filename
    
    print(f"\r[{bar}] {pct:5.1f}% ({current}/{total}) {filename:<45}", end="", flush=True)


def confidence_color(confidence: Confidence) -> str:
    """Get color for confidence level."""
    return {
        Confidence.HIGH: Colors.GREEN,
        Confidence.MEDIUM: Colors.YELLOW,
        Confidence.LOW: Colors.RED
    }[confidence]


def print_preview(previews: list):
    """Print preview of file organization."""
    print(f"\n{Colors.BOLD}Preview of changes:{Colors.RESET}\n")
    print("-" * 80)
    
    for media_file, dest_path in previews:
        conf = media_file.confidence
        color = confidence_color(conf)
        conf_str = f"[{conf.value.upper()}]"
        
        # Source
        print(f"{Colors.BLUE}From:{Colors.RESET} {media_file.source_path.name}")
        
        # Destination
        if dest_path:
            print(f"{Colors.GREEN}To:  {Colors.RESET} {dest_path}")
        else:
            print(f"{Colors.RED}To:   Manual Review{Colors.RESET}")
        
        # Confidence and match info
        print(f"{color}Confidence: {conf_str} ({media_file.confidence_score:.0%}){Colors.RESET}")
        
        if media_file.tmdb_match:
            match = media_file.tmdb_match
            if match.media_type == MediaType.MOVIE:
                print(f"  → TMDB: {match.title} ({match.year})")
            else:
                print(f"  → TMDB: {match.title} S{match.season_number:02d}E{match.episode_number:02d}")
        
        print("-" * 80)


def print_summary(summary):
    """Print summary of organization."""
    print(f"\n{Colors.BOLD}═══ Summary ═══{Colors.RESET}\n")
    print(f"  Total files processed: {summary.total_files}")
    print(f"  {Colors.GREEN}Movies organized:   {summary.movies_organized}{Colors.RESET}")
    print(f"  {Colors.GREEN}TV Shows organized: {summary.shows_organized}{Colors.RESET}")
    print(f"  {Colors.YELLOW}Manual review:      {summary.manual_review}{Colors.RESET}")
    print(f"  {Colors.BLUE}Skipped:            {summary.skipped}{Colors.RESET}")
    print(f"  {Colors.RED}Errors:             {summary.errors}{Colors.RESET}")
    
    if summary.errors > 0:
        print(f"\n{Colors.RED}Errors:{Colors.RESET}")
        for result in summary.results:
            if result.action == "error":
                print(f"  - {result.source_path.name}: {result.error_message}")


def main():
    parser = argparse.ArgumentParser(
        description="TidyFin - Organize media files for Jellyfin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes (dry run)
  python cli.py --source "D:/Downloads" --movies "D:/Jellyfin/Movies" --shows "D:/Jellyfin/Shows" --dry-run

  # Execute organization
  python cli.py --source "D:/Downloads" --movies "D:/Jellyfin/Movies" --shows "D:/Jellyfin/Shows"

  # With manual review folder
  python cli.py -s "D:/Downloads" -m "D:/Movies" -t "D:/Shows" -r "D:/Review"
        """
    )
    
    parser.add_argument(
        "-s", "--source",
        required=True,
        help="Source directory containing media files to organize"
    )
    parser.add_argument(
        "-m", "--movies",
        required=True,
        help="Destination directory for movies"
    )
    parser.add_argument(
        "-t", "--shows",
        required=True,
        help="Destination directory for TV shows"
    )
    parser.add_argument(
        "-r", "--review",
        help="Directory for files needing manual review"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without moving files"
    )
    parser.add_argument(
        "--no-tmdb",
        action="store_true",
        help="Skip TMDB lookup (use filename parsing only)"
    )
    parser.add_argument(
        "--api-key",
        help="TMDB API key (or set in config.json)"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file (default: config.json)"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't scan subdirectories"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    # Print banner
    if not args.quiet:
        print_banner()
    
    # Load config
    config_path = Path(args.config)
    config = load_config(config_path)
    
    # Get API key
    api_key = args.api_key or config.get("tmdb_api_key")
    
    # Initialize TMDB client
    tmdb_client = None
    if not args.no_tmdb:
        if api_key:
            tmdb_client = TMDBClient(api_key)
            if not args.quiet:
                print(f"{Colors.GREEN}✓ TMDB API connected{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}⚠ No TMDB API key provided. Using filename parsing only.{Colors.RESET}")
            print(f"  Set 'tmdb_api_key' in config.json or use --api-key flag.\n")
    
    # Validate directories
    source_dir = Path(args.source)
    if not source_dir.exists():
        print(f"{Colors.RED}Error: Source directory not found: {source_dir}{Colors.RESET}")
        sys.exit(1)
    
    movies_dir = Path(args.movies)
    shows_dir = Path(args.shows)
    review_dir = Path(args.review) if args.review else None
    
    # Scan for media files
    if not args.quiet:
        print(f"\n{Colors.BOLD}Scanning:{Colors.RESET} {source_dir}")
    
    scanner = FileScanner()
    recursive = not args.no_recursive
    files = scanner.scan(source_dir, recursive=recursive)
    
    if not files:
        print(f"{Colors.YELLOW}No media files found in source directory.{Colors.RESET}")
        sys.exit(0)
    
    if not args.quiet:
        print(f"Found {Colors.BOLD}{len(files)}{Colors.RESET} media files\n")
    
    # Initialize organizer
    organizer = FileOrganizer(
        movies_dir=movies_dir,
        shows_dir=shows_dir,
        review_dir=review_dir,
        tmdb_client=tmdb_client,
        dry_run=args.dry_run
    )
    
    # Preview or execute
    if args.dry_run:
        if not args.quiet:
            print(f"{Colors.CYAN}DRY RUN MODE - No files will be moved{Colors.RESET}")
        
        previews = organizer.preview(files)
        print_preview(previews)
        
        # Count by action
        moves = sum(1 for _, d in previews if d and "review" not in str(d).lower())
        reviews = sum(1 for _, d in previews if d and "review" in str(d).lower()) + sum(1 for _, d in previews if not d)
        
        print(f"\n{Colors.BOLD}Would organize:{Colors.RESET}")
        print(f"  {Colors.GREEN}{moves} files to Movies/Shows{Colors.RESET}")
        print(f"  {Colors.YELLOW}{reviews} files to Manual Review{Colors.RESET}")
        print(f"\nRun without --dry-run to apply changes.")
        
    else:
        if not args.quiet:
            print(f"{Colors.BOLD}Organizing files...{Colors.RESET}\n")
        
        # Run organization
        if args.quiet:
            summary = organizer.organize(files)
        else:
            summary = organizer.organize(files, progress_callback=print_progress)
            print()  # New line after progress bar
        
        print_summary(summary)
    
    # Save any config updates
    if api_key and not config.get("tmdb_api_key"):
        config["tmdb_api_key"] = api_key
        save_config(config_path, config)
        if not args.quiet:
            print(f"\n{Colors.GREEN}API key saved to {config_path}{Colors.RESET}")


if __name__ == "__main__":
    main()
