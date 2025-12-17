"""TMDB API client for media identification."""

import requests
from typing import Optional, List, Dict, Any
from difflib import SequenceMatcher

from .models import TMDBMatch, MediaType, ParsedInfo


class TMDBClient:
    """Client for The Movie Database API."""
    
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.params = {"api_key": api_key}  # type: ignore
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a GET request to TMDB API."""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"TMDB API error: {e}")
            return None
    
    def search_movie(self, title: str, year: Optional[int] = None) -> List[TMDBMatch]:
        """Search for movies by title and optional year."""
        params = {"query": title}
        if year:
            params["year"] = str(year)
        
        data = self._get("/search/movie", params)
        if not data or "results" not in data:
            return []
        
        matches = []
        for result in data["results"][:5]:  # Top 5 results
            match = TMDBMatch(
                tmdb_id=result["id"],
                title=result.get("title", ""),
                original_title=result.get("original_title", ""),
                year=self._extract_year(result.get("release_date", "")),
                overview=result.get("overview", ""),
                poster_path=result.get("poster_path"),
                vote_average=result.get("vote_average", 0),
                media_type=MediaType.MOVIE
            )
            # Calculate confidence
            match.confidence_score = self._calculate_confidence(
                title, match.title, year, match.year
            )
            matches.append(match)
        
        # Sort by confidence
        matches.sort(key=lambda m: m.confidence_score, reverse=True)
        return matches
    
    def search_tv(self, title: str, year: Optional[int] = None) -> List[TMDBMatch]:
        """Search for TV shows by title and optional year."""
        params = {"query": title}
        if year:
            params["first_air_date_year"] = str(year)
        
        data = self._get("/search/tv", params)
        if not data or "results" not in data:
            return []
        
        matches = []
        for result in data["results"][:5]:  # Top 5 results
            match = TMDBMatch(
                tmdb_id=result["id"],
                title=result.get("name", ""),
                original_title=result.get("original_name", ""),
                year=self._extract_year(result.get("first_air_date", "")),
                overview=result.get("overview", ""),
                poster_path=result.get("poster_path"),
                vote_average=result.get("vote_average", 0),
                media_type=MediaType.TV_SHOW
            )
            match.confidence_score = self._calculate_confidence(
                title, match.title, year, match.year
            )
            matches.append(match)
        
        matches.sort(key=lambda m: m.confidence_score, reverse=True)
        return matches
    
    def get_tv_episode(self, tv_id: int, season: int, episode: int) -> Optional[Dict]:
        """Get details for a specific TV episode."""
        data = self._get(f"/tv/{tv_id}/season/{season}/episode/{episode}")
        return data
    
    def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """Get detailed info for a movie."""
        return self._get(f"/movie/{movie_id}")
    
    def get_tv_details(self, tv_id: int) -> Optional[Dict]:
        """Get detailed info for a TV show."""
        return self._get(f"/tv/{tv_id}")
    
    def identify_media(self, parsed_info: ParsedInfo) -> Optional[TMDBMatch]:
        """
        Identify media from parsed filename info.
        Returns the best match or None if confidence is too low.
        """
        if parsed_info.is_tv_show():
            return self._identify_tv_show(parsed_info)
        else:
            return self._identify_movie(parsed_info)
    
    def _identify_movie(self, info: ParsedInfo) -> Optional[TMDBMatch]:
        """Identify a movie from parsed info."""
        matches = self.search_movie(info.title, info.year)
        if not matches:
            return None
        
        best_match = matches[0]
        return best_match
    
    def _identify_tv_show(self, info: ParsedInfo) -> Optional[TMDBMatch]:
        """Identify a TV show and episode from parsed info."""
        matches = self.search_tv(info.title, info.year)
        if not matches:
            return None
        
        best_match = matches[0]
        
        # Get episode details
        if info.season and info.episode:
            episode_data = self.get_tv_episode(
                best_match.tmdb_id, info.season, info.episode
            )
            if episode_data:
                best_match.season_number = info.season
                best_match.episode_number = info.episode
                best_match.episode_title = episode_data.get("name", "")
        
        return best_match
    
    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from a date string like '2023-05-20'."""
        if date_str and len(date_str) >= 4:
            try:
                return int(date_str[:4])
            except ValueError:
                pass
        return None
    
    def _calculate_confidence(
        self, 
        query_title: str, 
        result_title: str,
        query_year: Optional[int],
        result_year: Optional[int]
    ) -> float:
        """Calculate confidence score for a match."""
        # Title similarity (0-1)
        title_sim = SequenceMatcher(
            None, 
            query_title.lower(), 
            result_title.lower()
        ).ratio()
        
        # Year match bonus
        year_score = 0.0
        if query_year and result_year:
            if query_year == result_year:
                year_score = 0.2  # Exact match bonus
            elif abs(query_year - result_year) == 1:
                year_score = 0.1  # Off by one year
        elif not query_year:
            # No year in query - slight penalty
            year_score = -0.1
        
        # Calculate final score
        confidence = (title_sim * 0.8) + year_score
        
        # Clamp to 0-1
        return max(0.0, min(1.0, confidence))
    
    def test_connection(self) -> bool:
        """Test if the API key is valid."""
        data = self._get("/configuration")
        return data is not None


def create_client(api_key: str) -> TMDBClient:
    """Create a TMDB client instance."""
    return TMDBClient(api_key)
