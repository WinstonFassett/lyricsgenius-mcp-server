#!/usr/bin/env python3
"""
LyricsGenius MCP Server
A simplified Model Context Protocol server that provides tools for accessing song lyrics
and artist information from Genius.com through the LyricsGenius library.
"""
import sys
import os
from enum import Enum
from typing import Dict, List, Optional, Union, Any

import lyricsgenius
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Image

# Import our reusable MCP logging module
from mcp_logging import configure_logging

# Set up logger with our server name (including -server suffix)
logger = configure_logging("lyricsgenius-mcp-server")

# Define search type enum for better parameter handling
class SearchType(str, Enum):
    """Type of content to search for on Genius."""
    SONG = "song"
    ARTIST = "artist" 
    ALBUM = "album"
    LYRIC = "lyric"
    VIDEO = "video"
    ARTICLE = "article"
    USER = "user"
    MULTI = "multi"
    ALL = ""  # Empty string means no filter

# Load environment variables from .env file
load_dotenv()

# Get Genius API token from environment variable
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
if not GENIUS_TOKEN:
  raise EnvironmentError(
    "GENIUS_TOKEN environment variable not found. "
    "Please set it with your Genius API token. "
    "You can get a token at: https://genius.com/api-clients"
  )

# Helper function to clean lyrics
def get_clean_lyrics(song):
    """Clean lyrics by removing header text and extra information."""
    if not song or not song.lyrics:
        return "No lyrics found"
    
    # Try to extract the actual lyrics after the "Lyrics" marker
    if "Lyrics" in song.lyrics:
        lyrics_position = song.lyrics.find("Lyrics")
        
        # Only use the split if "Lyrics" appears in the first half of the text
        # This helps avoid splitting on lyrics that contain the word "Lyrics"
        if lyrics_position < len(song.lyrics) / 2:
            actual_lyrics = song.lyrics.split("Lyrics", 1)[1]
            # If the split resulted in empty lyrics, fall back to the original
            if not actual_lyrics.strip():
                actual_lyrics = song.lyrics
        else:
            actual_lyrics = song.lyrics
    else:
        actual_lyrics = song.lyrics
    
    return actual_lyrics

# Helper function to find artist ID from name or ID
def _find_artist_id(artist_identifier):
    """
    Find artist ID from name or ID.
    
    Args:
        artist_identifier: Artist name (string) or ID (number/string)
    
    Returns:
        tuple: (artist_id, artist_name) or (None, None) if not found
    """
    global genius
    
    # Check if artist_identifier might be an ID already
    if isinstance(artist_identifier, (int, str)) and str(artist_identifier).isdigit():
        try:
            # Try to get artist directly by ID
            artist_data = genius.artist(artist_identifier)
            if artist_data and 'artist' in artist_data:
                artist = artist_data['artist']
                return artist['id'], artist['name']
        except Exception as e:
            logger.debug(f"Failed to get artist by ID, falling back to search: {e}")
    
    # If we're here, we need to search for the artist by name
    try:
        # Convert to string in case we got a number
        artist_name = str(artist_identifier)
        search_result = genius.search_artists(artist_name)
        
        if not search_result or 'sections' not in search_result:
            return None, None
        
        # Extract artist from search results
        hits = []
        for section in search_result.get('sections', []):
            hits.extend(section.get('hits', []))
        
        # Look for matching artist
        for hit in hits:
            if hit.get('type') == 'artist':
                artist_info = hit.get('result', {})
                return artist_info.get('id'), artist_info.get('name')
                
        return None, None
    except Exception as e:
        logger.error(f"Error in _find_artist_id: {str(e)}")
        return None, None

# Helper function to find album ID from name or ID
def _find_album_id(album_identifier):
    """
    Find album ID from name or ID.
    
    Args:
        album_identifier: Album name (string) or ID (number/string)
    
    Returns:
        tuple: (album_id, album_name, artist_name) or (None, None, None) if not found
    """
    global genius
    
    # Check if album_identifier might be an ID already
    if isinstance(album_identifier, (int, str)) and str(album_identifier).isdigit():
        try:
            # Try to get album directly by ID
            album_data = genius.album(album_identifier)
            if album_data and 'album' in album_data:
                album = album_data['album']
                artist_name = album.get('artist', {}).get('name', 'Unknown Artist')
                return album['id'], album['name'], artist_name
        except Exception as e:
            logger.debug(f"Failed to get album by ID, falling back to search: {e}")
    
    # If we're here, we need to search for the album by name
    try:
        # Search for albums with this name
        search_result = genius.search(album_identifier, type_="album")
        
        if not search_result or 'hits' not in search_result:
            return None, None, None
        
        # Look for matching album
        for hit in search_result['hits']:
            if hit.get('type') == 'album':
                album_info = hit.get('result', {})
                artist_info = album_info.get('artist', {})
                artist_name = artist_info.get('name', 'Unknown Artist')
                return album_info.get('id'), album_info.get('name'), artist_name
                
        return None, None, None
    except Exception as e:
        logger.error(f"Error in _find_album_id: {str(e)}")
        return None, None, None

