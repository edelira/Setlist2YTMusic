# Setlist2YTMusic

Convert setlist.fm setlists to YouTube Music playlists automatically.

## Quick Start

1. **Install Python dependencies:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Get API keys:**
   - **setlist.fm API key**: Visit [setlist.fm API settings](https://www.setlist.fm/settings/api) and request a key
   - **Google OAuth credentials**: 
     - Go to [Google Cloud Console](https://console.cloud.google.com/)
     - Create a new project or select existing one
     - Enable YouTube Data API v3
     - Create OAuth 2.0 credentials (Desktop Application)
     - Download the JSON file and save as `client_secret.json` in this directory

3. **Configure environment:**
   ```powershell
   copy .env.example .env
   # Edit .env and add your setlist.fm API key
   ```

4. **Run the application:**
   ```powershell
   python main.py "https://www.setlist.fm/setlist/artist/2025/venue-12345678.html"
   ```

## Usage

### Basic usage:
```powershell
python main.py "https://www.setlist.fm/setlist/artist/2025/venue-city-12345678.html"
```

### Options:
- `--privacy private|unlisted|public` - Set playlist privacy (default: private)
- `--dry-run` - Preview matches without creating playlist
- `--show-tracks` - Display track list before processing

### Examples:
```powershell
# Create a private playlist (default)
python main.py "https://www.setlist.fm/setlist/..."

# Create an unlisted playlist
python main.py --privacy unlisted "https://www.setlist.fm/setlist/..."

# Preview what would be found without creating playlist
python main.py --dry-run "https://www.setlist.fm/setlist/..."

# Show track list and ask for confirmation
python main.py --show-tracks "https://www.setlist.fm/setlist/..."
```

## How it works

1. **Parse setlist URL** - Extracts setlist ID from the setlist.fm URL
2. **Fetch setlist data** - Uses setlist.fm API to get song list, artist, venue, date
3. **Authenticate with Google** - Uses OAuth to access your YouTube account (one-time setup)
4. **Create playlist** - Creates a new YouTube playlist with generated title and description
5. **Find matches** - Searches YouTube for each song using smart query strategies:
   - For covers: tries original artist first, then performing artist
   - Multiple query variations: "Song Artist", "Song - Artist", "Song official", etc.
6. **Add to playlist** - Adds best matches to the playlist in original setlist order

## Features

- **Smart matching**: Handles covers correctly by prioritizing original artists
- **Beautiful CLI**: Rich terminal interface with progress bars and colored output
- **Flexible privacy**: Create private, unlisted, or public playlists
- **Dry run mode**: Preview results before creating the actual playlist
- **Error handling**: Graceful handling of missing songs and API errors
- **Attribution**: Playlist description includes original setlist.fm URL

## Requirements

- Python 3.8+
- setlist.fm API key (free)
- Google Cloud project with YouTube Data API v3 enabled
- OAuth 2.0 credentials for desktop application

## File Structure

- `main.py` - Main CLI application
- `setlist_parser.py` - setlist.fm API integration and URL parsing
- `youtube_client.py` - YouTube API integration and authentication
- `config.py` - Configuration management
- `client_secret.json` - Google OAuth credentials (download from Google Cloud Console)
- `youtube_token.json` - Stored YouTube auth token (auto-generated after first login)
- `.env` - Environment variables (copy from .env.example)

## Troubleshooting

### "SETLISTFM_API_KEY environment variable is required"
- Copy `.env.example` to `.env`
- Add your setlist.fm API key to the `.env` file

### "Google OAuth client secret file not found"
- Download OAuth credentials from Google Cloud Console
- Save as `client_secret.json` in the project directory

### "Setlist not found"
- Check that the URL is correct and the setlist exists
- Make sure the URL is from setlist.fm and ends in `.html`

### "Rate limit exceeded"
- Wait a few minutes and try again
- setlist.fm has rate limits on their API

### Songs not found
- Some songs may not have good matches on YouTube
- Try searching manually for missing songs
- Cover songs are prioritized by original artist, which may not always be available

## Privacy and Data

- Your Google authentication tokens are stored locally in `youtube_token.json`
- The app only requests YouTube playlist creation/modification permissions
- No data is sent to external servers beyond Google and setlist.fm APIs
- Playlist descriptions include attribution to the original setlist.fm URL
