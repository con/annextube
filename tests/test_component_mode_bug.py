"""Test for component-specific mode metadata schema bug."""
import pytest

from annextube.services.youtube import YouTubeService


@pytest.mark.ai_generated
def test_metadata_to_video_with_stored_schema():
    """Test that metadata_to_video handles our stored schema (video_id) not just yt-dlp schema (id)."""
    
    # Simulate what's stored in metadata.json (our Video.to_dict() schema)
    stored_metadata = {
        "video_id": "test123",  # We use video_id in stored format
        "title": "Test Video",
        "channel_id": "UC123",
        "channel_name": "Test Channel",
        "published_at": "2026-01-01T00:00:00",
        "duration": 120,
        "view_count": 1000,
        "like_count": 50,
        "comment_count": 10,
        "thumbnail_url": "https://example.com/thumb.jpg",
        "license": "standard",
        "privacy_status": "public",
        "availability": "public",
        "tags": [],
        "categories": [],
        "captions_available": [],
        "has_auto_captions": False,
        "download_status": "pending",
        "source_url": "https://youtube.com/watch?v=test123",
        "fetched_at": "2026-01-01T00:00:00"
    }
    
    youtube = YouTubeService()
    
    # This should NOT raise KeyError - should handle both schemas
    video = youtube.metadata_to_video(stored_metadata)
    
    # Verify the video was created correctly
    assert video.video_id == "test123"
    assert video.title == "Test Video"
    assert video.channel_id == "UC123"


@pytest.mark.ai_generated
def test_metadata_to_video_with_ytdlp_schema():
    """Test that metadata_to_video still works with yt-dlp schema (id)."""
    
    # yt-dlp schema uses 'id' not 'video_id'
    ytdlp_metadata = {
        "id": "test456",  # yt-dlp uses 'id'
        "title": "YT-DLP Video",
        "channel_id": "UC456",
        "channel": "YT-DLP Channel",
        "upload_date": "20260101",
        "duration": 180,
        "view_count": 2000,
        "like_count": 100,
        "comment_count": 20,
        "thumbnail": "https://example.com/thumb2.jpg",
        "license": None,
        "availability": "public",
        "tags": ["test"],
        "categories": ["Education"],
        "subtitles": {},
        "automatic_captions": {},
        "webpage_url": "https://youtube.com/watch?v=test456"
    }
    
    youtube = YouTubeService()
    
    # This should work with yt-dlp schema
    video = youtube.metadata_to_video(ytdlp_metadata)
    
    # Verify the video was created correctly
    assert video.video_id == "test456"
    assert video.title == "YT-DLP Video"
    assert video.channel_id == "UC456"
