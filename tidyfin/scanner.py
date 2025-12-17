"""File scanner for discovering media files."""

from pathlib import Path
from typing import List, Generator, Optional, Set

from .models import MediaFile, Confidence
from .parser import FilenameParser


class FileScanner:
    """Scan directories for media files."""
    
    def __init__(self, extensions: Optional[Set[str]] = None):
        """
        Initialize scanner.
        
        Args:
            extensions: Set of file extensions to include (with dots, lowercase).
                       Defaults to common video formats.
        """
        self.parser = FilenameParser()
        self.extensions = extensions or self.parser.VIDEO_EXTENSIONS
    
    def scan(self, source_dir: Path, recursive: bool = True) -> List[MediaFile]:
        """
        Scan a directory for media files.
        
        Args:
            source_dir: Directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of MediaFile objects
        """
        return list(self.scan_iter(source_dir, recursive))
    
    def scan_iter(
        self, 
        source_dir: Path, 
        recursive: bool = True
    ) -> Generator[MediaFile, None, None]:
        """
        Scan a directory and yield media files.
        
        Args:
            source_dir: Directory to scan
            recursive: Whether to scan subdirectories
            
        Yields:
            MediaFile objects
        """
        source_dir = Path(source_dir)
        
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        
        if not source_dir.is_dir():
            raise NotADirectoryError(f"Not a directory: {source_dir}")
        
        # Choose iteration method
        if recursive:
            files = source_dir.rglob("*")
        else:
            files = source_dir.glob("*")
        
        for file_path in files:
            if self._is_media_file(file_path):
                yield self._create_media_file(file_path)
    
    def _is_media_file(self, path: Path) -> bool:
        """Check if path is a media file we should process."""
        if not path.is_file():
            return False
        return path.suffix.lower() in self.extensions
    
    def _create_media_file(self, path: Path) -> MediaFile:
        """Create a MediaFile from a path."""
        # Parse the filename
        parsed_info = self.parser.parse(path.name)
        
        # Determine initial confidence based on parsing quality
        confidence = self._initial_confidence(parsed_info)
        
        return MediaFile(
            source_path=path,
            parsed_info=parsed_info,
            confidence=confidence,
            confidence_score=self._confidence_to_score(confidence)
        )
    
    def _initial_confidence(self, parsed_info) -> Confidence:
        """Determine initial confidence from parsed info."""
        from .models import MediaType
        
        # TV show with season and episode is usually high confidence
        if parsed_info.is_tv_show() and parsed_info.title:
            return Confidence.HIGH
        
        # Movie with year is medium-high confidence
        if parsed_info.media_type == MediaType.MOVIE and parsed_info.year:
            return Confidence.HIGH
        
        # Title only, no year
        if parsed_info.title and len(parsed_info.title) >= 2:
            return Confidence.MEDIUM
        
        # Unable to parse anything meaningful
        return Confidence.LOW
    
    def _confidence_to_score(self, confidence: Confidence) -> float:
        """Convert confidence enum to score."""
        return {
            Confidence.HIGH: 0.85,
            Confidence.MEDIUM: 0.6,
            Confidence.LOW: 0.3
        }[confidence]
    
    def count_files(self, source_dir: Path, recursive: bool = True) -> int:
        """Count media files in directory without loading them all."""
        count = 0
        source_dir = Path(source_dir)
        
        if recursive:
            files = source_dir.rglob("*")
        else:
            files = source_dir.glob("*")
        
        for file_path in files:
            if self._is_media_file(file_path):
                count += 1
        
        return count


def scan_directory(source_dir: str, recursive: bool = True) -> List[MediaFile]:
    """Convenience function to scan a directory."""
    scanner = FileScanner()
    return scanner.scan(Path(source_dir), recursive)
