"""Unit tests for ExportService channel.json generation."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from annextube.services.export import ExportService


@pytest.fixture
def mock_archive(tmp_path):
    """Create a mock archive with config and video metadata."""
    # Create config
    config_dir = tmp_path / ".annextube"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text("""
[[sources]]
url = "https://www.youtube.com/@TestChannel"
type = "channel"
enabled = true
""")

    # Create videos directory with sample metadata
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()

    video1_dir = videos_dir / "2024" / "01" / "video1"
    video1_dir.mkdir(parents=True)
    video1_meta = {
        "video_id": "test_video_1",
        "channel_id": "UC_TEST_CHANNEL_ID",
        "channel_name": "Test Channel",
        "title": "Test Video 1",
        "published_at": "2024-01-01T00:00:00",
        "duration": 300,
        "view_count": 1000,
        "like_count": 50,
        "comment_count": 10,
    }
    (video1_dir / "metadata.json").write_text(json.dumps(video1_meta))

    # Create video.mkv symlink (simulate git-annex)
    video_file = video1_dir / "video.mkv"
    # Create a small file to symlink to
    actual_file = tmp_path / ".git" / "annex" / "objects" / "test1"
    actual_file.parent.mkdir(parents=True, exist_ok=True)
    actual_file.write_bytes(b"x" * 1024 * 1024 * 10)  # 10 MB
    video_file.symlink_to(actual_file)

    # Create videos.tsv
    videos_tsv = videos_dir / "videos.tsv"
    videos_tsv.write_text(
        "video_id\ttitle\tchannel_id\tchannel_name\tpublished_at\t"
        "duration\tview_count\tlike_count\tcomment_count\t"
        "thumbnail_url\tdownload_status\tsource_url\tpath\n"
        "test_video_1\tTest Video 1\tUC_TEST_CHANNEL_ID\tTest Channel\t2024-01-01T00:00:00\t"
        "300\t1000\t50\t10\t\ttracked\thttps://youtube.com/watch?v=test_video_1\t2024/01/video1\n"
    )

    # Create playlists directory
    playlists_dir = tmp_path / "playlists"
    playlists_dir.mkdir()
    playlist1_dir = playlists_dir / "Test_Playlist"
    playlist1_dir.mkdir()
    (playlist1_dir / "playlist.json").write_text(json.dumps({"playlist_id": "PLtest1"}))

    return tmp_path


@pytest.mark.ai_generated
def test_generate_channel_json_basic(mock_archive):
    """Test basic channel.json generation without API."""
    service = ExportService(mock_archive)

    # Mock yt-dlp to return channel metadata
    with patch('annextube.services.youtube.YouTubeService') as mock_youtube_service:
        mock_youtube = MagicMock()
        mock_youtube.get_channel_metadata.return_value = {
            "channel_id": "UC_TEST_CHANNEL_ID",
            "channel_name": "Test Channel",
            "description": "Test channel description",
            "custom_url": "TestChannel",
            "avatar_url": "https://example.com/avatar.jpg",
            "subscriber_count": 5000,
            "video_count": 100,
        }
        mock_youtube_service.return_value = mock_youtube

        # Generate channel.json
        output_path = service.generate_channel_json()

        assert output_path.exists()
        assert output_path == mock_archive / "channel.json"

        # Verify content
        with open(output_path) as f:
            data = json.load(f)

        assert data["channel_id"] == "UC_TEST_CHANNEL_ID"
        assert data["name"] == "Test Channel"
        assert data["description"] == "Test channel description"
        assert data["custom_url"] == "TestChannel"
        assert data["subscriber_count"] == 5000
        assert data["video_count"] == 1  # From archive, not YouTube
        assert data["playlist_count"] == 1
        assert data["avatar_url"] == "https://example.com/avatar.jpg"

        # Check archive stats
        stats = data["archive_stats"]
        assert stats["total_videos_archived"] == 1
        assert stats["first_video_date"] == "2024-01-01T00:00:00"
        assert stats["last_video_date"] == "2024-01-01T00:00:00"
        assert stats["total_duration_seconds"] == 300
        assert stats["total_size_bytes"] == 10 * 1024 * 1024  # 10 MB


@pytest.mark.ai_generated
def test_generate_channel_json_with_youtube_api(mock_archive):
    """Test channel.json generation with YouTube API (preferred method)."""
    service = ExportService(mock_archive)

    # Mock YouTube API client
    with patch('annextube.services.youtube_api.create_api_client') as mock_create_client:
        mock_api_client = MagicMock()
        mock_api_client.get_channel_details.return_value = {
            "channel_id": "UC_TEST_CHANNEL_ID",
            "channel_name": "Test Channel",
            "description": "Complete API description",
            "custom_url": "TestChannel",
            "avatar_url": "https://example.com/avatar_hd.jpg",
            "banner_url": "https://example.com/banner.jpg",
            "country": "US",
            "subscriber_count": 5000,
            "video_count": 100,
            "created_at": "2020-01-01T00:00:00Z",
        }
        mock_create_client.return_value = mock_api_client

        # Set API key environment variable
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_api_key"}):
            output_path = service.generate_channel_json()

        # Verify API was used
        mock_create_client.assert_called_once_with("test_api_key")
        mock_api_client.get_channel_details.assert_called_once_with("UC_TEST_CHANNEL_ID")

        # Verify content has complete metadata
        with open(output_path) as f:
            data = json.load(f)

        assert data["description"] == "Complete API description"
        assert data["banner_url"] == "https://example.com/banner.jpg"
        assert data["country"] == "US"
        assert data["created_at"] == "2020-01-01T00:00:00Z"


@pytest.mark.ai_generated
def test_generate_channel_json_fallback_to_ytdlp(mock_archive):
    """Test fallback to yt-dlp when API fails."""
    service = ExportService(mock_archive)

    # Mock API to fail
    with patch('annextube.services.youtube_api.create_api_client') as mock_create_client:
        mock_create_client.return_value = None  # API client creation fails

        # Mock yt-dlp
        with patch('annextube.services.youtube.YouTubeService') as mock_youtube_service:
            mock_youtube = MagicMock()
            mock_youtube.get_channel_metadata.return_value = {
                "channel_id": "UC_TEST_CHANNEL_ID",
                "channel_name": "Test Channel",
                "description": "yt-dlp description",
                "custom_url": "TestChannel",
                "avatar_url": "https://example.com/avatar.jpg",
                "subscriber_count": 5000,
                "video_count": 100,
            }
            mock_youtube_service.return_value = mock_youtube

            with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
                output_path = service.generate_channel_json()

            # Verify yt-dlp was used
            mock_youtube.get_channel_metadata.assert_called_once()

            with open(output_path) as f:
                data = json.load(f)

            assert data["description"] == "yt-dlp description"


@pytest.mark.ai_generated
def test_generate_channel_json_fallback_to_archive(mock_archive):
    """Test ultimate fallback when both API and yt-dlp fail."""
    service = ExportService(mock_archive)

    # Mock both to fail
    with patch('annextube.services.youtube_api.create_api_client') as mock_create_client:
        mock_create_client.return_value = None

        with patch('annextube.services.youtube.YouTubeService') as mock_youtube_service:
            mock_youtube = MagicMock()
            mock_youtube.get_channel_metadata.side_effect = Exception("yt-dlp failed")
            mock_youtube_service.return_value = mock_youtube

            output_path = service.generate_channel_json()

            # Verify it still works with minimal metadata
            with open(output_path) as f:
                data = json.load(f)

            # Should have channel ID and name from videos
            assert data["channel_id"] == "UC_TEST_CHANNEL_ID"
            assert data["name"] == "Test Channel"

            # But description, avatar, etc. should be empty
            assert data["description"] == ""
            assert data["avatar_url"] == ""
            assert data["banner_url"] == ""


@pytest.mark.ai_generated
def test_generate_channel_json_idempotent(mock_archive):
    """Test that generate_channel_json is idempotent."""
    service = ExportService(mock_archive)

    with patch('annextube.services.youtube.YouTubeService') as mock_youtube_service:
        mock_youtube = MagicMock()
        mock_youtube.get_channel_metadata.return_value = {
            "channel_id": "UC_TEST_CHANNEL_ID",
            "channel_name": "Test Channel",
            "description": "Test description",
            "custom_url": "TestChannel",
            "avatar_url": "https://example.com/avatar.jpg",
            "subscriber_count": 5000,
            "video_count": 100,
        }
        mock_youtube_service.return_value = mock_youtube

        # Generate twice
        path1 = service.generate_channel_json()
        with open(path1) as f:
            data1 = json.load(f)

        path2 = service.generate_channel_json()
        with open(path2) as f:
            data2 = json.load(f)

        # Paths should be the same
        assert path1 == path2

        # Content should be identical except timestamps
        assert data1["channel_id"] == data2["channel_id"]
        assert data1["name"] == data2["name"]
        assert data1["archive_stats"] == data2["archive_stats"]


@pytest.mark.ai_generated
def test_generate_channel_json_no_sources_error(tmp_path):
    """Test error when no sources configured."""
    # Create empty config
    config_dir = tmp_path / ".annextube"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text("[sources]\n")

    service = ExportService(tmp_path)

    with pytest.raises(ValueError, match="No sources configured"):
        service.generate_channel_json()


@pytest.mark.ai_generated
def test_generate_channel_json_no_channel_sources_error(tmp_path):
    """Test error when no channel sources found."""
    # Create config with only playlist source
    config_dir = tmp_path / ".annextube"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text("""
