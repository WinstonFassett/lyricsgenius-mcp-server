# LyricsGenius MCP Server

A Model Context Protocol (MCP) server for accessing song lyrics and artist information from Genius.com via the LyricsGenius library.

## Features

- Search for artists and songs on Genius.com
- Get detailed information about artists
- Retrieve song lyrics
- Get artist albums and top songs
- Get album tracks
- Search across different content types (songs, artists, albums, etc.)

## Requirements

- Python 3.8+
- LyricsGenius API token (get one from https://genius.com/api-clients)

## Installation

1. Clone this repository
   ```
   git clone <repository-url>
   cd lyricsgenius-mcp
   ```

2. Create a virtual environment
   ```
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies
   ```
   uv pip install -r requirements.txt
   ```

4. Set up your Genius API token
   - Create a copy of `.env` and rename it to `.env`
   - Replace `your_token_here` with your actual Genius API token

## Usage

### Running the server directly

```
python server.py
```

### Installing in Claude Desktop

```
mcp install server.py
```

### Running with MCP development tools

```
mcp dev server.py
```

## Server Capabilities

### Tools

- `search(query, search_type=None, per_page=10, page=1)` - Search Genius for artists, songs, albums or other content
- `get_lyrics(title, artist=None)` - Get lyrics for a song directly
- `get_artist_songs(artist_identifier, per_page=20, sort="popularity")` - Get songs by an artist
- `get_artist_albums(artist_identifier)` - Get albums by an artist
- `get_album_tracks(album_identifier)` - Get tracks from an album by its ID or name

## License

MIT