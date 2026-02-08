"""Unit tests for unavailable video filtering in playlist updates."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from annextube.services.youtube import YouTubeService


@pytest.fixture
def mock_repo_path(tmp_path: Path) -> Path:
    """Create a mock repository with some unavailable videos."""
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()

    # Create metadata for an available video
    available_dir = videos_dir / "2024" / "01" / "2024-01-15_available-video"
    available_dir.mkdir(parents=True)
    available_metadata = {
        "video_id": "available123",
        "title": "Available Video",
        "availability": "public",
        "privacy_status": "public",
    }
    with open(available_dir / "metadata.json", "w") as f:
        json.dump(available_metadata, f)

    # Create metadata for a private video
    private_dir = videos_dir / "2024" / "01" / "2024-01-10_private-video"
    private_dir.mkdir(parents=True)
    private_metadata = {
        "video_id": "private456",
        "title": "Private Video",
        "availability": "private",
        "privacy_status": "non-public",
    }
    with open(private_dir / "metadata.json", "w") as f:
        json.dump(private_metadata, f)

    # Create metadata for a removed video
    removed_dir = videos_dir / "2024" / "01" / "2024-01-05_removed-video"
    removed_dir.mkdir(parents=True)
    removed_metadata = {
        "video_id": "removed789",
        "title": "Removed Video",
        "availability": "removed",
        "privacy_status": "removed",
    }
    with open(removed_dir / "metadata.json", "w") as f:
        json.dump(removed_metadata, f)

    return tmp_path


@pytest.mark.ai_generated
def test_load_unavailable_videos(mock_repo_path: Path) -> None:
    """Test loading unavailable video IDs from repository."""
    service = YouTubeService()
    unavailable = service._load_unavailable_videos(mock_repo_path)

    # Should find private and removed videos, but not available one
    assert "private456" in unavailable
    assert "removed789" in unavailable
    assert "available123" not in unavailable
    assert len(unavailable) == 2


@pytest.mark.ai_generated
def test_load_unavailable_videos_empty_repo(tmp_path: Path) -> None:
    """Test loading from empty repository returns empty set."""
    service = YouTubeService()
    unavailable = service._load_unavailable_videos(tmp_path)

    assert len(unavailable) == 0


@pytest.mark.ai_generated
def test_load_unavailable_videos_nonexistent_repo(tmp_path: Path) -> None:
    """Test loading from nonexistent repository returns empty set."""
    service = YouTubeService()
    nonexistent = tmp_path / "nonexistent"
    unavailable = service._load_unavailable_videos(nonexistent)

    assert len(unavailable) == 0


@pytest.mark.ai_generated
@patch("annextube.services.youtube.yt_dlp.YoutubeDL")
def test_get_playlist_videos_incremental_two_pass(
    mock_ytdl_class: MagicMock, mock_repo_path: Path
) -> None:
    """Test that incremental mode uses two-pass approach to skip unavailable videos."""
    service = YouTubeService()

    # Mock first pass (flat extraction) to return video IDs
    mock_flat_ydl = MagicMock()
    mock_flat_info = {
        "entries": [
            {"id": "available123"},  # Available - will fetch
            {"id": "private456"},    # Private - will skip
            {"id": "removed789"},    # Removed - will skip
            {"id": "new_video999"},  # New video - will fetch
        ]
    }
    mock_flat_ydl.extract_info.return_value = mock_flat_info

    # Mock second pass (full metadata) to return video data
    mock_full_ydl = MagicMock()
    mock_full_ydl.extract_info.side_effect = [
        {"id": "available123", "title": "Available Video"},
        {"id": "new_video999", "title": "New Video"},
    ]

    # Configure YoutubeDL to return different instances for flat vs full
    mock_ytdl_class.return_value.__enter__.side_effect = [
        mock_flat_ydl, mock_full_ydl
    ]

    playlist_url = "https://www.youtube.com/playlist?list=PLtest"
    videos = service.get_playlist_videos(
        playlist_url, repo_path=mock_repo_path, incremental=True
    )

    # Should only fetch full metadata for available123 and new_video999
    # Should skip private456 and removed789
    assert len(videos) == 2
    assert videos[0]["id"] == "available123"
    assert videos[1]["id"] == "new_video999"

    # Verify that full metadata was only fetched for non-unavailable videos
    assert mock_full_ydl.extract_info.call_count == 2


@pytest.mark.ai_generated
@patch("annextube.services.youtube.yt_dlp.YoutubeDL")
def test_get_playlist_videos_non_incremental_single_pass(
    mock_ytdl_class: MagicMock, mock_repo_path: Path
) -> None:
    """Test that non-incremental mode uses single-pass approach."""
    service = YouTubeService()

    # Mock regular extraction (full metadata in one pass)
    mock_ydl = MagicMock()
    mock_info = {
        "entries": [
            {"id": "video1", "title": "Video 1"},
            {"id": "video2", "title": "Video 2"},
            None,  # Unavailable video (yt-dlp returns None)
            {"id": "video3", "title": "Video 3"},
        ]
    }
    mock_ydl.extract_info.return_value = mock_info
    mock_ytdl_class.return_value.__enter__.return_value = mock_ydl

    playlist_url = "https://www.youtube.com/playlist?list=PLtest"
    videos = service.get_playlist_videos(
        playlist_url, repo_path=mock_repo_path, incremental=False
    )

    # Should filter out None entry, return 3 videos
    assert len(videos) == 3
    assert videos[0]["id"] == "video1"
    assert videos[1]["id"] == "video2"
    assert videos[2]["id"] == "video3"

    # Verify only one extraction call (single-pass)
    assert mock_ydl.extract_info.call_count == 1


@pytest.mark.ai_generated
def test_load_unavailable_videos_corrupted_metadata(tmp_path: Path) -> None:
    """Test that corrupted metadata files are skipped gracefully."""
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()

    # Create valid metadata
    valid_dir = videos_dir / "valid"
    valid_dir.mkdir()
    with open(valid_dir / "metadata.json", "w") as f:
        json.dump({"video_id": "valid123", "availability": "private"}, f)

    # Create corrupted metadata
    corrupted_dir = videos_dir / "corrupted"
    corrupted_dir.mkdir()
    with open(corrupted_dir / "metadata.json", "w") as f:
        f.write("{invalid json")

    # Create metadata without video_id
    no_id_dir = videos_dir / "no_id"
    no_id_dir.mkdir()
    with open(no_id_dir / "metadata.json", "w") as f:
        json.dump({"availability": "private"}, f)

    service = YouTubeService()
    unavailable = service._load_unavailable_videos(tmp_path)

    # Should only find the valid unavailable video
    assert len(unavailable) == 1
    assert "valid123" in unavailable
