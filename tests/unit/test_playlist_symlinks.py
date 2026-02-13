"""Unit tests for playlist symlink rebuild logic."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from annextube.models.playlist import Playlist
from annextube.services.archiver import Archiver


def _make_video_dir(videos_dir: Path, year: str, month: str, title: str,
                    video_id: str, published_at: str) -> Path:
    """Create a video directory with metadata.json for testing."""
    video_dir = videos_dir / year / month / title
    video_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "video_id": video_id,
        "title": title,
        "published_at": published_at,
        "channel_id": "UC_test",
        "channel_name": "Test Channel",
        "duration": 100,
        "view_count": 0,
        "like_count": 0,
        "comment_count": 0,
        "thumbnail_url": "",
        "download_status": "metadata_only",
        "source_url": f"https://www.youtube.com/watch?v={video_id}",
    }
    with open(video_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)
    return video_dir


def _make_archiver_stub(repo_path: Path) -> Archiver:
    """Create an Archiver with minimal mocked dependencies for unit testing."""
    config = MagicMock()
    config.organization.playlist_video_pattern = "{video_index:04d}_{video_path_basename}"
    config.user.ytdlp_extra_opts = []
    config.user.cookies_file = None
    config.user.cookies_from_browser = None
    config.user.proxy = None
    config.user.limit_rate = None
    config.user.sleep_interval = None
    config.user.max_sleep_interval = None
    config.user.api_key = None

    # Create Archiver using __new__ to skip __init__ (avoid YouTube/git-annex setup)
    archiver = object.__new__(Archiver)
    archiver.repo_path = repo_path
    archiver.config = config
    return archiver


@pytest.mark.ai_generated
def test_build_video_id_map() -> None:
    """Test _build_video_id_map scans videos/ and returns correct mapping."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        videos_dir = repo_path / "videos"

        v1 = _make_video_dir(videos_dir, "2025", "06", "vid-A", "AAA", "2025-06-01T00:00:00")
        v2 = _make_video_dir(videos_dir, "2025", "07", "vid-B", "BBB", "2025-07-15T00:00:00")

        archiver = _make_archiver_stub(repo_path)
        video_map = archiver._build_video_id_map()

        assert len(video_map) == 2
        assert video_map["AAA"] == v1
        assert video_map["BBB"] == v2


@pytest.mark.ai_generated
def test_rebuild_playlist_symlinks_chronological_order() -> None:
    """Test that symlinks are created in chronological order (oldest first)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        videos_dir = repo_path / "videos"

        # Create videos in non-chronological order
        _make_video_dir(videos_dir, "2026", "01", "newer-video", "VID2", "2026-01-15T00:00:00")
        _make_video_dir(videos_dir, "2025", "06", "oldest-video", "VID1", "2025-06-01T00:00:00")
        _make_video_dir(videos_dir, "2025", "12", "middle-video", "VID3", "2025-12-25T00:00:00")

        playlist_dir = repo_path / "playlists" / "test-playlist"
        playlist_dir.mkdir(parents=True)

        playlist = Playlist(
            playlist_id="PL_test",
            title="Test Playlist",
            description="",
            channel_id="UC_test",
            channel_name="Test Channel",
            video_count=3,
            privacy_status="public",
            last_modified=None,
            video_ids=["VID2", "VID1", "VID3"],  # YouTube order (not chronological)
        )

        archiver = _make_archiver_stub(repo_path)
        archiver._rebuild_playlist_symlinks(playlist_dir, playlist)

        # Verify symlinks created
        symlinks = sorted([f for f in playlist_dir.iterdir() if f.is_symlink()])
        assert len(symlinks) == 3

        # Verify chronological order: VID1 (2025-06), VID3 (2025-12), VID2 (2026-01)
        assert symlinks[0].name.startswith("0001_")
        assert "oldest-video" in symlinks[0].name
        assert symlinks[1].name.startswith("0002_")
        assert "middle-video" in symlinks[1].name
        assert symlinks[2].name.startswith("0003_")
        assert "newer-video" in symlinks[2].name


@pytest.mark.ai_generated
def test_rebuild_playlist_symlinks_cleans_old_symlinks() -> None:
    """Test that rebuild removes old symlinks before creating new ones."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        videos_dir = repo_path / "videos"

        _make_video_dir(videos_dir, "2025", "06", "vid-A", "AAA", "2025-06-01T00:00:00")
        _make_video_dir(videos_dir, "2025", "07", "vid-B", "BBB", "2025-07-15T00:00:00")

        playlist_dir = repo_path / "playlists" / "test-playlist"
        playlist_dir.mkdir(parents=True)

        # Create stale symlinks (simulating a previous run with wrong indices)
        stale1 = playlist_dir / "0003_vid-A"
        stale2 = playlist_dir / "0005_vid-B"
        stale1.symlink_to(Path("..") / ".." / "videos" / "2025" / "06" / "vid-A")
        stale2.symlink_to(Path("..") / ".." / "videos" / "2025" / "07" / "vid-B")

        # Also create a non-symlink file (should NOT be removed)
        (playlist_dir / "playlist.json").write_text("{}")

        playlist = Playlist(
            playlist_id="PL_test",
            title="Test Playlist",
            description="",
            channel_id="UC_test",
            channel_name="Test Channel",
            video_count=2,
            privacy_status="public",
            last_modified=None,
            video_ids=["AAA", "BBB"],
        )

        archiver = _make_archiver_stub(repo_path)
        archiver._rebuild_playlist_symlinks(playlist_dir, playlist)

        # Verify old stale symlinks are gone
        assert not stale1.exists() and not stale1.is_symlink()
        assert not stale2.exists() and not stale2.is_symlink()

        # Verify new correct symlinks exist
        symlinks = sorted([f for f in playlist_dir.iterdir() if f.is_symlink()])
        assert len(symlinks) == 2
        assert symlinks[0].name.startswith("0001_")
        assert symlinks[1].name.startswith("0002_")

        # Verify non-symlink files are preserved
        assert (playlist_dir / "playlist.json").exists()


