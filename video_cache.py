import json
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class CacheEntry:
    video_id: str
    title: str
    channel: str
    timestamp: str
    search_query: str

class VideoCache:
    def __init__(self, cache_file: str = "video_cache.json"):
        self.cache_file = cache_file
        self.cache: Dict[str, CacheEntry] = {}
        self.load_cache()
    
    def load_cache(self):
        """Load cache from file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, entry_data in data.items():
                        self.cache[key] = CacheEntry(**entry_data)
            except (json.JSONDecodeError, KeyError):
                # If cache is corrupted, start fresh
                self.cache = {}
    
    def save_cache(self):
        """Save cache to file."""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            data = {}
            for key, entry in self.cache.items():
                data[key] = {
                    'video_id': entry.video_id,
                    'title': entry.title,
                    'channel': entry.channel,
                    'timestamp': entry.timestamp,
                    'search_query': entry.search_query
                }
            json.dump(data, f, indent=2)
    
    def get_cache_key(self, song_title: str, artist: str) -> str:
        """Generate a cache key for a song."""
        return f"{song_title.lower().strip()}|{artist.lower().strip()}"
    
    def get(self, song_title: str, artist: str) -> Optional[CacheEntry]:
        """Get cached video for a song."""
        key = self.get_cache_key(song_title, artist)
        entry = self.cache.get(key)
        
        if entry:
            # Check if cache entry is still valid (7 days)
            try:
                cache_time = datetime.fromisoformat(entry.timestamp)
                if datetime.now() - cache_time < timedelta(days=7):
                    return entry
                else:
                    # Remove expired entry
                    del self.cache[key]
                    self.save_cache()
            except ValueError:
                # Invalid timestamp, remove entry
                del self.cache[key]
                self.save_cache()
        
        return None
    
    def set(self, song_title: str, artist: str, video_id: str, 
            title: str, channel: str, search_query: str):
        """Cache a video result."""
        key = self.get_cache_key(song_title, artist)
        entry = CacheEntry(
            video_id=video_id,
            title=title,
            channel=channel,
            timestamp=datetime.now().isoformat(),
            search_query=search_query
        )
        self.cache[key] = entry
        self.save_cache()
    
    def clear_expired(self):
        """Remove expired cache entries."""
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self.cache.items():
            try:
                cache_time = datetime.fromisoformat(entry.timestamp)
                if now - cache_time >= timedelta(days=7):
                    expired_keys.append(key)
            except ValueError:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self.save_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now()
        total_entries = len(self.cache)
        recent_entries = 0
        
        for entry in self.cache.values():
            try:
                cache_time = datetime.fromisoformat(entry.timestamp)
                if now - cache_time < timedelta(days=1):
                    recent_entries += 1
            except ValueError:
                pass
        
        return {
            'total_entries': total_entries,
            'recent_entries': recent_entries,
            'cache_file_size': os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0
        }
