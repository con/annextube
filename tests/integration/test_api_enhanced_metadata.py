"""Integration tests for YouTube API enhanced metadata extraction.

These tests verify:
1. yt-dlp-only mode (no API key) still works
2. API-enhanced mode correctly integrates with YouTubeService
3. Creative Commons video detection works
4. Recording location extraction works
5. Backward compatibility with existing metadata.json files
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from annextube.models.video import Video
from annextube.services.youtube import YouTubeService
from annextube.services.youtube_api import YouTubeAPIMetadataClient


@pytest.mark.ai_generated
def test_youtube_service_without_api_key() -> None:
    """Test YouTubeService works without API key (yt-dlp-only mode)."""
    # Initialize without API key
    service = YouTubeService(youtube_api_key=None)

    # Should initialize successfully
    assert service.api_client is None

    # Verify license defaults to 'standard' when yt-dlp returns None
    metadata = {
        "id": "test123",
        "title": "Test Video",
        "description": "Test",
        "channel_id": "channel123",
        "channel": "Test Channel",
        "upload_date": "20260201",
        "duration": 300,
        "view_count": 1000,
        "like_count": 50,
        "comment_count": 10,
        "thumbnail": "https://example.com/thumb.jpg",
        "license": None,  # yt-dlp returns None
        "availability": "public",
        "tags": [],
        "categories": ["Science"],
        "automatic_captions": {},
        "subtitles": {},
    }

    video = service.metadata_to_video(metadata)

    # Should default to 'standard' when yt-dlp returns None
    assert video.license == "standard"

    # Enhanced metadata fields should be None
    assert video.licensed_content is None
    assert video.embeddable is None
    assert video.made_for_kids is None
    assert video.recording_date is None
    assert video.recording_location is None


@pytest.mark.ai_generated
def test_youtube_service_with_api_key_mock() -> None:
    """Test YouTubeService with API key (mocked API responses)."""
    mock_youtube = MagicMock()
    mock_response = {
        "items": [
            {
                "id": "test123",
                "status": {
                    "license": "creativeCommon",
                    "embeddable": True,
                    "madeForKids": False,
                },
                "contentDetails": {
                    "licensedContent": True,
                    "definition": "hd",
                    "dimension": "2d",
                    "projection": "rectangular",
                },
                "recordingDetails": {
                    "recordingDate": "2026-01-15T10:30:00Z",
                    "location": {
                        "latitude": 37.7749,
                        "longitude": -122.4194,
                    },
                    "locationDescription": "San Francisco, CA",
                },
            }
        ]
    }
    mock_youtube.videos().list().execute.return_value = mock_response

    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = mock_youtube

        # Initialize with API key
        service = YouTubeService(youtube_api_key="test-key")

        # Should have API client
        assert service.api_client is not None

        # Test metadata conversion with API enhancement
        metadata = {
            "id": "test123",
            "title": "Test Video",
            "description": "Test",
            "channel_id": "channel123",
            "channel": "Test Channel",
            "upload_date": "20260201",
            "duration": 300,
            "view_count": 1000,
            "like_count": 50,
            "comment_count": 10,
            "thumbnail": "https://example.com/thumb.jpg",
            "license": None,  # yt-dlp returns None
            "availability": "public",
            "tags": [],
            "categories": ["Science"],
            "automatic_captions": {},
            "subtitles": {},
        }

        video = service.metadata_to_video(metadata, enhance_with_api=True)

        # Should have Creative Commons license from API
        assert video.license == "creativeCommon"

        # Should have enhanced metadata
        assert video.licensed_content is True
        assert video.embeddable is True
        assert video.made_for_kids is False
        assert video.definition == "hd"
        assert video.dimension == "2d"
        assert video.projection == "rectangular"

        # Should have recording details
        assert video.recording_date == datetime.fromisoformat("2026-01-15T10:30:00+00:00")
        assert video.recording_location is not None
        assert video.recording_location["latitude"] == 37.7749
        assert video.recording_location["longitude"] == -122.4194
        assert video.location_description == "San Francisco, CA"


@pytest.mark.ai_generated
def test_creative_commons_detection() -> None:
    """Test that Creative Commons videos are correctly detected via API."""
    mock_youtube = MagicMock()

    # Mock two videos: one CC, one standard license
    mock_response = {
        "items": [
            {
                "id": "cc_video",
                "status": {"license": "creativeCommon"},
            },
            {
                "id": "standard_video",
                "status": {"license": "youtube"},
            },
        ]
    }
    mock_youtube.videos().list().execute.return_value = mock_response

    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = mock_youtube

        client = YouTubeAPIMetadataClient(api_key="test-key")
        result = client.enhance_video_metadata(["cc_video", "standard_video"])

        # CC video should be detected
        assert result["cc_video"]["license"] == "creativeCommon"

        # Standard video should be detected
        assert result["standard_video"]["license"] == "youtube"


@pytest.mark.ai_generated
def test_backward_compatibility_video_model() -> None:
    """Test that Video model is backward compatible with existing metadata.json."""
    # Old metadata.json format (before API enhancement)
    old_metadata = {
        "video_id": "old123",
        "title": "Old Video",
        "description": "Old description",
        "channel_id": "channel123",
        "channel_name": "Test Channel",
        "published_at": "2025-01-01T00:00:00",
        "source_url": "https://youtube.com/watch?v=old123",
        "fetched_at": "2025-01-26T10:00:00",
        "duration": 300,
        "thumbnail_url": "https://example.com/thumb.jpg",
        "view_count": 1000,
        "like_count": 50,
        "comment_count": 10,
        "privacy_status": "public",
        "availability": "public",
        "download_status": "downloaded",
        "tags": ["test"],
        "categories": ["Science"],
        "captions_available": ["en"],
        "has_auto_captions": True,
        "license": "standard",
        # NOTE: No enhanced metadata fields
    }

    # Should load successfully
    video = Video.from_dict(old_metadata)

    assert video.video_id == "old123"
    assert video.license == "standard"

    # Enhanced fields should be None (default)
    assert video.licensed_content is None
    assert video.embeddable is None
    assert video.made_for_kids is None
    assert video.recording_date is None
    assert video.recording_location is None
    assert video.location_description is None
    assert video.definition is None
    assert video.dimension is None
    assert video.projection is None
    assert video.region_restriction is None
    assert video.content_rating is None
    assert video.topic_categories is None


@pytest.mark.ai_generated
def test_backward_compatibility_round_trip() -> None:
    """Test that old metadata can be loaded, modified, and saved."""
    # Old metadata without enhanced fields
    old_data = {
        "video_id": "test123",
        "title": "Test Video",
        "description": "Test",
        "channel_id": "channel123",
        "channel_name": "Test Channel",
        "published_at": "2025-01-01T00:00:00",
        "source_url": "https://youtube.com/watch?v=test123",
        "fetched_at": "2025-01-26T10:00:00",
        "duration": 300,
        "thumbnail_url": "https://example.com/thumb.jpg",
        "view_count": 1000,
        "like_count": 50,
        "comment_count": 10,
        "privacy_status": "public",
        "availability": "public",
        "download_status": "downloaded",
        "tags": [],
        "categories": ["Science"],
        "captions_available": [],
        "has_auto_captions": False,
        "license": "standard",
    }

    # Load old metadata
    video = Video.from_dict(old_data)

    # Convert back to dict
    new_data = video.to_dict()

    # Should have all enhanced fields with None values
    assert "licensed_content" in new_data
    assert new_data["licensed_content"] is None
    assert "embeddable" in new_data
    assert new_data["embeddable"] is None
    assert "made_for_kids" in new_data
    assert new_data["made_for_kids"] is None
    assert "recording_date" in new_data
    assert new_data["recording_date"] is None
    assert "recording_location" in new_data
    assert new_data["recording_location"] is None

    # Old fields should still be present
    assert new_data["video_id"] == "test123"
    assert new_data["license"] == "standard"


@pytest.mark.ai_generated
def test_api_enhancement_optional() -> None:
    """Test that API enhancement is optional (can be disabled)."""
    mock_youtube = MagicMock()

    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = mock_youtube

        # Initialize with API key
        service = YouTubeService(youtube_api_key="test-key")

        metadata = {
            "id": "test123",
            "title": "Test Video",
            "description": "Test",
            "channel_id": "channel123",
            "channel": "Test Channel",
            "upload_date": "20260201",
            "duration": 300,
            "view_count": 1000,
            "like_count": 50,
            "comment_count": 10,
            "thumbnail": "https://example.com/thumb.jpg",
            "license": "standard",
            "availability": "public",
            "tags": [],
            "categories": ["Science"],
            "automatic_captions": {},
            "subtitles": {},
        }

        # Call with enhance_with_api=False
        video = service.metadata_to_video(metadata, enhance_with_api=False)

        # Should NOT have enhanced metadata
        assert video.license == "standard"  # From yt-dlp
        assert video.licensed_content is None
        assert video.embeddable is None

        # API should not have been called
        mock_youtube.videos().list.assert_not_called()


@pytest.mark.ai_generated
def test_api_error_handling_graceful_fallback() -> None:
    """Test that API errors don't break metadata extraction."""
    mock_youtube = MagicMock()
    # Simulate API error
    mock_youtube.videos().list().execute.side_effect = Exception("API error")

    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = mock_youtube

        service = YouTubeService(youtube_api_key="test-key")

        metadata = {
            "id": "test123",
            "title": "Test Video",
            "description": "Test",
            "channel_id": "channel123",
            "channel": "Test Channel",
            "upload_date": "20260201",
            "duration": 300,
            "view_count": 1000,
            "like_count": 50,
            "comment_count": 10,
            "thumbnail": "https://example.com/thumb.jpg",
            "license": "standard",
            "availability": "public",
            "tags": [],
            "categories": ["Science"],
            "automatic_captions": {},
            "subtitles": {},
        }

        # Should not raise exception, should fallback to yt-dlp data
        video = service.metadata_to_video(metadata, enhance_with_api=True)

        # Should use yt-dlp license as fallback
        assert video.license == "standard"

        # Enhanced fields should be None
        assert video.licensed_content is None


