#!/usr/bin/env python3
"""
LyricsGenius MCP Server
A Model Context Protocol server that provides tools and resources for accessing song lyrics
and artist information from Genius.com through the LyricsGenius library.
"""
import os
from typing import Dict, List, Optional, Union
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

import lyricsgenius
from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP, Image

# Load environment variables from .env file
load_dotenv()

# Get Genius API token from environment variable
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
if not GENIUS_TOKEN:
    print("WARNING: GENIUS_TOKEN environment variable not found.")
    print("Please set it with your Genius API token.")
    print("You can get a token at: https://genius.com/api-clients")


@dataclass
class AppContext:
    """Application context for the MCP server."""
    genius: lyricsgenius.Genius


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with Genius API client."""
    # Initialize Genius client
    if not GENIUS_TOKEN:
        raise ValueError(
            "GENIUS_TOKEN environment variable not set. "
            "Please set it with your Genius API token."
        )
    
    genius = lyricsgenius.Genius(
        GENIUS_TOKEN,
        verbose=True,
        remove_section_headers=True,
        skip_non_songs=False,
        excluded_terms=["(Remix)", "(Live)"]
    )
    
    try:
        yield AppContext(genius=genius)
    finally:
        # No special cleanup needed for Genius client
        pass


# Create FastMCP server with lifespan support
mcp = FastMCP(
    "LyricsGenius",
    description="Access song lyrics and artist information from Genius.com",
    dependencies=["lyricsgenius", "python-dotenv"],
    lifespan=app_lifespan
)


# Resource to get basic information about an artist
@mcp.resource("artist://{artist_name}/info")
def get_artist_info(artist_name: str, ctx: Context) -> str:
    """Get basic information about an artist."""
    genius = ctx.request_context.lifespan_context.genius
    
    artist = genius.search_artist(artist_name, max_songs=1, sort="title", 
                                 include_features=False, get_full_info=True)
    if not artist:
        return f"Could not find artist: {artist_name}"
    
    info = (
        f"# {artist.name}\n\n"
        f"**Alternate names**: {', '.join(artist.alternate_names) if artist.alternate_names else 'None'}\n\n"
        f"**Description**:\n{artist.description['plain'] if artist.description and 'plain' in artist.description else 'No description available'}\n\n"
        f"**Followers count**: {artist.followers_count}\n"
        f"**Popular songs count**: {artist.songs_count if hasattr(artist, 'songs_count') else 'Unknown'}\n"
    )
    return info


# Resource to get lyrics of a song
@mcp.resource("song://{artist_name}/{song_title}")
def get_song_lyrics(artist_name: str, song_title: str, ctx: Context) -> str:
    """Get lyrics for a specific song by an artist."""
    genius = ctx.request_context.lifespan_context.genius
    
    song = genius.search_song(song_title, artist_name)
    if not song:
        return f"Could not find song '{song_title}' by {artist_name}"
    
    result = (
        f"# {song.title} by {song.artist}\n\n"
        f"**Album**: {song.album if song.album else 'Unknown'}\n"
        f"**Release date**: {song.release_date if song.release_date else 'Unknown'}\n\n"
        f"## Lyrics\n\n{song.lyrics}"
    )
    return result


# Tool to search for artists
@mcp.tool()
def search_artist(name: str, max_songs: int = 5, ctx: Context) -> str:
    """
    Search for an artist on Genius and return their top songs.
    
    Args:
        name: The name of the artist to search for
        max_songs: Maximum number of songs to return (default: 5)
    
    Returns:
        Information about the artist and their top songs
    """
    genius = ctx.request_context.lifespan_context.genius
    
    artist = genius.search_artist(name, max_songs=max_songs, sort="popularity", 
                                 include_features=False)
    if not artist:
        return f"Could not find artist: {name}"
    
    songs_list = "\n".join([f"- {song.title}" for song in artist.songs])
    
    result = (
        f"# {artist.name}\n\n"
        f"**Top {len(artist.songs)} songs**:\n{songs_list}\n\n"
        f"Use the song resource to get lyrics: `song://{artist.name}/SONG_TITLE`"
    )
    return result


# Tool to search for songs
@mcp.tool()
def search_song(title: str, artist: Optional[str] = None, ctx: Context) -> str:
    """
    Search for a song on Genius.
    
    Args:
        title: The title of the song to search for
        artist: The name of the artist (optional)
    
    Returns:
        Information about the song and how to access its lyrics
    """
    genius = ctx.request_context.lifespan_context.genius
    
    song = genius.search_song(title, artist)
    if not song:
        artist_msg = f" by {artist}" if artist else ""
        return f"Could not find song '{title}'{artist_msg}"
    
    result = (
        f"# {song.title} by {song.artist}\n\n"
        f"**Album**: {song.album if song.album else 'Unknown'}\n"
        f"**Release date**: {song.release_date if song.release_date else 'Unknown'}\n\n"
        f"To get full lyrics, use the resource: `song://{song.artist}/{song.title}`"
    )
    return result


# Tool to get top songs by an artist
@mcp.tool()
def get_artist_top_songs(artist_name: str, limit: int = 10, ctx: Context) -> str:
    """
    Get the top songs by an artist.
    
    Args:
        artist_name: The name of the artist
        limit: Maximum number of songs to return (default: 10)
    
    Returns:
        List of the artist's top songs
    """
    genius = ctx.request_context.lifespan_context.genius
    
    artist = genius.search_artist(artist_name, max_songs=limit, sort="popularity", 
                                 include_features=False)
    if not artist:
        return f"Could not find artist: {artist_name}"
    
    songs_list = "\n".join([
        f"{i+1}. **{song.title}** - {song.album if song.album else 'Unknown album'}" 
        for i, song in enumerate(artist.songs)
    ])
    
    result = (
        f"# Top {len(artist.songs)} Songs by {artist.name}\n\n"
        f"{songs_list}\n\n"
        f"To get lyrics for any song, use: `song://{artist.name}/SONG_TITLE`"
    )
    return result


# Tool to get artist's albums
@mcp.tool()
def get_artist_albums(artist_name: str, ctx: Context) -> str:
    """
    Get albums by an artist.
    
    Args:
        artist_name: The name of the artist
    
    Returns:
        List of the artist's albums
    """
    genius = ctx.request_context.lifespan_context.genius
    
    # First get the artist ID
    artist_search = genius.search_artists(artist_name)
    if not artist_search or not artist_search.get('sections', []):
        return f"Could not find artist: {artist_name}"
    
    hits = []
    for section in artist_search.get('sections', []):
        hits.extend(section.get('hits', []))
    
    if not hits:
        return f"No artists found matching: {artist_name}"
    
    artist_id = None
    artist_name_result = None
    for hit in hits:
        if hit.get('type') == 'artist':
            artist_id = hit.get('result', {}).get('id')
            artist_name_result = hit.get('result', {}).get('name')
            break
    
    if not artist_id:
        return f"Could not find artist ID for: {artist_name}"
    
    # Get the artist's albums
    albums = genius.artist_albums(artist_id)
    if not albums or not albums.get('albums', []):
        return f"No albums found for artist: {artist_name_result or artist_name}"
    
    albums_list = albums.get('albums', [])
    albums_info = "\n".join([
        f"- **{album.get('name')}** ({album.get('release_date_components', {}).get('year', 'Unknown')})"
        for album in albums_list
    ])
    
    result = (
        f"# Albums by {artist_name_result or artist_name}\n\n"
        f"{albums_info}\n\n"
        f"Total: {len(albums_list)} albums"
    )
    return result


# Example prompt for analyzing song lyrics
@mcp.prompt()
def analyze_lyrics(artist: str, song: str) -> str:
    """
    Create a prompt to analyze song lyrics.
    
    Args:
        artist: Artist name
        song: Song title
    """
    return (
        f"Please analyze the lyrics of the song '{song}' by {artist}.\n"
        f"Consider the themes, literary devices, cultural context, and meaning.\n\n"
        f"First, I'll help you access the lyrics using the LyricsGenius MCP server."
    )


# Example prompt for comparing songs by the same artist
@mcp.prompt()
def compare_songs(artist: str, song1: str, song2: str) -> str:
    """
    Create a prompt to compare two songs by the same artist.
    
    Args:
        artist: Artist name
        song1: First song title
        song2: Second song title
    """
    return (
        f"Please compare and contrast the lyrics and themes of '{song1}' and '{song2}' by {artist}.\n"
        f"Consider how these songs relate to each other, evolution in style, recurring themes, and differences.\n\n"
        f"First, I'll help you access the lyrics of both songs using the LyricsGenius MCP server."
    )


if __name__ == "__main__":
    # Run the server
    mcp.run()