# Initialize global Genius client immediately at module level
genius = None
if GENIUS_TOKEN:
    logger.info("Initializing Genius client with token")
    genius = lyricsgenius.Genius(
        GENIUS_TOKEN,
        verbose=False,  # Disable verbose output to avoid MCP parsing issues
        remove_section_headers=True,  # Clean up lyrics formatting
        skip_non_songs=True,  # Skip non-song results
        excluded_terms=[],  # Don't exclude any terms by default
        timeout=15,  # Set timeout to 15 seconds to prevent hanging
        retries=2    # Add retries for better reliability
    )        
else:
    logger.error("Cannot initialize Genius client - missing API token")
    
logger.info("Genius client initialized successfully")

# Create FastMCP server
mcp = FastMCP(
    "LyricsGenius",
    description="Access song lyrics and artist information from Genius.com",
    dependencies=["lyricsgenius", "python-dotenv"]
)

# ----- CORE SEARCH TOOLS -----

@mcp.tool()
def search(query: str, search_type: Optional[str] = None, per_page: int = 10, page: int = 1) -> str:
    """
    Search Genius for artists, songs, albums or other content.
    
    Args:
        query: The search term to look for
        search_type: Type of content to search for ('song', 'artist', 'album', 'lyric', 'video', 'article', 'user', 'multi')
        per_page: Number of results per page (max 50)
        page: Page number for pagination
    
    Returns:
        Search results in a readable format
    """
    global genius
    if not genius:
        return "Error: Genius client not initialized. Please set GENIUS_TOKEN."
    
    try:
        # Print parameters for debugging - using logger
        logger.debug(f"Search called with: query='{query}', search_type='{search_type}', per_page={per_page}, page={page}")
        
        # Ensure per_page is within limits
        per_page = min(per_page, 50)
        
        # Let the lyricsgenius lib handle the search type logic
        if search_type:
            logger.debug(f"Using search with type={search_type} for: '{query}'")
            results = genius.search(query, per_page=per_page, page=page, type_=search_type)
        else:
            logger.debug(f"Using default search for: '{query}'")
            results = genius.search(query, per_page=per_page, page=page)
            
        # Debug the results structure
        logger.debug(f"Result keys: {list(results.keys() if results else [])}")
            
        # Extract hits from results
        hits = []
        if 'hits' in results:
            hits = results['hits']
        elif 'sections' in results:
            for section in results['sections']:
                if 'hits' in section:
                    hits.extend(section.get('hits', []))
        
        if not hits:
            return f"No results found for '{query}'"
            
        # Log the number of hits and their types
        hit_types = [hit.get('type', 'unknown') for hit in hits]
        logger.debug(f"Search returned {len(hits)} hits with types: {hit_types}")
        
        # Build response based on result type
        output = [f"# Search Results for '{query}'"]
        if search_type:
            output[0] += f" (type: {search_type})"
        
        for hit in hits:
            result = hit.get('result', {})
            result_type = hit.get('type', 'unknown')
            
            if result_type == 'song':
                # Debug artist name resolution
                title = result.get('title', 'Unknown Title')
                artist_name = result.get('artist_name') or result.get('primary_artist', {}).get('name')
                
                # Fallback if we still don't have an artist name
                if not artist_name:
                    artist = result.get('primary_artist') or {}
                    artist_name = artist.get('name', 'Unknown Artist')
                    
                output.append(f"- 🎵 **{title}** by {artist_name}")
            
            elif result_type == 'artist':
                name = result.get('name', 'Unknown Artist')
                artist_id = result.get('id')
                output.append(f"- 👤 **{name}** (ID: {artist_id})")
                output.append(f"  `get_artist_songs(artist_identifier=\"{artist_id}\")` | `get_artist_albums(artist_identifier=\"{artist_id}\")`")
            
            elif result_type == 'album':
                name = result.get('name', 'Unknown Album')
                album_id = result.get('id')
                
                # Better handling of album artist
                artist_info = result.get('artist', {})
                artist_name = artist_info.get('name', 'Unknown Artist')
                
                output.append(f"- 💿 **{name}** by {artist_name} (ID: {album_id})")
                output.append(f"  `get_album_tracks(album_identifier=\"{album_id}\")`")
            
            else:
                name = result.get('name') or result.get('title', 'Unknown Item')
                output.append(f"- **{result_type.capitalize()}**: {name}")
        
        return "\n\n".join(output)
    except Exception as e:
        logger.error(f"ERROR in search: {str(e)}")
        return f"Error during search: {str(e)}"


