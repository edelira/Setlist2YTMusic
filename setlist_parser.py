import re
import requests
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from config import SETLISTFM_API_KEY, SETLISTFM_API_BASE


@dataclass
class Track:
    title: str
    artist: str  # The performing artist (show artist)
    original_artist: Optional[str] = None  # If it's a cover, the original artist
    is_cover: bool = False
    is_tape: bool = False  # Taped music, not live performance


@dataclass
class SetlistInfo:
    artist: str
    venue: str
    city: str
    date: str
    tracks: List[Track]
    url: str


def parse_setlist_url(url: str) -> str:
    """Extract setlist ID from a setlist.fm URL."""
    # Example: https://www.setlist.fm/setlist/artist-name/2025/venue-city-state-country-53af56b5.html
    url = url.strip().rstrip("/")
    
    if "setlist.fm/setlist/" not in url:
        raise ValueError("URL must be from setlist.fm and contain '/setlist/'")
    
    # Get the last part of the URL (filename)
    filename = url.split("/")[-1]
    
    if not filename.endswith(".html"):
        raise ValueError("URL does not appear to be a valid setlist page (should end in .html)")
    
    # Remove .html extension
    stem = filename[:-5]
    
    # The setlist ID is typically the last part after the final hyphen
    # It's usually 8 hex characters
    parts = stem.split("-")
    setlist_id = parts[-1]
    
    # Validate that it looks like a setlist ID (hexadecimal)
    if not re.match(r"^[0-9a-fA-F]{6,16}$", setlist_id):
        raise ValueError(f"Could not extract valid setlist ID from URL. Got: {setlist_id}")
    
    return setlist_id


def fetch_setlist_data(setlist_id: str) -> Dict[str, Any]:
    """Fetch setlist data from the setlist.fm API."""
    if not SETLISTFM_API_KEY:
        raise RuntimeError("SETLISTFM_API_KEY environment variable is required")
    
    headers = {
        "Accept": "application/json",
        "x-api-key": SETLISTFM_API_KEY,
        "Accept-Language": "en",
        "User-Agent": "Setlist2YTMusic/1.0"
    }
    
    url = f"{SETLISTFM_API_BASE}/setlist/{setlist_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            raise RuntimeError("Setlist not found. Please check the URL and try again.")
        elif response.status_code == 401:
            raise RuntimeError("Invalid setlist.fm API key. Please check your configuration.")
        elif response.status_code == 429:
            raise RuntimeError("Rate limit exceeded. Please try again later.")
        
        response.raise_for_status()
        return response.json()
        
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch setlist data: {str(e)}")


def parse_setlist_data(data: Dict[str, Any], original_url: str) -> SetlistInfo:
    """Parse the JSON response from setlist.fm API into a SetlistInfo object."""
    
    # Extract basic info
    artist = data.get("artist", {}).get("name", "Unknown Artist")
    venue_info = data.get("venue", {})
    venue = venue_info.get("name", "Unknown Venue")
    city_info = venue_info.get("city", {})
    city = f"{city_info.get('name', 'Unknown City')}, {city_info.get('stateProvince', city_info.get('country', {}).get('name', ''))}"
    date = data.get("eventDate", "Unknown Date")
    
    # Extract tracks from sets
    tracks = []
    sets = data.get("sets", {}).get("set", [])
    
    for set_data in sets:
        songs = set_data.get("song", [])
        
        for song in songs:
            # Skip if it's marked as tape (not a live performance)
            if song.get("tape", False):
                continue
            
            title = song.get("name")
            if not title:
                continue
            
            # Check if it's a cover
            is_cover = "cover" in song and song["cover"]
            original_artist = None
            
            if is_cover and isinstance(song["cover"], dict):
                original_artist = song["cover"].get("name")
            
            track = Track(
                title=title,
                artist=artist,
                original_artist=original_artist,
                is_cover=is_cover,
                is_tape=song.get("tape", False)
            )
            
            tracks.append(track)
    
    return SetlistInfo(
        artist=artist,
        venue=venue,
        city=city,
        date=date,
        tracks=tracks,
        url=original_url
    )


def get_setlist_from_url(url: str) -> SetlistInfo:
    """Main function to get setlist info from a setlist.fm URL."""
    setlist_id = parse_setlist_url(url)
    data = fetch_setlist_data(setlist_id)
    return parse_setlist_data(data, url)