@pytest.mark.ai_generated
def test_rebuild_playlist_symlinks_skips_missing_videos() -> None:
    """Test that rebuild skips video IDs not present in archive."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        videos_dir = repo_path / "videos"

        _make_video_dir(videos_dir, "2025", "06", "vid-A", "AAA", "2025-06-01T00:00:00")
        # VID "BBB" is in playlist but NOT in the archive

        playlist_dir = repo_path / "playlists" / "test-playlist"
        playlist_dir.mkdir(parents=True)

        playlist = Playlist(
            playlist_id="PL_test",
            title="Test Playlist",
            description="",
            channel_id="UC_test",
            channel_name="Test Channel",
            video_count=2,
            privacy_status="public",
            last_modified=None,
            video_ids=["AAA", "BBB"],
        )

        archiver = _make_archiver_stub(repo_path)
        archiver._rebuild_playlist_symlinks(playlist_dir, playlist)

        # Only 1 symlink should be created (BBB is missing)
        symlinks = sorted([f for f in playlist_dir.iterdir() if f.is_symlink()])
        assert len(symlinks) == 1
        assert symlinks[0].name.startswith("0001_")
        assert "vid-A" in symlinks[0].name


@pytest.mark.ai_generated
def test_rebuild_playlist_symlinks_tiebreaker_on_same_date() -> None:
    """Test that videos with same published_at are ordered by video_id as tiebreaker."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        videos_dir = repo_path / "videos"

        # Two videos on the same day
        _make_video_dir(videos_dir, "2025", "06", "vid-Z", "ZZZ", "2025-06-01T00:00:00")
        _make_video_dir(videos_dir, "2025", "06", "vid-A", "AAA", "2025-06-01T00:00:00")

        playlist_dir = repo_path / "playlists" / "test-playlist"
        playlist_dir.mkdir(parents=True)

        playlist = Playlist(
            playlist_id="PL_test",
            title="Test Playlist",
            description="",
            channel_id="UC_test",
            channel_name="Test Channel",
            video_count=2,
            privacy_status="public",
            last_modified=None,
            video_ids=["ZZZ", "AAA"],
        )

        archiver = _make_archiver_stub(repo_path)
        archiver._rebuild_playlist_symlinks(playlist_dir, playlist)

        symlinks = sorted([f for f in playlist_dir.iterdir() if f.is_symlink()])
        assert len(symlinks) == 2

        # AAA < ZZZ alphabetically, so AAA should be index 1
        assert "vid-A" in symlinks[0].name
        assert "vid-Z" in symlinks[1].name