@pytest.mark.ai_generated
@pytest.mark.network
def test_real_api_creative_commons_video() -> None:
    """Test with real YouTube API - known Creative Commons video from test channel.

    This test requires YOUTUBE_API_KEY environment variable and network access.
    Marked with @pytest.mark.network so it can be skipped in CI if needed.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        pytest.skip("YOUTUBE_API_KEY not set - skipping real API test")

    # AnnexTube Test Channel - Creative Commons 1 (known CC video)
    video_id = "GhGQV_enM8M"

    client = YouTubeAPIMetadataClient(api_key=api_key)
    result = client.enhance_video_metadata(video_id)

    assert video_id in result
    metadata = result[video_id]

    # Should detect Creative Commons license
    assert metadata["license"] == "creativeCommon"

    # Should have technical details
    assert metadata.get("definition") in ["hd", "sd"]
    assert metadata.get("dimension") in ["2d", "3d"]
    assert metadata.get("projection") in ["rectangular", "360"]


@pytest.mark.ai_generated
@pytest.mark.network
def test_real_api_standard_video() -> None:
    """Test with real YouTube API - standard license video from test channel.

    This test requires YOUTUBE_API_KEY environment variable and network access.
    Marked with @pytest.mark.network so it can be skipped in CI if needed.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        pytest.skip("YOUTUBE_API_KEY not set - skipping real API test")

    # AnnexTube Test Channel - Standard License 1 (known standard license video)
    video_id = "ma84N_6Mybs"

    client = YouTubeAPIMetadataClient(api_key=api_key)
    result = client.enhance_video_metadata(video_id)

    assert video_id in result
    metadata = result[video_id]

    # Should detect standard YouTube license
    assert metadata["license"] == "youtube"

    # Should have embeddable status
    assert isinstance(metadata.get("embeddable"), bool)


