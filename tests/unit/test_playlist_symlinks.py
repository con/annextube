"""Unit tests for playlist symlink rebuild logic."""

import json
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
    archiver._video_id_map_cache = None
    archiver.update_mode = "videos-incremental"
    return archiver


@pytest.mark.ai_generated
def test_build_video_id_map(tmp_path: Path) -> None:
    """Test _build_video_id_map scans videos/ and returns correct mapping."""
    repo_path = tmp_path
    videos_dir = repo_path / "videos"

    v1 = _make_video_dir(videos_dir, "2025", "06", "vid-A", "AAA", "2025-06-01T00:00:00")
    v2 = _make_video_dir(videos_dir, "2025", "07", "vid-B", "BBB", "2025-07-15T00:00:00")

    archiver = _make_archiver_stub(repo_path)
    video_map = archiver._build_video_id_map()

    assert len(video_map) == 2
    assert video_map["AAA"] == v1
    assert video_map["BBB"] == v2


@pytest.mark.ai_generated
def test_rebuild_playlist_symlinks_chronological_order(tmp_path: Path) -> None:
    """Test that symlinks are created in chronological order (oldest first)."""
    repo_path = tmp_path
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
def test_rebuild_playlist_symlinks_cleans_old_symlinks(tmp_path: Path) -> None:
    """Test that rebuild removes old symlinks before creating new ones."""
    repo_path = tmp_path
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
def test_rebuild_playlist_symlinks_skips_missing_videos(tmp_path: Path) -> None:
    """Test that rebuild skips video IDs not present in archive."""
    repo_path = tmp_path
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
def test_rebuild_playlist_symlinks_tiebreaker_on_same_date(tmp_path: Path) -> None:
    """Test that videos with same published_at are ordered by video_id as tiebreaker."""
    repo_path = tmp_path
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


# ── Tests for diff-based _update_playlist_symlinks ──────────────────


@pytest.mark.ai_generated
def test_update_playlist_symlinks_returns_false_when_unchanged(tmp_path: Path) -> None:
    """Test that _update_playlist_symlinks returns False when symlinks match desired state."""
    repo_path = tmp_path
    videos_dir = repo_path / "videos"

    _make_video_dir(videos_dir, "2025", "06", "vid-A", "AAA", "2025-06-01T00:00:00")
    _make_video_dir(videos_dir, "2025", "07", "vid-B", "BBB", "2025-07-15T00:00:00")

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
    video_id_map = archiver._build_video_id_map()

    # First call: creates symlinks, returns True
    result1 = archiver._update_playlist_symlinks(playlist_dir, playlist, video_id_map)
    assert result1 is True

    # Second call: same state, should return False
    result2 = archiver._update_playlist_symlinks(playlist_dir, playlist, video_id_map)
    assert result2 is False


@pytest.mark.ai_generated
def test_update_playlist_symlinks_returns_true_when_video_added(tmp_path: Path) -> None:
    """Test that _update_playlist_symlinks returns True when a video is added."""
    repo_path = tmp_path
    videos_dir = repo_path / "videos"

    _make_video_dir(videos_dir, "2025", "06", "vid-A", "AAA", "2025-06-01T00:00:00")
    _make_video_dir(videos_dir, "2025", "07", "vid-B", "BBB", "2025-07-15T00:00:00")

    playlist_dir = repo_path / "playlists" / "test-playlist"
    playlist_dir.mkdir(parents=True)

    playlist_v1 = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=1, privacy_status="public", last_modified=None,
        video_ids=["AAA"],
    )
    playlist_v2 = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=2, privacy_status="public", last_modified=None,
        video_ids=["AAA", "BBB"],
    )

    archiver = _make_archiver_stub(repo_path)
    video_id_map = archiver._build_video_id_map()

    # First: one video
    archiver._update_playlist_symlinks(playlist_dir, playlist_v1, video_id_map)
    symlinks = [f for f in playlist_dir.iterdir() if f.is_symlink()]
    assert len(symlinks) == 1

    # Second: add a video → should return True and create 2 symlinks
    result = archiver._update_playlist_symlinks(playlist_dir, playlist_v2, video_id_map)
    assert result is True
    symlinks = sorted([f for f in playlist_dir.iterdir() if f.is_symlink()])
    assert len(symlinks) == 2


# ── Tests for video_id_map caching ──────────────────────────────────


