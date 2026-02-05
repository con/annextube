"""Unit tests for YouTube API metadata client."""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from googleapiclient.errors import HttpError

from annextube.services.youtube_api import (
    YouTubeAPIMetadataClient,
    create_api_client,
)


@pytest.mark.ai_generated
def test_client_initialization_with_api_key() -> None:
    """Test client initializes successfully with API key."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()

        client = YouTubeAPIMetadataClient(api_key="test-key-123")

        assert client.api_key == "test-key-123"
        assert client.youtube is not None
        mock_build.assert_called_once_with(
            "youtube", "v3", developerKey="test-key-123", cache_discovery=False
        )


@pytest.mark.ai_generated
def test_client_initialization_from_env_var() -> None:
    """Test client reads API key from environment variable."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()

        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "env-key-456"}):
            client = YouTubeAPIMetadataClient()

            assert client.api_key == "env-key-456"


@pytest.mark.ai_generated
def test_client_initialization_no_api_key() -> None:
    """Test client raises error when no API key provided."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="YouTube API key required"):
            YouTubeAPIMetadataClient()


@pytest.mark.ai_generated
def test_get_video_details_single_video() -> None:
    """Test fetching details for a single video."""
    mock_youtube = MagicMock()
    mock_response = {
        "items": [
            {
                "id": "video123",
                "status": {"license": "creativeCommon"},
            }
        ]
    }
    mock_youtube.videos().list().execute.return_value = mock_response

    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = mock_youtube

        client = YouTubeAPIMetadataClient(api_key="test-key")
        result = client.get_video_details("video123")

        assert len(result) == 1
        assert "video123" in result
        assert result["video123"]["id"] == "video123"
        assert result["video123"]["status"]["license"] == "creativeCommon"


@pytest.mark.ai_generated
def test_get_video_details_multiple_videos() -> None:
    """Test fetching details for multiple videos (batch request)."""
    mock_youtube = MagicMock()
    mock_response = {
        "items": [
            {"id": "video1", "status": {"license": "youtube"}},
            {"id": "video2", "status": {"license": "creativeCommon"}},
            {"id": "video3", "status": {"license": "youtube"}},
        ]
    }
    mock_youtube.videos().list().execute.return_value = mock_response

    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = mock_youtube

        client = YouTubeAPIMetadataClient(api_key="test-key")
        result = client.get_video_details(["video1", "video2", "video3"])

        assert len(result) == 3
        assert "video1" in result
        assert "video2" in result
        assert "video3" in result


@pytest.mark.ai_generated
def test_get_video_details_max_50_videos() -> None:
    """Test that more than 50 video IDs raises ValueError."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()

        client = YouTubeAPIMetadataClient(api_key="test-key")

        video_ids = [f"video{i}" for i in range(51)]

        with pytest.raises(ValueError, match="Maximum 50 video IDs per request"):
            client.get_video_details(video_ids)


@pytest.mark.ai_generated
def test_get_video_details_empty_list() -> None:
    """Test handling of empty video ID list."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()

        client = YouTubeAPIMetadataClient(api_key="test-key")
        result = client.get_video_details([])

        assert result == {}


@pytest.mark.ai_generated
def test_get_video_details_missing_videos() -> None:
    """Test handling when API doesn't return some requested videos."""
    mock_youtube = MagicMock()
    mock_response = {
        "items": [
            {"id": "video1", "status": {"license": "youtube"}},
            # video2 is missing (deleted/private)
        ]
    }
    mock_youtube.videos().list().execute.return_value = mock_response

    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = mock_youtube

        client = YouTubeAPIMetadataClient(api_key="test-key")
        result = client.get_video_details(["video1", "video2"])

        # Should only return video1
        assert len(result) == 1
        assert "video1" in result
        assert "video2" not in result


@pytest.mark.ai_generated
def test_get_video_details_http_error() -> None:
    """Test handling of HTTP errors from API."""
    mock_youtube = MagicMock()
    mock_response = Mock(status=403)
    mock_youtube.videos().list().execute.side_effect = HttpError(
        resp=mock_response, content=b"Quota exceeded"
    )

    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = mock_youtube

        client = YouTubeAPIMetadataClient(api_key="test-key")
        result = client.get_video_details("video123")

        # Should return empty dict on error
        assert result == {}


