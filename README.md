# LyricsGenius MCP Server

A Model Context Protocol (MCP) server for accessing song lyrics and artist information from Genius.com via the LyricsGenius library.

## Features

- Search for artists and songs on Genius.com
- Get detailed information about artists
- Retrieve song lyrics
- Get artist albums and top songs
- Analyze lyrics and compare songs using prompts

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

### Resources

- `artist://{artist_name}/info` - Get basic information about an artist
- `song://{artist_name}/{song_title}` - Get lyrics for a specific song

### Tools

- `search_artist(name, max_songs=5)` - Search for an artist and their top songs
- `search_song(title, artist=None)` - Search for a song
- `get_artist_top_songs(artist_name, limit=10)` - Get the top songs by an artist
- `get_artist_albums(artist_name)` - Get albums by an artist

### Prompts

- `analyze_lyrics(artist, song)` - Create a prompt to analyze song lyrics
- `compare_songs(artist, song1, song2)` - Create a prompt to compare two songs by the same artist

## License

MIT