@mcp.tool()
def get_lyrics(title: str, artist: Optional[str] = None) -> str:
    """
    Get lyrics for a song directly.
    
    Args:
        title: The title of the song to get lyrics for
        artist: The name of the artist (optional, improves search accuracy)
    
    Returns:
        The lyrics of the song with metadata
    """
    global genius
    if not genius:
        return "Error: Genius client not initialized. Please set GENIUS_TOKEN."
    
    try:
        logger.info(f"Getting lyrics for song: {title} by {artist}")
        
        # Only use artist parameter if it's not None and not empty
        if artist and artist.strip():
            logger.debug("Searching with both title and artist")
            song = genius.search_song(title, artist)
        else:
            logger.debug("Searching with just title")
            song = genius.search_song(title)
        
        if not song:
            artist_msg = f" by {artist}" if artist else ""
            return f"Could not find song '{title}'{artist_msg}"
        
        # Use our clean lyrics helper
        clean_lyrics = get_clean_lyrics(song)
        
        result = (
            f"# {song.title} by {song.artist}\n\n"
            f"**Album**: {song.album if song.album else 'Unknown'}\n"
            # Include release date if available
            f"{f'**Release date**: {song.year}\\n' if hasattr(song, 'year') and song.year else ''}"
            f"## Lyrics\n\n{clean_lyrics}"
        )
        return result
    except Exception as e:
        logger.error(f"Error in get_lyrics: {str(e)}")
        return f"Error retrieving lyrics: {str(e)}"


@mcp.tool()
def get_artist_songs(artist_identifier: str, per_page: int = 20, sort: str = "popularity") -> str:
    """
    Get songs by an artist.
    
    Args:
        artist_identifier: The name or ID of the artist
        per_page: Number of songs to return
        sort: How to sort the results ("popularity", "title")
    
    Returns:
        List of the artist's songs
    """
    global genius
    if not genius:
        return "Error: Genius client not initialized. Please set GENIUS_TOKEN."
    
    try:
        logger.info(f"Getting songs for artist identifier: {artist_identifier}")
        
        # Find the artist ID using our helper function
        artist_id, artist_name = _find_artist_id(artist_identifier)
        
        if not artist_id:
            return f"Could not find artist with identifier: {artist_identifier}"
            
        # Get songs for this artist
        logger.debug(f"Found artist {artist_name} (ID: {artist_id}), fetching songs...")
        
        # Use artist_songs which is more efficient 
        songs_data = genius.artist_songs(artist_id, per_page=per_page, sort=sort)
        songs = songs_data.get('songs', [])
        
        if not songs:
            return f"No songs found for artist: {artist_name}"
        
        # Format output - don't try to display album since it's often missing
        songs_list = "\n".join([
            f"{i+1}. **{song.get('title')}**"
            for i, song in enumerate(songs[:per_page])
        ])
        
        result = (
            f"# Songs by {artist_name}\n\n"
            f"{songs_list}\n\n"
            f"Use `get_lyrics(title=\"Song Title\", artist=\"{artist_name}\")`"
        )
        return result
    except Exception as e:
        logger.error(f"Error in get_artist_songs: {str(e)}")
        return f"Error getting songs: {str(e)}"


@mcp.tool()
def get_artist_albums(artist_identifier: str) -> str:
    """
    Get albums by an artist.
    
    Args:
        artist_identifier: The name or ID of the artist
    
    Returns:
        List of the artist's albums with release years
    """
    global genius
    if not genius:
        return "Error: Genius client not initialized. Please set GENIUS_TOKEN."
    
    try:
        logger.info(f"Getting albums for artist identifier: {artist_identifier}")
        
        # Find the artist ID using our helper function
        artist_id, artist_name = _find_artist_id(artist_identifier)
        
        if not artist_id:
            return f"Could not find artist with identifier: {artist_identifier}"
            
        # Get albums
        logger.debug(f"Found artist {artist_name} (ID: {artist_id}), fetching albums...")
        
        albums = genius.artist_albums(artist_id)
        if not albums or not albums.get('albums', []):
            return f"No albums found for artist: {artist_name}"
        
        albums_list = albums.get('albums', [])
        albums_info = "\n".join([
            f"- **{album.get('name')}** ({album.get('release_date_components', {}).get('year', 'Unknown')}) - `get_album_tracks(album_identifier=\"{album.get('id')}\")`"
            for album in albums_list[:20]  # Limit to 20 albums to prevent too much data
        ])
        
        total_albums = len(albums_list)
        shown_albums = min(20, total_albums)
        
        result = (
            f"# Albums by {artist_name}\n\n"
            f"{albums_info}\n\n"
        )
        
        if total_albums > shown_albums:
            result += f"Showing {shown_albums} of {total_albums} total albums"
        else:
            result += f"Total: {total_albums} albums"
            
        return result
    except Exception as e:
        logger.error(f"Error in get_artist_albums: {str(e)}")
        return f"Error getting albums: {str(e)}"


