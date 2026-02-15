"""Unit tests for unavailable video filtering in playlist updates."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from annextube.lib.config import Config
from annextube.models.playlist import Playlist
from annextube.services.archiver import Archiver
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

    # Second pass now creates a separate YoutubeDL per video via
    # _fetch_single_video_info.  Return a fresh mock for each call.
    def make_per_video_ydl():
        m = MagicMock()
        def _extract(url, download=False):
            if "available123" in url:
                return {"id": "available123", "title": "Available Video"}
            if "new_video999" in url:
                return {"id": "new_video999", "title": "New Video"}
            return None
        m.extract_info.side_effect = _extract
        return m

    # First call is flat pass, subsequent calls are per-video
    call_count = [0]
    def enter_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_flat_ydl
        return make_per_video_ydl()

    mock_ytdl_class.return_value.__enter__ = lambda self: enter_side_effect()
    mock_ytdl_class.return_value.__exit__ = MagicMock(return_value=False)

    playlist_url = "https://www.youtube.com/playlist?list=PLtest"
    videos = service.get_playlist_videos(
        playlist_url, repo_path=mock_repo_path, incremental=True
    )

    # Should only fetch full metadata for available123 and new_video999
    # Should skip private456 and removed789
    assert len(videos) == 2
    assert videos[0]["id"] == "available123"
    assert videos[1]["id"] == "new_video999"


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


@pytest.fixture
def playlist_with_unavailable() -> Playlist:
    """Create a playlist that includes both available and unavailable video IDs."""
    return Playlist(
        playlist_id="PLtest123",
        title="Test Playlist",
        description="",
        channel_id="UCtest",
        channel_name="Test Channel",
        video_count=4,
        privacy_status="public",
        last_modified=None,
        video_ids=["avail1", "avail2", "gone1", "gone2"],
    )


@pytest.mark.ai_generated
def test_save_unavailable_stubs_creates_json(
    tmp_path: Path, playlist_with_unavailable: Playlist
) -> None:
    """Unavailable video IDs are recorded in .annextube/unavailable_videos.json."""
    config = Config()
    archiver = Archiver(tmp_path, config)

    # Only avail1 and avail2 were successfully fetched
    fetched_ids = {"avail1", "avail2"}
    new_count = archiver._save_unavailable_stubs(playlist_with_unavailable, fetched_ids)

    assert new_count == 2

    # Verify the centralized JSON file
    unavail_path = tmp_path / ".annextube" / "unavailable_videos.json"
    assert unavail_path.exists()

    with open(unavail_path) as f:
        data = json.load(f)

    assert set(data.keys()) == {"gone1", "gone2"}
    for _vid, entry in data.items():
        assert "detected_at" in entry
        assert entry["reason"] == "unavailable"
        assert entry["playlist_id"] == "PLtest123"

    # No stub metadata.json should exist in videos/
    videos_dir = tmp_path / "videos"
    assert not list(videos_dir.rglob("metadata.json")) if videos_dir.exists() else True


@pytest.mark.ai_generated
def test_load_unavailable_finds_json_entries(
    tmp_path: Path, playlist_with_unavailable: Playlist
) -> None:
    """_load_unavailable_videos() finds entries from unavailable_videos.json."""
    config = Config()
    archiver = Archiver(tmp_path, config)

    # Record unavailable videos
    archiver._save_unavailable_stubs(playlist_with_unavailable, {"avail1", "avail2"})

    # Now _load_unavailable_videos should find them
    service = YouTubeService()
    unavailable = service._load_unavailable_videos(tmp_path)

    assert "gone1" in unavailable
    assert "gone2" in unavailable
    assert "avail1" not in unavailable
    assert "avail2" not in unavailable


@pytest.mark.ai_generated
def test_save_unavailable_stubs_is_idempotent(
    tmp_path: Path, playlist_with_unavailable: Playlist
) -> None:
    """Running _save_unavailable_stubs twice does not duplicate entries."""
    config = Config()
    archiver = Archiver(tmp_path, config)

    # Record once
    count1 = archiver._save_unavailable_stubs(playlist_with_unavailable, {"avail1", "avail2"})
    assert count1 == 2

    # Record again — should add zero new entries
    count2 = archiver._save_unavailable_stubs(playlist_with_unavailable, {"avail1", "avail2"})
    assert count2 == 0

    # File should still have exactly 2 entries
    unavail_path = tmp_path / ".annextube" / "unavailable_videos.json"
    with open(unavail_path) as f:
        data = json.load(f)
    assert len(data) == 2


@pytest.mark.ai_generated
def test_two_pass_tracks_failed_extractions() -> None:
    """Two-pass path adds failed video IDs to _last_unavailable_ids."""
    service = YouTubeService()

    # Verify initial state is empty
    assert service._last_unavailable_ids == set()

    # Mock yt-dlp to simulate two-pass extraction with failures.
    # Second pass now creates a separate YoutubeDL per video via _fetch_single_video_info.
    with patch("annextube.services.youtube.yt_dlp.YoutubeDL") as mock_ytdl_class:
        # First pass: flat extraction returns 3 IDs
        mock_flat_ydl = MagicMock()
        mock_flat_ydl.extract_info.return_value = {
            "entries": [
                {"id": "ok1"},
                {"id": "fail1"},
                {"id": "ok2"},
            ]
        }

        # Per-video mock: fail1 raises an error
        def make_per_video_ydl():
            m = MagicMock()
            def _extract(url, download=False):
                if "fail1" in url:
                    raise Exception("Video unavailable")
                vid = url.split("=")[-1]
                return {"id": vid, "title": "OK"}
            m.extract_info.side_effect = _extract
            return m

        call_count = [0]
        def enter_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_flat_ydl
            return make_per_video_ydl()

        mock_ytdl_class.return_value.__enter__ = lambda self: enter_side_effect()
        mock_ytdl_class.return_value.__exit__ = MagicMock(return_value=False)

        # Create a repo with a known unavailable video so two-pass is triggered
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            videos_dir = repo_path / "videos" / "dummy"
            videos_dir.mkdir(parents=True)
            with open(videos_dir / "metadata.json", "w") as f:
                json.dump({"video_id": "old_unavail", "availability": "unavailable"}, f)

            videos = service.get_playlist_videos(
                "https://www.youtube.com/playlist?list=PLtest",
                repo_path=repo_path,
                incremental=True,
            )

        assert len(videos) == 2
        assert "fail1" in service._last_unavailable_ids