@pytest.mark.ai_generated
def test_build_video_id_map_caching(tmp_path: Path) -> None:
    """Test that _build_video_id_map caches results and invalidation works."""
    repo_path = tmp_path
    videos_dir = repo_path / "videos"

    _make_video_dir(videos_dir, "2025", "06", "vid-A", "AAA", "2025-06-01T00:00:00")

    archiver = _make_archiver_stub(repo_path)

    # First call: builds and caches
    map1 = archiver._build_video_id_map()
    assert len(map1) == 1
    assert archiver._video_id_map_cache is not None

    # Add another video
    _make_video_dir(videos_dir, "2025", "07", "vid-B", "BBB", "2025-07-15T00:00:00")

    # Second call: returns cached (still 1 video)
    map2 = archiver._build_video_id_map()
    assert len(map2) == 1
    assert map2 is map1  # Same object

    # Invalidate cache
    archiver._invalidate_video_id_map_cache()
    assert archiver._video_id_map_cache is None

    # Third call: rescans, finds 2 videos
    map3 = archiver._build_video_id_map()
    assert len(map3) == 2


@pytest.mark.ai_generated
def test_build_video_id_map_use_cache_false(tmp_path: Path) -> None:
    """Test that use_cache=False bypasses cache."""
    repo_path = tmp_path
    videos_dir = repo_path / "videos"

    _make_video_dir(videos_dir, "2025", "06", "vid-A", "AAA", "2025-06-01T00:00:00")

    archiver = _make_archiver_stub(repo_path)

    # Build and cache
    map1 = archiver._build_video_id_map()
    assert len(map1) == 1

    # Add another video
    _make_video_dir(videos_dir, "2025", "07", "vid-B", "BBB", "2025-07-15T00:00:00")

    # With use_cache=False: rescans
    map2 = archiver._build_video_id_map(use_cache=False)
    assert len(map2) == 2


# ── Tests for _save_playlist_metadata ───────────────────────────────


@pytest.mark.ai_generated
def test_save_playlist_metadata_creates_new(tmp_path: Path) -> None:
    """Test that _save_playlist_metadata creates playlist.json for new playlist."""
    repo_path = tmp_path
    playlist_dir = repo_path / "playlists" / "test"
    playlist_dir.mkdir(parents=True)

    playlist = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=1, privacy_status="public", last_modified=None,
        video_ids=["AAA"],
    )

    archiver = _make_archiver_stub(repo_path)
    result = archiver._save_playlist_metadata(playlist, playlist_dir)

    assert result is True
    assert (playlist_dir / "playlist.json").exists()


@pytest.mark.ai_generated
def test_save_playlist_metadata_skips_when_unchanged(tmp_path: Path) -> None:
    """Test that _save_playlist_metadata returns False when video IDs unchanged."""
    repo_path = tmp_path
    playlist_dir = repo_path / "playlists" / "test"
    playlist_dir.mkdir(parents=True)

    playlist = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=1, privacy_status="public", last_modified=None,
        video_ids=["AAA"],
    )

    archiver = _make_archiver_stub(repo_path)

    # First save
    archiver._save_playlist_metadata(playlist, playlist_dir)

    # Second save with same video_ids → should return False
    result = archiver._save_playlist_metadata(playlist, playlist_dir)
    assert result is False


@pytest.mark.ai_generated
def test_save_playlist_metadata_refuses_truncation_vs_reported_count(
    tmp_path: Path,
) -> None:
    """Guard: refuse to overwrite when fewer video_ids than YouTube reports.

    Reproduces the yt-dlp continuation-token truncation bug: yt-dlp returns
    playlist_count=144 (correct) but only 100 entries. Prior behavior would
    persist the truncated list, dropping 44 IDs from the archive.
    """
    repo_path = tmp_path
    playlist_dir = repo_path / "playlists" / "test"
    playlist_dir.mkdir(parents=True)

    archiver = _make_archiver_stub(repo_path)

    # Seed with a full playlist (144 IDs).
    full = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=144, privacy_status="public", last_modified=None,
        video_ids=[f"vid{i:03d}" for i in range(144)],
    )
    assert archiver._save_playlist_metadata(full, playlist_dir) is True

    # yt-dlp truncates to 100 IDs but still reports 144.
    truncated = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=144, privacy_status="public", last_modified=None,
        video_ids=[f"vid{i:03d}" for i in range(100)],
    )
    result = archiver._save_playlist_metadata(truncated, playlist_dir)
    assert result is False

    # playlist.json on disk MUST still have all 144 IDs.
    with open(playlist_dir / "playlist.json") as f:
        on_disk = json.load(f)
    assert len(on_disk["video_ids"]) == 144
    assert on_disk["video_ids"][-1] == "vid143"