@pytest.mark.ai_generated
def test_extract_enhanced_metadata_license() -> None:
    """Test extracting license information."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()
        client = YouTubeAPIMetadataClient(api_key="test-key")

        api_data = {
            "status": {
                "license": "creativeCommon",
                "embeddable": True,
                "madeForKids": False,
            }
        }

        result = client.extract_enhanced_metadata(api_data)

        assert result["license"] == "creativeCommon"
        assert result["embeddable"] is True
        assert result["made_for_kids"] is False


@pytest.mark.ai_generated
def test_extract_enhanced_metadata_content_details() -> None:
    """Test extracting content details."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()
        client = YouTubeAPIMetadataClient(api_key="test-key")

        api_data = {
            "contentDetails": {
                "licensedContent": True,
                "definition": "hd",
                "dimension": "2d",
                "projection": "rectangular",
            }
        }

        result = client.extract_enhanced_metadata(api_data)

        assert result["licensed_content"] is True
        assert result["definition"] == "hd"
        assert result["dimension"] == "2d"
        assert result["projection"] == "rectangular"


@pytest.mark.ai_generated
def test_extract_enhanced_metadata_region_restriction() -> None:
    """Test extracting geographic restrictions."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()
        client = YouTubeAPIMetadataClient(api_key="test-key")

        api_data = {
            "contentDetails": {
                "regionRestriction": {
                    "allowed": ["US", "CA", "GB"],
                    "blocked": ["CN", "KP"],
                }
            }
        }

        result = client.extract_enhanced_metadata(api_data)

        assert result["region_restriction"]["allowed"] == ["US", "CA", "GB"]
        assert result["region_restriction"]["blocked"] == ["CN", "KP"]


@pytest.mark.ai_generated
def test_extract_enhanced_metadata_recording_details() -> None:
    """Test extracting recording location and date."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()
        client = YouTubeAPIMetadataClient(api_key="test-key")

        api_data = {
            "recordingDetails": {
                "recordingDate": "2026-01-15T10:30:00Z",
                "location": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "altitude": 52.0,
                },
                "locationDescription": "San Francisco, CA",
            }
        }

        result = client.extract_enhanced_metadata(api_data)

        assert result["recording_date"] == "2026-01-15T10:30:00Z"
        assert result["recording_location"]["latitude"] == 37.7749
        assert result["recording_location"]["longitude"] == -122.4194
        assert result["recording_location"]["altitude"] == 52.0
        assert result["location_description"] == "San Francisco, CA"


@pytest.mark.ai_generated
def test_extract_enhanced_metadata_topic_categories() -> None:
    """Test extracting topic categories."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()
        client = YouTubeAPIMetadataClient(api_key="test-key")

        api_data = {
            "topicDetails": {
                "topicCategories": [
                    "https://en.wikipedia.org/wiki/Science",
                    "https://en.wikipedia.org/wiki/Technology",
                ]
            }
        }

        result = client.extract_enhanced_metadata(api_data)

        assert len(result["topic_categories"]) == 2
        assert "Science" in result["topic_categories"][0]
        assert "Technology" in result["topic_categories"][1]


@pytest.mark.ai_generated
def test_extract_enhanced_metadata_empty() -> None:
    """Test extracting metadata from empty API response."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()
        client = YouTubeAPIMetadataClient(api_key="test-key")

        api_data = {}

        result = client.extract_enhanced_metadata(api_data)

        # Should return empty dict, not crash
        assert result == {}


@pytest.mark.ai_generated
def test_enhance_video_metadata() -> None:
    """Test convenience method for fetching and extracting metadata."""
    mock_youtube = MagicMock()
    mock_response = {
        "items": [
            {
                "id": "video123",
                "status": {"license": "creativeCommon"},
                "contentDetails": {"definition": "hd"},
            }
        ]
    }
    mock_youtube.videos().list().execute.return_value = mock_response

    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = mock_youtube

        client = YouTubeAPIMetadataClient(api_key="test-key")
        result = client.enhance_video_metadata("video123")

        assert "video123" in result
        assert result["video123"]["license"] == "creativeCommon"
        assert result["video123"]["definition"] == "hd"


@pytest.mark.ai_generated
def test_create_api_client_with_key() -> None:
    """Test helper function creates client when key provided."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()

        client = create_api_client("test-key-789")

        assert client is not None
        assert isinstance(client, YouTubeAPIMetadataClient)
        assert client.api_key == "test-key-789"


@pytest.mark.ai_generated
def test_create_api_client_no_key() -> None:
    """Test helper function returns None when no key provided."""
    client = create_api_client(None)
    assert client is None

    client = create_api_client("")
    assert client is None

    client = create_api_client("   ")
    assert client is None


@pytest.mark.ai_generated
def test_create_api_client_error_handling() -> None:
    """Test helper function handles client creation errors gracefully."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.side_effect = Exception("API initialization failed")

        client = create_api_client("test-key")

        # Should return None instead of raising exception
        assert client is None