@mcp.tool()
def get_album_tracks(album_identifier: str) -> str:
    """
    Get tracks from an album by its ID or name.
    
    Args:
        album_identifier: The Genius album ID or name
    
    Returns:
        List of tracks in the album
    """
    global genius
    if not genius:
        return "Error: Genius client not initialized. Please set GENIUS_TOKEN."
    
    try:
        logger.info(f"Getting tracks for album identifier: {album_identifier}")
        
        # Find the album ID using our helper function
        album_id, album_name, artist_name = _find_album_id(album_identifier)
        
        if not album_id:
            return f"Could not find album with identifier: {album_identifier}"
        
        logger.debug(f"Found album {album_name} (ID: {album_id}) by {artist_name}")
            
        # Try to get the album data
        album_data = genius.album(album_id)
        if not album_data or not album_data.get('album'):
            return f"Could not find album with ID: {album_id}"
            
        album = album_data.get('album', {})
        album_name = album.get('name', album_name)  # Use the album name from data or from our helper
        artist_name = album.get('artist', {}).get('name', artist_name)  # Use artist name from data or helper
        
        logger.debug(f"Album structure keys: {list(album.keys())}")
        
        # Let's try getting tracks through the performance_groups which should contain track listings
        if 'performance_groups' in album and album['performance_groups']:
            groups = album['performance_groups']
            logger.debug(f"Found {len(groups)} performance groups")
            
            # Build track list from performance_groups which contains actual tracks
            track_list = []
            track_num = 1
            
            for group in groups:
                # Check if this group represents a track (should have a song key)
                if 'song' in group:
                    song_data = group['song']
                    if isinstance(song_data, dict) and 'title' in song_data:
                        title = song_data['title']
                        track_list.append(f"{track_num}. **{title}**")
                        track_num += 1
            
            # If we found tracks, return them
            if track_list:
                result = (
                    f"# Tracks on {album_name} by {artist_name}\n\n"
                    f"{'\n'.join(track_list)}"
                )
                return result
                
        # Fallback to checking song_performances if performance_groups didn't work
        if 'song_performances' in album and album['song_performances']:
            performances = album['song_performances']
            logger.debug(f"Found {len(performances)} performances")
            
            # Print more debug info about the structure
            if performances:
                perf = performances[0]
                logger.debug(f"First performance keys: {list(perf.keys())}")
                if 'song' in perf:
                    logger.debug(f"First performance song keys: {list(perf['song'].keys())}")
            
            # Try a different approach - check for tracks in primary_artists or tracks
            if 'tracks' in album:
                tracks = album['tracks']
                track_list = []
                for i, track in enumerate(tracks):
                    title = track.get('title', "Unknown Track")
                    track_list.append(f"{i+1}. **{title}**")
                if track_list:
                    result = (
                        f"# Tracks on {album_name} by {artist_name}\n\n"
                        f"{'\n'.join(track_list)}"
                    )
                    return result
        
        # If we got here, we need to try accessing data differently
        # Some albums have the track listing in a different format
        logger.debug("Trying alternative methods to find tracks...")
        
        # Try to access through the API directly with a different endpoint
        try:
            album_with_tracks = genius.album_tracks(album_id)
            if album_with_tracks and 'tracks' in album_with_tracks:
                tracks = album_with_tracks['tracks']
                track_list = []
                for i, track in enumerate(tracks):
                    if isinstance(track, dict):
                        title = track.get('song', {}).get('title', "Unknown Track")
                        track_list.append(f"{i+1}. **{title}**")
                
                if track_list:
                    result = (
                        f"# Tracks on {album_name} by {artist_name}\n\n"
                        f"{'\n'.join(track_list)}"
                    )
                    return result
        except Exception as e:
            logger.error(f"Failed to get tracks through album_tracks API: {str(e)}")
        
        return f"Could not extract track titles for album: {album_name} by {artist_name}. This album may have incomplete data on Genius."
    except Exception as e:
        logger.error(f"Error in get_album_tracks: {str(e)}")
        return f"Error getting album tracks: {str(e)}"


if __name__ == "__main__":
    # Run the server
    mcp.run()