[[sources]]
url = "https://www.youtube.com/playlist?list=PLtest"
type = "playlist"
enabled = true
""")

    service = ExportService(tmp_path)

    with pytest.raises(ValueError, match="No channel sources found"):
        service.generate_channel_json()


@pytest.mark.ai_generated
def test_parse_channel_id_from_channel_url(mock_archive):
    """Test parsing channel ID from /channel/ URL format."""
    service = ExportService(mock_archive)

    channel_id = service._parse_channel_id_from_url(
        "https://www.youtube.com/channel/UC_TEST_CHANNEL_ID"
    )

    assert channel_id == "UC_TEST_CHANNEL_ID"


@pytest.mark.ai_generated
def test_parse_channel_id_from_username_url(mock_archive):
    """Test parsing channel ID from @username URL (uses archive)."""
    service = ExportService(mock_archive)

    channel_id = service._parse_channel_id_from_url(
        "https://www.youtube.com/@TestChannel"
    )

    # Should resolve from video metadata
    assert channel_id == "UC_TEST_CHANNEL_ID"


@pytest.mark.ai_generated
def test_get_channel_name_from_videos(mock_archive):
    """Test extracting channel name from video metadata."""
    service = ExportService(mock_archive)

    channel_name = service._get_channel_name_from_videos()

    assert channel_name == "Test Channel"


@pytest.mark.ai_generated
def test_get_channel_name_from_videos_empty(tmp_path):
    """Test extracting channel name when no videos exist."""
    service = ExportService(tmp_path)

    channel_name = service._get_channel_name_from_videos()

    assert channel_name == ""


@pytest.mark.ai_generated
def test_download_channel_avatar(mock_archive):
    """Test downloading channel avatar."""
    service = ExportService(mock_archive)

    # Mock urllib and magic
    fake_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00'  # PNG header

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = fake_image_data
        mock_urlopen.return_value = mock_response

        with patch('magic.Magic') as mock_magic_class:
            mock_magic = MagicMock()
            mock_magic.from_buffer.return_value = 'image/png'
            mock_magic_class.return_value = mock_magic

            with patch.object(service, '_download_channel_avatar', wraps=service._download_channel_avatar):
                # Download avatar
                avatar_path = service._download_channel_avatar("https://example.com/avatar.png")

                assert avatar_path is not None
                assert avatar_path.name == "channel_avatar.png"
                assert avatar_path.exists()

                # Verify content
                with open(avatar_path, 'rb') as f:
                    assert f.read() == fake_image_data


@pytest.mark.ai_generated
def test_download_channel_avatar_already_exists(mock_archive):
    """Test that avatar download is skipped if file already exists."""
    service = ExportService(mock_archive)

    # Create existing avatar
    existing_avatar = mock_archive / "channel_avatar.jpg"
    existing_avatar.write_bytes(b"existing")

    # Try to download (should skip)
    with patch('urllib.request.urlopen') as mock_urlopen:
        avatar_path = service._download_channel_avatar("https://example.com/avatar.jpg")

        # Should return existing file without downloading
        assert avatar_path == existing_avatar
        assert avatar_path.read_bytes() == b"existing"
        mock_urlopen.assert_not_called()


@pytest.mark.ai_generated
def test_download_channel_avatar_download_failure(mock_archive):
    """Test graceful handling of download failure."""
    service = ExportService(mock_archive)

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = Exception("Network error")

        avatar_path = service._download_channel_avatar("https://example.com/avatar.jpg")

        assert avatar_path is None


@pytest.mark.ai_generated
def test_mime_to_extension():
    """Test MIME type to extension mapping."""
    service = ExportService(Path("/tmp"))

    assert service._mime_to_extension("image/jpeg") == "jpg"
    assert service._mime_to_extension("image/png") == "png"
    assert service._mime_to_extension("image/gif") == "gif"
    assert service._mime_to_extension("image/webp") == "webp"
    assert service._mime_to_extension("image/svg+xml") == "svg"
    assert service._mime_to_extension("unknown/type") is None