@pytest.mark.ai_generated
def test_video_model_all_enhanced_fields() -> None:
    """Test Video model with all enhanced fields populated."""
    video = Video(
        # Required fields
        video_id="test123",
        title="Test Video",
        description="Test description",
        channel_id="channel123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 1, 12, 0, 0),
        source_url="https://youtube.com/watch?v=test123",
        fetched_at=datetime(2026, 1, 26, 10, 0, 0),
        duration=300,
        thumbnail_url="https://example.com/thumb.jpg",
        view_count=1000,
        like_count=50,
        comment_count=10,
        privacy_status="public",
        availability="public",
        download_status="downloaded",
        tags=["test"],
        categories=["Science"],
        captions_available=["en"],
        has_auto_captions=True,
        license="creativeCommon",
        # Enhanced fields
        licensed_content=True,
        embeddable=True,
        made_for_kids=False,
        recording_date=datetime(2026, 1, 15, 10, 30, 0),
        recording_location={"latitude": 37.7749, "longitude": -122.4194},
        location_description="San Francisco, CA",
        definition="hd",
        dimension="2d",
        projection="rectangular",
        region_restriction={"allowed": ["US", "CA"], "blocked": []},
        content_rating={"mpaaRating": "pg"},
        topic_categories=["https://en.wikipedia.org/wiki/Science"],
    )

    # Should serialize and deserialize correctly
    data = video.to_dict()
    restored = Video.from_dict(data)

    assert restored.video_id == video.video_id
    assert restored.license == "creativeCommon"
    assert restored.licensed_content is True
    assert restored.embeddable is True
    assert restored.made_for_kids is False
    assert restored.recording_date == video.recording_date
    assert restored.recording_location == video.recording_location
    assert restored.location_description == video.location_description
    assert restored.definition == "hd"
    assert restored.dimension == "2d"
    assert restored.projection == "rectangular"
    assert restored.region_restriction == video.region_restriction
    assert restored.content_rating == video.content_rating
    assert restored.topic_categories == video.topic_categories