@pytest.mark.ai_generated
def test_save_playlist_metadata_allows_legit_owner_removal(tmp_path: Path) -> None:
    """A legit owner-side removal MUST persist when reported_count matches.

    When yt-dlp is internally consistent (len(video_ids) == playlist_count),
    the truncation guard does not fire. This covers pure removals AND
    add-and-remove curation.
    """
    repo_path = tmp_path
    playlist_dir = repo_path / "playlists" / "test"
    playlist_dir.mkdir(parents=True)

    archiver = _make_archiver_stub(repo_path)

    seed = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=3, privacy_status="public", last_modified=None,
        video_ids=["A", "B", "C"],
    )
    assert archiver._save_playlist_metadata(seed, playlist_dir) is True

    # Owner removed C (pure shrink, no additions).
    pure_removal = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=2, privacy_status="public", last_modified=None,
        video_ids=["A", "B"],
    )
    assert archiver._save_playlist_metadata(pure_removal, playlist_dir) is True

    with open(playlist_dir / "playlist.json") as f:
        on_disk = json.load(f)
    assert on_disk["video_ids"] == ["A", "B"]

    # Owner removed A but added D and E (add + remove curation).
    curated = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=3, privacy_status="public", last_modified=None,
        video_ids=["B", "D", "E"],
    )
    assert archiver._save_playlist_metadata(curated, playlist_dir) is True

    with open(playlist_dir / "playlist.json") as f:
        on_disk = json.load(f)
    assert on_disk["video_ids"] == ["B", "D", "E"]


@pytest.mark.ai_generated
def test_save_playlist_metadata_refuses_truncation_on_first_save(
    tmp_path: Path,
) -> None:
    """Guard fires on first-time saves too, not just overwrites.

    Otherwise a new archive's very first fetch of a large playlist would
    silently persist the truncated list before any protection kicks in.
    """
    repo_path = tmp_path
    playlist_dir = repo_path / "playlists" / "test"
    playlist_dir.mkdir(parents=True)

    archiver = _make_archiver_stub(repo_path)
    truncated = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=144, privacy_status="public", last_modified=None,
        video_ids=[f"vid{i:03d}" for i in range(100)],
    )
    result = archiver._save_playlist_metadata(truncated, playlist_dir)

    assert result is False
    assert not (playlist_dir / "playlist.json").exists(), (
        "No file should have been created — first-time truncated save must be refused"
    )


@pytest.mark.ai_generated
def test_save_playlist_metadata_refuses_when_existing_file_unreadable(
    tmp_path: Path,
) -> None:
    """Corrupt playlist.json must NOT be silently rewritten.

    Rewriting would mask corruption / permissions problems and leave the
    archive in a state where the operator has no signal that something went
    wrong. Refuse the save and log an error instead.
    """
    repo_path = tmp_path
    playlist_dir = repo_path / "playlists" / "test"
    playlist_dir.mkdir(parents=True)

    (playlist_dir / "playlist.json").write_text("{ this is not valid json")

    archiver = _make_archiver_stub(repo_path)
    playlist = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=1, privacy_status="public", last_modified=None,
        video_ids=["A"],
    )
    assert archiver._save_playlist_metadata(playlist, playlist_dir) is False
    # File must remain untouched — operator has to fix it manually.
    assert (playlist_dir / "playlist.json").read_text() == "{ this is not valid json"


@pytest.mark.ai_generated
def test_save_playlist_metadata_allows_race_gained_video(tmp_path: Path) -> None:
    """A video added mid-fetch (entries > reported_count) MUST persist.

    yt-dlp probes playlist_count and entries in separate operations. If a
    video is added between them, entries can legitimately exceed
    playlist_count — the guard must not misfire on this race.
    """
    repo_path = tmp_path
    playlist_dir = repo_path / "playlists" / "test"
    playlist_dir.mkdir(parents=True)

    archiver = _make_archiver_stub(repo_path)
    raced = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=3, privacy_status="public", last_modified=None,
        video_ids=["A", "B", "C", "D"],  # one more than reported
    )
    assert archiver._save_playlist_metadata(raced, playlist_dir) is True
    with open(playlist_dir / "playlist.json") as f:
        assert json.load(f)["video_ids"] == ["A", "B", "C", "D"]


@pytest.mark.ai_generated
def test_save_playlist_metadata_allows_legitimately_emptied_playlist(
    tmp_path: Path,
) -> None:
    """An owner emptying the playlist (count 0, entries []) MUST persist."""
    repo_path = tmp_path
    playlist_dir = repo_path / "playlists" / "test"
    playlist_dir.mkdir(parents=True)
    archiver = _make_archiver_stub(repo_path)

    seed = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=2, privacy_status="public", last_modified=None,
        video_ids=["A", "B"],
    )
    assert archiver._save_playlist_metadata(seed, playlist_dir) is True

    emptied = Playlist(
        playlist_id="PL_test", title="Test", description="",
        channel_id="UC_test", channel_name="Test Channel",
        video_count=0, privacy_status="public", last_modified=None,
        video_ids=[],
    )
    assert archiver._save_playlist_metadata(emptied, playlist_dir) is True
    with open(playlist_dir / "playlist.json") as f:
        assert json.load(f)["video_ids"] == []
