"""Data models for TidyFin media organizer."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List


class MediaType(Enum):
    """Type of media file."""
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    UNKNOWN = "unknown"


class Confidence(Enum):
    """Confidence level for media identification."""
    HIGH = "high"      # 80-100% - Auto-process
    MEDIUM = "medium"  # 50-79% - Auto-process with warning
    LOW = "low"        # 0-49% - Manual review


@dataclass
class ParsedInfo:
    """Information parsed from a filename."""
    title: str
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    media_type: MediaType = MediaType.UNKNOWN
    
    def is_tv_show(self) -> bool:
        return self.season is not None and self.episode is not None


@dataclass
class TMDBMatch:
    """A match from TMDB search."""
    tmdb_id: int
    title: str
    original_title: str
    year: Optional[int] = None
    overview: str = ""
    poster_path: Optional[str] = None
    vote_average: float = 0.0
    media_type: MediaType = MediaType.UNKNOWN
    # TV Show specific
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    episode_title: Optional[str] = None
    
    @property
    def confidence_score(self) -> float:
        """Calculate confidence based on match quality."""
        return self._confidence
    
    @confidence_score.setter
    def confidence_score(self, value: float):
        self._confidence = max(0.0, min(1.0, value))
    
    def __post_init__(self):
        self._confidence = 0.0


@dataclass
class MediaFile:
    """Represents a media file to be organized."""
    source_path: Path
    parsed_info: Optional[ParsedInfo] = None
    tmdb_match: Optional[TMDBMatch] = None
    confidence: Confidence = Confidence.LOW
    confidence_score: float = 0.0
    error: Optional[str] = None
    
    @property
    def filename(self) -> str:
        return self.source_path.name
    
    @property
    def extension(self) -> str:
        return self.source_path.suffix.lower()
    
    def get_media_type(self) -> MediaType:
        """Get the determined media type."""
        if self.tmdb_match:
            return self.tmdb_match.media_type
        if self.parsed_info:
            return self.parsed_info.media_type
        return MediaType.UNKNOWN


@dataclass
class OrganizeResult:
    """Result of organizing a single file."""
    media_file: MediaFile
    success: bool
    source_path: Path
    destination_path: Optional[Path] = None
    action: str = ""  # "moved", "skipped", "manual_review", "error"
    error_message: Optional[str] = None
    dry_run: bool = False


@dataclass 
class OrganizeSummary:
    """Summary of an organize operation."""
    total_files: int = 0
    movies_organized: int = 0
    shows_organized: int = 0
    manual_review: int = 0
    skipped: int = 0
    errors: int = 0
    results: List[OrganizeResult] = field(default_factory=list)
    
    def add_result(self, result: OrganizeResult):
        self.results.append(result)
        self.total_files += 1
        if result.action == "moved":
            if result.media_file.get_media_type() == MediaType.MOVIE:
                self.movies_organized += 1
            else:
                self.shows_organized += 1
        elif result.action == "manual_review":
            self.manual_review += 1
        elif result.action == "skipped":
            self.skipped += 1
        elif result.action == "error":
            self.errors += 1
