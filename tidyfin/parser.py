"""Filename parser for extracting media information."""

import re
from pathlib import Path
from typing import Optional, Tuple, List

from .models import ParsedInfo, MediaType


class FilenameParser:
    """Parse media filenames to extract title, year, season, episode info."""
    
    # Common video extensions
    VIDEO_EXTENSIONS = {
        '.mkv', '.mp4', '.avi', '.mov', '.wmv', 
        '.flv', '.webm', '.m4v', '.ts', '.mpg', '.mpeg'
    }
    
    # Patterns to remove from filenames (release groups, quality, etc.)
    CLEANUP_PATTERNS = [
        r'\[.*?\]',           # [stuff in brackets]
        r'\((?!(?:19|20)\d{2})\D*\)',  # (stuff) but not (year)
        r'\b(720p|1080p|2160p|4k|uhd)\b',
        r'\b(bluray|bdrip|brrip|dvdrip|webrip|web-dl|hdtv|hdrip)\b',
        r'\b(x264|x265|h264|h265|hevc|avc|xvid|divx)\b',
        r'\b(aac|ac3|dts|truehd|atmos|flac|mp3)\b',
        r'\b(remux|repack|proper|extended|unrated|directors\.cut)\b',
        r'\b(yts|yify|rarbg|ettv|eztv|sparks|geckos|ntg)\b',
        r'\b(multi|dual|complete)\b',
        r'-\w+$',             # -ReleaseGroup at end
    ]
    
    # TV Show patterns (order matters - more specific first)
    TV_PATTERNS = [
        # S01E01 format (most common)
        r'[.\s_-]S(\d{1,2})[\s._-]?E(\d{1,3})(?:[\s._-]E(\d{1,3}))?',
        # 1x01 format
        r'[.\s_-](\d{1,2})x(\d{1,3})',
        # Season 1 Episode 1 format
        r'[.\s_-]Season[\s._-]?(\d{1,2})[\s._-]?Episode[\s._-]?(\d{1,3})',
        # S01.E01 format
        r'[.\s_-]S(\d{1,2})\.E(\d{1,3})',
    ]
    
    # Year pattern
    YEAR_PATTERN = r'[\.\s_\(\[-]((?:19|20)\d{2})[\.\s_\)\]-]'
    
    def __init__(self):
        # Compile patterns for performance
        self.cleanup_regexes = [
            re.compile(p, re.IGNORECASE) for p in self.CLEANUP_PATTERNS
        ]
        self.tv_regexes = [
            re.compile(p, re.IGNORECASE) for p in self.TV_PATTERNS
        ]
        self.year_regex = re.compile(self.YEAR_PATTERN)
    
    def is_video_file(self, path: Path) -> bool:
        """Check if file is a video based on extension."""
        return path.suffix.lower() in self.VIDEO_EXTENSIONS
    
    def parse(self, filename: str) -> ParsedInfo:
        """Parse a filename and extract media information."""
        # Remove extension
        name = Path(filename).stem
        
        # Try TV show parsing first
        tv_info = self._parse_tv_show(name)
        if tv_info:
            return tv_info
        
        # Fall back to movie parsing
        return self._parse_movie(name)
    
    def _parse_tv_show(self, name: str) -> Optional[ParsedInfo]:
        """Try to parse as a TV show."""
        for regex in self.tv_regexes:
            match = regex.search(name)
            if match:
                groups = match.groups()
                season = int(groups[0])
                episode = int(groups[1])
                
                # Extract title (everything before the S01E01 pattern)
                title_part = name[:match.start()]
                title = self._clean_title(title_part)
                
                # Extract episode title (everything after pattern, cleaned)
                episode_title = None
                after_pattern = name[match.end():]
                if after_pattern:
                    episode_title = self._clean_title(after_pattern)
                    if len(episode_title) < 2:
                        episode_title = None
                
                # Try to find year in title
                year = self._extract_year(title_part)
                
                return ParsedInfo(
                    title=title,
                    year=year,
                    season=season,
                    episode=episode,
                    episode_title=episode_title,
                    media_type=MediaType.TV_SHOW
                )
        
        return None
    
    def _parse_movie(self, name: str) -> ParsedInfo:
        """Parse as a movie."""
        # Extract year first
        year = self._extract_year(name)
        
        # If we have a year, title is everything before it
        if year:
            year_match = self.year_regex.search(name)
            if year_match:
                title_part = name[:year_match.start()]
            else:
                title_part = name
        else:
            title_part = name
        
        # Clean the title
        title = self._clean_title(title_part)
        
        return ParsedInfo(
            title=title,
            year=year,
            media_type=MediaType.MOVIE if year else MediaType.UNKNOWN
        )
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Extract a year (1900-2099) from text."""
        match = self.year_regex.search(text)
        if match:
            year = int(match.group(1))
            # Sanity check - year should be reasonable
            if 1900 <= year <= 2099:
                return year
        return None
    
    def _clean_title(self, title: str) -> str:
        """Clean up a title string."""
        # Apply cleanup patterns
        for regex in self.cleanup_regexes:
            title = regex.sub(' ', title)
        
        # Replace dots, underscores, hyphens with spaces
        title = re.sub(r'[._-]+', ' ', title)
        
        # Remove multiple spaces
        title = re.sub(r'\s+', ' ', title)
        
        # Strip and title case
        title = title.strip()
        
        # Don't change case if it looks intentionally formatted
        if not title.isupper() and not title.islower():
            return title
        
        return title.title()


# Convenience function
def parse_filename(filename: str) -> ParsedInfo:
    """Parse a filename and return extracted info."""
    parser = FilenameParser()
    return parser.parse(filename)
