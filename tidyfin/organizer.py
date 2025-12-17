"""File organizer for moving media to Jellyfin structure."""

import shutil
import re
from pathlib import Path
from typing import Optional, Callable

from .models import (
    MediaFile, MediaType, Confidence, 
    OrganizeResult, OrganizeSummary, TMDBMatch
)
from .tmdb_client import TMDBClient
from .parser import FilenameParser


class FileOrganizer:
    """Organize media files into Jellyfin-compatible structure."""
    
    # Minimum confidence threshold for auto-processing
    MIN_CONFIDENCE_THRESHOLD = 0.5
    
    def __init__(
        self,
        movies_dir: Path,
        shows_dir: Path,
        review_dir: Optional[Path] = None,
        tmdb_client: Optional[TMDBClient] = None,
        dry_run: bool = False
    ):
        """
        Initialize organizer.
        
        Args:
            movies_dir: Destination directory for movies
            shows_dir: Destination directory for TV shows
            review_dir: Directory for files needing manual review
            tmdb_client: TMDB client for metadata lookup
            dry_run: If True, don't actually move files
        """
        self.movies_dir = Path(movies_dir)
        self.shows_dir = Path(shows_dir)
        self.review_dir = Path(review_dir) if review_dir else None
        self.tmdb_client = tmdb_client
        self.dry_run = dry_run
        self.parser = FilenameParser()
    
    def organize(
        self, 
        files: list,
        progress_callback: Optional[Callable[[int, int, MediaFile], None]] = None
    ) -> OrganizeSummary:
        """
        Organize a list of media files.
        
        Args:
            files: List of MediaFile objects
            progress_callback: Optional callback(current, total, file)
            
        Returns:
            OrganizeSummary with results
        """
        summary = OrganizeSummary()
        total = len(files)
        
        for i, media_file in enumerate(files):
            if progress_callback:
                progress_callback(i + 1, total, media_file)
            
            result = self.organize_file(media_file)
            summary.add_result(result)
        
        return summary
    
    def organize_file(self, media_file: MediaFile) -> OrganizeResult:
        """
        Organize a single media file.
        
        Args:
            media_file: The MediaFile to organize
            
        Returns:
            OrganizeResult with outcome
        """
        try:
            # Try to identify with TMDB if we have a client
            if self.tmdb_client and media_file.parsed_info:
                match = self.tmdb_client.identify_media(media_file.parsed_info)
                if match:
                    media_file.tmdb_match = match
                    media_file.confidence_score = match.confidence_score
                    media_file.confidence = self._score_to_confidence(match.confidence_score)
            
            # Check if confidence is too low
            if media_file.confidence_score < self.MIN_CONFIDENCE_THRESHOLD:
                return self._send_to_review(media_file)
            
            # Generate destination path
            dest_path = self._generate_destination(media_file)
            if not dest_path:
                return self._send_to_review(media_file)
            
            # Move the file
            return self._move_file(media_file, dest_path)
            
        except Exception as e:
            return OrganizeResult(
                media_file=media_file,
                success=False,
                source_path=media_file.source_path,
                action="error",
                error_message=str(e),
                dry_run=self.dry_run
            )
    
    def _generate_destination(self, media_file: MediaFile) -> Optional[Path]:
        """Generate the destination path for a media file."""
        media_type = media_file.get_media_type()
        
        if media_type == MediaType.MOVIE:
            return self._generate_movie_path(media_file)
        elif media_type == MediaType.TV_SHOW:
            return self._generate_show_path(media_file)
        
        return None
    
    def _generate_movie_path(self, media_file: MediaFile) -> Path:
        """
        Generate Jellyfin movie path.
        Format: /Movies/Movie Name (Year)/Movie Name (Year).ext
        """
        # Prefer TMDB data, fall back to parsed
        if media_file.tmdb_match:
            title = media_file.tmdb_match.title
            year = media_file.tmdb_match.year
        elif media_file.parsed_info:
            title = media_file.parsed_info.title
            year = media_file.parsed_info.year
        else:
            raise ValueError("No title information available")
        
        # Clean title for filesystem
        clean_title = self._clean_for_filesystem(title)
        
        # Format folder and filename
        if year:
            folder_name = f"{clean_title} ({year})"
        else:
            folder_name = clean_title
        
        filename = f"{folder_name}{media_file.extension}"
        
        return self.movies_dir / folder_name / filename
    
    def _generate_show_path(self, media_file: MediaFile) -> Path:
        """
        Generate Jellyfin TV show path.
        Format: /Shows/Show Name/Season 01/Show Name - S01E01 - Episode Title.ext
        """
        # Prefer TMDB data, fall back to parsed
        if media_file.tmdb_match:
            title = media_file.tmdb_match.title
            season = media_file.tmdb_match.season_number
            episode = media_file.tmdb_match.episode_number
            episode_title = media_file.tmdb_match.episode_title
        elif media_file.parsed_info:
            title = media_file.parsed_info.title
            season = media_file.parsed_info.season
            episode = media_file.parsed_info.episode
            episode_title = media_file.parsed_info.episode_title
        else:
            raise ValueError("No title information available")
        
        if season is None or episode is None:
            raise ValueError("Missing season/episode information")
        
        # Clean title for filesystem
        clean_title = self._clean_for_filesystem(title)
        
        # Format paths
        season_folder = f"Season {season:02d}"
        
        # Build filename
        if episode_title:
            clean_ep_title = self._clean_for_filesystem(episode_title)
            filename = f"{clean_title} - S{season:02d}E{episode:02d} - {clean_ep_title}{media_file.extension}"
        else:
            filename = f"{clean_title} - S{season:02d}E{episode:02d}{media_file.extension}"
        
        return self.shows_dir / clean_title / season_folder / filename
    
    def _move_file(self, media_file: MediaFile, dest_path: Path) -> OrganizeResult:
        """Move a file to its destination."""
        if not self.dry_run:
            # Create destination directory
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            shutil.move(str(media_file.source_path), str(dest_path))
        
        return OrganizeResult(
            media_file=media_file,
            success=True,
            source_path=media_file.source_path,
            destination_path=dest_path,
            action="moved",
            dry_run=self.dry_run
        )
    
    def _send_to_review(self, media_file: MediaFile) -> OrganizeResult:
        """Send a file to manual review folder."""
        if not self.review_dir:
            return OrganizeResult(
                media_file=media_file,
                success=False,
                source_path=media_file.source_path,
                action="skipped",
                error_message="Low confidence and no review directory configured",
                dry_run=self.dry_run
            )
        
        dest_path = self.review_dir / media_file.filename
        
        if not self.dry_run:
            self.review_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(media_file.source_path), str(dest_path))
        
        return OrganizeResult(
            media_file=media_file,
            success=True,
            source_path=media_file.source_path,
            destination_path=dest_path,
            action="manual_review",
            dry_run=self.dry_run
        )
    
    def _clean_for_filesystem(self, name: str) -> str:
        """Clean a name for safe filesystem use."""
        # Remove/replace invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        clean = re.sub(invalid_chars, '', name)
        
        # Replace multiple spaces with single space
        clean = re.sub(r'\s+', ' ', clean)
        
        # Strip leading/trailing whitespace and dots
        clean = clean.strip(' .')
        
        # Limit length (Windows max path component is 255)
        if len(clean) > 200:
            clean = clean[:200]
        
        return clean
    
    def _score_to_confidence(self, score: float) -> Confidence:
        """Convert confidence score to enum."""
        if score >= 0.8:
            return Confidence.HIGH
        elif score >= 0.5:
            return Confidence.MEDIUM
        else:
            return Confidence.LOW
    
    def preview(self, files: list) -> list:
        """
        Preview what would happen without moving files.
        
        Returns list of (MediaFile, proposed_destination) tuples.
        """
        previews = []
        for media_file in files:
            # Identify if not already done
            if self.tmdb_client and media_file.parsed_info and not media_file.tmdb_match:
                match = self.tmdb_client.identify_media(media_file.parsed_info)
                if match:
                    media_file.tmdb_match = match
                    media_file.confidence_score = match.confidence_score
            
            try:
                dest = self._generate_destination(media_file)
            except:
                dest = self.review_dir if self.review_dir else None
            
            previews.append((media_file, dest))
        
        return previews
