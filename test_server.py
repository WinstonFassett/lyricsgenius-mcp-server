#!/usr/bin/env python3
"""
Integration tests for the LyricsGenius MCP Server.

This file contains tests that use real data from the Genius API
to verify the MCP server functions correctly with actual artists,
albums, and songs.

Usage:
    pytest -xvs test_server.py
"""
import os
import sys
import pytest
from unittest import mock
import logging

# Import our server module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server


class TestLyricsGeniusMCPRealData:
    """Integration tests with real Genius API data."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test environment with necessary config."""
        # Disable verbose logging during tests
        logging.basicConfig(level=logging.ERROR)
        
        # Check if Genius client is initialized
        if server.genius is None:
            pytest.skip("GENIUS_TOKEN not set - skipping integration tests")
            
    def test_get_lyrics_real(self):
        """Test the get_lyrics tool with a real song."""
        # Use a very popular song that's unlikely to be removed from Genius
        result = server.get_lyrics("Bohemian Rhapsody", "Queen")
        assert "Bohemian Rhapsody" in result
        assert "Queen" in result
        assert "Is this the real life" in result
    
    def test_get_artist_songs_real(self):
        """Test the get_artist_songs tool with a real artist."""
        # Use a well-established artist
        result = server.get_artist_songs("The Beatles")
        assert "Songs by The Beatles" in result
        # Should have multiple songs
        assert len(result.split("**")) > 5  # Each song title is wrapped in ** markers
        
    def test_get_artist_albums_real(self):
        """Test the get_artist_albums tool with a real artist."""
        # Use a well-established artist
        result = server.get_artist_albums("Michael Jackson")
        assert "Albums by Michael Jackson" in result
        # Well-known album that should always be present
        assert "Thriller" in result
        
    def test_get_album_tracks_real(self):
        """Test the get_album_tracks tool with a real album."""
        # Search for the album by name and artist
        search_result = server.search("Thriller Michael Jackson", search_type="album")
        
        # Extract album ID from search results
        album_id = None
        lines = search_result.splitlines()
        
        # Look for Michael Jackson's Thriller album ID
        for line in lines:
            if "Michael Jackson" in line and "Thriller" in line and "(ID:" in line:
                # Extract ID from format like "**Thriller** by Michael Jackson (ID: 11769)"
                try:
                    album_id = line.split("(ID:")[1].split(")")[0].strip()
                    break
                except (IndexError, KeyError):
                    continue
            
            # Also look for ID in the function call format
            elif "get_album_tracks" in line and "album_identifier" in line and "11769" in line:
                try:
                    album_id = line.split('album_identifier="')[1].split('"')[0]
                    break
                except (IndexError, KeyError):
                    continue
        
        # If we found an ID, get the tracks and verify
        if not album_id:
            # Try with known ID as fallback
            album_id = "11769"  # Known ID for Michael Jackson's Thriller
            
        # Get tracks with the album ID
        result = server.get_album_tracks(album_id)
        
        # Check for expected content
        assert "Tracks on Thriller" in result
        assert "Billie Jean" in result or "Beat It" in result
        
    def test_search_real(self):
        """Test the search tool with real data."""
        result = server.search("Beyoncé", search_type="artist")
        assert "Beyoncé" in result
        
        # Test song search
        result = server.search("Hey Jude", search_type="song")
        assert "Hey Jude" in result
        assert "The Beatles" in result


# For quick manual testing without pytest
if __name__ == "__main__":
    try:
        import pytest
        sys.exit(pytest.main(["-xvs", __file__]))
    except ImportError:
        print("Pytest not found. Please install pytest to run tests.")
        sys.exit(1)