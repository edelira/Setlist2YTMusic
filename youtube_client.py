import os
import json
from typing import Optional, List, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import YOUTUBE_SCOPES, GOOGLE_CLIENT_SECRET_FILE, YOUTUBE_TOKEN_FILE, YOUTUBE_REGION_CODE
from setlist_parser import Track
from video_cache import VideoCache


class YouTubeClient:
    def __init__(self):
        self.service = None
        self.cache = VideoCache()
        self.quota_used = 0
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google and create YouTube service."""
        creds = None
        
        # Load existing token if available
        if os.path.exists(YOUTUBE_TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(YOUTUBE_TOKEN_FILE, YOUTUBE_SCOPES)
            except Exception:
                # Token file is corrupted, we'll re-authenticate
                if os.path.exists(YOUTUBE_TOKEN_FILE):
                    os.remove(YOUTUBE_TOKEN_FILE)
        
        # If there are no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    # Refresh failed, need to re-authenticate
                    creds = None
            
            if not creds:
                if not os.path.exists(GOOGLE_CLIENT_SECRET_FILE):
                    raise RuntimeError(
                        f"Google OAuth client secret file not found: {GOOGLE_CLIENT_SECRET_FILE}\n"
                        "Please download it from Google Cloud Console and place it in the project directory."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    GOOGLE_CLIENT_SECRET_FILE, YOUTUBE_SCOPES
                )
                creds = flow.run_local_server(port=0, prompt="consent")
            
            # Save the credentials for the next run
            with open(YOUTUBE_TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        
        self.service = build("youtube", "v3", credentials=creds)
    
    def create_playlist(self, title: str, description: str, privacy_status: str = "private") -> str:
        """Create a new YouTube playlist and return its ID."""
        try:
            request = self.service.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description
                    },
                    "status": {
                        "privacyStatus": privacy_status
                    }
                }
            )
            response = request.execute()
            return response["id"]
        
        except HttpError as e:
            raise RuntimeError(f"Failed to create playlist: {e}")
    
    def search_video(self, query: str, max_results: int = 3) -> Optional[Tuple[str, str, str]]:
        """Search for a video and return (video_id, title, channel)."""
        try:
            # Track quota usage (search costs 100 units)
            self.quota_used += 100
            
            search_params = {
                "part": "id,snippet",
                "q": query,
                "type": "video",
                "maxResults": max_results,
                "order": "relevance"
            }
            
            if YOUTUBE_REGION_CODE:
                search_params["regionCode"] = YOUTUBE_REGION_CODE
            
            request = self.service.search().list(**search_params)
            response = request.execute()
            
            items = response.get("items", [])
            if not items:
                return None
            
            # Return the first (most relevant) result with metadata
            item = items[0]
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            
            return (video_id, title, channel)
        
        except HttpError as e:
            print(f"Search failed for '{query}': {e}")
            return None
    
    def add_video_to_playlist(self, playlist_id: str, video_id: str) -> bool:
        """Add a video to a playlist. Returns True if successful."""
        try:
            # Track quota usage (playlist insert costs 50 units)
            self.quota_used += 50
            
            request = self.service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        }
                    }
                }
            )
            request.execute()
            return True
        
        except HttpError as e:
            print(f"Failed to add video {video_id} to playlist: {e}")
            return False
    
    def build_search_queries(self, track: Track) -> List[str]:
        """Build optimized search queries for a track."""
        queries = []
        
        # If it's a cover, prioritize the original artist
        if track.is_cover and track.original_artist:
            queries.append(f"{track.title} {track.original_artist}")
            queries.append(f"{track.title} - {track.original_artist}")
            # Fallback to performing artist
            queries.append(f"{track.title} {track.artist}")
        else:
            # Not a cover, use the performing artist
            queries.append(f"{track.title} {track.artist}")
            queries.append(f"{track.title} - {track.artist}")
        
        # Only add one generic fallback to reduce queries
        queries.append(f"{track.title} official")
        
        return queries
    
    def find_best_match(self, track: Track) -> Optional[str]:
        """Find the best YouTube video match for a track with caching."""
        # Check cache first
        cached = self.cache.get(track.title, track.artist)
        if cached:
            print(f"  [CACHED] {track.title} -> {cached.title}")
            return cached.video_id
        
        # Search with optimized queries
        queries = self.build_search_queries(track)
        
        for query in queries:
            result = self.search_video(query)
            if result:
                video_id, title, channel = result
                # Cache the result
                self.cache.set(track.title, track.artist, video_id, title, channel, query)
                return video_id
        
        return None
    
    def get_playlist_url(self, playlist_id: str) -> str:
        """Get the YouTube playlist URL."""
        return f"https://www.youtube.com/playlist?list={playlist_id}"
    
    def get_quota_usage(self) -> dict:
        """Get current quota usage statistics."""
        cache_stats = self.cache.get_stats()
        return {
            'quota_used': self.quota_used,
            'estimated_remaining': 10000 - self.quota_used,  # Free tier limit
            'cache_hits': cache_stats['total_entries'],
            'recent_cache_hits': cache_stats['recent_entries']
        }
    
    def check_quota_limit(self, additional_quota: int = 0) -> bool:
        """Check if we're approaching quota limits."""
        total_quota = self.quota_used + additional_quota
        return total_quota < 9500  # Leave some buffer
    
    def clear_cache(self):
        """Clear the video cache."""
        self.cache.clear_expired()
        print("Cache cleared of expired entries.")
