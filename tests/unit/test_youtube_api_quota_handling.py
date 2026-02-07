"""Unit tests for YouTube API quota exceeded handling."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from googleapiclient.errors import HttpError

from annextube.lib.quota_manager import QuotaExceededError, QuotaManager
from annextube.services.youtube_api import YouTubeAPICommentsService, YouTubeAPIMetadataClient


@pytest.mark.ai_generated
class TestMetadataClientQuotaHandling:
    """Tests for quota exceeded handling in YouTubeAPIMetadataClient."""

    def test_quota_exceeded_with_auto_wait_disabled(self):
        """Test quota exceeded raises error when auto-wait disabled."""
        mock_youtube = MagicMock()
        mock_response = Mock(status=403)
        mock_youtube.videos().list().execute.side_effect = HttpError(
            resp=mock_response, content=b'quotaExceeded'
        )

        with patch("annextube.services.youtube_api.build") as mock_build:
            mock_build.return_value = mock_youtube

            # Disable auto-wait
            quota_manager = QuotaManager(enabled=False)
            client = YouTubeAPIMetadataClient(api_key="test-key", quota_manager=quota_manager)

            with pytest.raises(QuotaExceededError, match="Quota resets at midnight Pacific Time"):
                client.get_video_details("video123")

    def test_quota_exceeded_with_excessive_wait_time(self):
        """Test quota exceeded raises error when wait time exceeds max."""
        mock_youtube = MagicMock()
        mock_response = Mock(status=403)
        mock_youtube.videos().list().execute.side_effect = HttpError(
            resp=mock_response, content=b'quotaExceeded'
        )

        with patch("annextube.services.youtube_api.build") as mock_build:
            mock_build.return_value = mock_youtube

            # Set very low max wait time
            quota_manager = QuotaManager(enabled=True, max_wait_hours=0.001)  # ~3 seconds
            client = YouTubeAPIMetadataClient(api_key="test-key", quota_manager=quota_manager)

            with pytest.raises(QuotaExceededError, match="hours away"):
                client.get_video_details("video123")

    def test_quota_exceeded_with_auto_retry(self):
        """Test quota exceeded waits and retries operation successfully."""
        mock_youtube = MagicMock()
        mock_response_403 = Mock(status=403)
        mock_response_success = {
            "items": [
                {
                    "id": "video123",
                    "status": {"license": "youtube"},
                }
            ]
        }

        # First call: quota exceeded, second call: success
        mock_youtube.videos().list().execute.side_effect = [
            HttpError(resp=mock_response_403, content=b'quotaExceeded'),
            mock_response_success,
        ]

        with patch("annextube.services.youtube_api.build") as mock_build:
            mock_build.return_value = mock_youtube

            # Use a mock quota manager to avoid actual sleeping
            quota_manager = MagicMock(spec=QuotaManager)
            quota_manager.handle_quota_exceeded.return_value = None  # Simulates wait completed

            client = YouTubeAPIMetadataClient(api_key="test-key", quota_manager=quota_manager)
            result = client.get_video_details("video123")

            # Should retry and succeed
            assert len(result) == 1
            assert "video123" in result
            quota_manager.handle_quota_exceeded.assert_called_once()

    def test_non_quota_http_errors_not_caught(self):
        """Test that non-quota HTTP errors are handled normally."""
        mock_youtube = MagicMock()
        mock_response = Mock(status=403)
        # Different error (not quotaExceeded)
        mock_youtube.videos().list().execute.side_effect = HttpError(
            resp=mock_response, content=b'Access denied'
        )

        with patch("annextube.services.youtube_api.build") as mock_build:
            mock_build.return_value = mock_youtube

            client = YouTubeAPIMetadataClient(api_key="test-key")
            result = client.get_video_details("video123")

            # Should return empty dict (logged error, not raised)
            assert result == {}


@pytest.mark.ai_generated
class TestCommentsServiceQuotaHandling:
    """Tests for quota exceeded handling in YouTubeAPICommentsService."""

    def test_quota_exceeded_with_auto_wait_disabled(self):
        """Test quota exceeded raises error when auto-wait disabled."""
        mock_youtube = MagicMock()
        mock_response = Mock(status=403)
        mock_youtube.commentThreads().list().execute.side_effect = HttpError(
            resp=mock_response, content=b'quotaExceeded'
        )

        with patch("annextube.services.youtube_api.build") as mock_build:
            mock_build.return_value = mock_youtube

            # Disable auto-wait
            quota_manager = QuotaManager(enabled=False)
            client = YouTubeAPICommentsService(api_key="test-key", quota_manager=quota_manager)

            with pytest.raises(QuotaExceededError, match="Quota resets at midnight Pacific Time"):
                client.fetch_comments("video123")

    def test_quota_exceeded_with_auto_retry(self):
        """Test quota exceeded waits and retries operation successfully."""
        mock_youtube = MagicMock()
        mock_response_403 = Mock(status=403)
        mock_response_success = {
            "items": [
                {
                    "snippet": {
                        "topLevelComment": {
                            "id": "comment123",
                            "snippet": {
                                "textDisplay": "Great video!",
                                "authorDisplayName": "Test User",
                                "likeCount": 5,
                                "publishedAt": "2026-01-15T10:00:00Z",
                            },
                        }
                    }
                }
            ]
        }

        # First call: quota exceeded, second call: success
        mock_youtube.commentThreads().list().execute.side_effect = [
            HttpError(resp=mock_response_403, content=b'quotaExceeded'),
            mock_response_success,
        ]

        with patch("annextube.services.youtube_api.build") as mock_build:
            mock_build.return_value = mock_youtube

            # Use a mock quota manager to avoid actual sleeping
            quota_manager = MagicMock(spec=QuotaManager)
            quota_manager.handle_quota_exceeded.return_value = None  # Simulates wait completed

            client = YouTubeAPICommentsService(api_key="test-key", quota_manager=quota_manager)
            result = client.fetch_comments("video123")

            # Should retry and succeed
            assert len(result) == 1
            quota_manager.handle_quota_exceeded.assert_called_once()

    def test_comments_disabled_not_treated_as_quota_error(self):
        """Test that commentsDisabled error is handled separately."""
        mock_youtube = MagicMock()
        mock_response = Mock(status=403)
        mock_youtube.commentThreads().list().execute.side_effect = HttpError(
            resp=mock_response, content=b'commentsDisabled'
        )

        with patch("annextube.services.youtube_api.build") as mock_build:
            mock_build.return_value = mock_youtube

            client = YouTubeAPICommentsService(api_key="test-key")
            result = client.fetch_comments("video123")

            # Should return empty list (not raise error)
            assert result == []

    def test_non_quota_403_errors_raised(self):
        """Test that non-quota 403 errors are raised."""
        mock_youtube = MagicMock()
        mock_response = Mock(status=403)
        # Different 403 error (not quotaExceeded or commentsDisabled)
        mock_youtube.commentThreads().list().execute.side_effect = HttpError(
            resp=mock_response, content=b'Forbidden: Access denied'
        )

        with patch("annextube.services.youtube_api.build") as mock_build:
            mock_build.return_value = mock_youtube

            client = YouTubeAPICommentsService(api_key="test-key")

            # Should raise the HttpError
            with pytest.raises(HttpError):
                client.fetch_comments("video123")


@pytest.mark.ai_generated
def test_default_quota_manager_initialization():
    """Test that both services initialize with default quota manager."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()

        # Test metadata client
        metadata_client = YouTubeAPIMetadataClient(api_key="test-key")
        assert metadata_client.quota_manager is not None
        assert isinstance(metadata_client.quota_manager, QuotaManager)
        assert metadata_client.quota_manager.enabled is True
        assert metadata_client.quota_manager.max_wait_hours == 48

        # Test comments service
        comments_service = YouTubeAPICommentsService(api_key="test-key")
        assert comments_service.quota_manager is not None
        assert isinstance(comments_service.quota_manager, QuotaManager)
        assert comments_service.quota_manager.enabled is True
        assert comments_service.quota_manager.max_wait_hours == 48


@pytest.mark.ai_generated
def test_custom_quota_manager_injection():
    """Test that custom quota manager can be injected."""
    with patch("annextube.services.youtube_api.build") as mock_build:
        mock_build.return_value = MagicMock()

        custom_quota_manager = QuotaManager(enabled=False, max_wait_hours=24)

        # Test metadata client
        metadata_client = YouTubeAPIMetadataClient(api_key="test-key", quota_manager=custom_quota_manager)
        assert metadata_client.quota_manager is custom_quota_manager
        assert metadata_client.quota_manager.enabled is False
        assert metadata_client.quota_manager.max_wait_hours == 24

        # Test comments service
        comments_service = YouTubeAPICommentsService(api_key="test-key", quota_manager=custom_quota_manager)
        assert comments_service.quota_manager is custom_quota_manager
        assert comments_service.quota_manager.enabled is False
        assert comments_service.quota_manager.max_wait_hours == 24
