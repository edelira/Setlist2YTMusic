import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
SETLISTFM_API_KEY = os.getenv("SETLISTFM_API_KEY")
SETLISTFM_API_BASE = "https://api.setlist.fm/rest/1.0"

# YouTube API Configuration
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube"]
YOUTUBE_REGION_CODE = os.getenv("YOUTUBE_REGION_CODE", "US")

# Default Settings
DEFAULT_PRIVACY = os.getenv("DEFAULT_PRIVACY", "private")

# File paths
GOOGLE_CLIENT_SECRET_FILE = "client_secret.json"
YOUTUBE_TOKEN_FILE = "youtube_token.json"
