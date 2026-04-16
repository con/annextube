"""Unit tests for batch API request optimization (T039).

Tests verify that backup_playlist uses batch API calls
(batch_enhance_video_metadata, batch_get_video_statistics) instead of
per-video API calls, minimizing YouTube Data API quota usage.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from annextube.services.archiver import Archiver


def _make_video_meta(video_id: str, is_new: bool = True) -> dict:
    """Build a minimal video metadata dict."""
    if is_new:
        return {
            "id": video_id,
            "title": f"Video {video_id}",
            "channel_id": "UCtest",
            "channel": "Test Channel",
            "upload_date": "20260101",
            "duration": 60,
            "view_count": 100,
            "like_count": 10,
            "comment_count": 5,
            "thumbnail": "",
            "tags": [],
            "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
        }
    return {
        "video_id": video_id,
        "title": f"Video {video_id}",
        "channel_id": "UCtest",
        "channel_name": "Test Channel",
        "published_at": "2026-01-01T00:00:00",
        "duration": 60,
        "view_count": 100,
        "like_count": 10,
        "comment_count": 5,
        "thumbnail_url": "",
        "tags": [],
        "source_url": f"https://www.youtube.com/watch?v={video_id}",
    }


def _make_archiver(tmp_path: Path, update_mode: str = "all-force", is_initial: bool = True) -> Archiver:
    """Create a minimally-initialized Archiver with mocked internals."""
    (tmp_path / "videos").mkdir(exist_ok=True)
    (tmp_path / ".annextube").mkdir(exist_ok=True)
    (tmp_path / "playlists" / "test").mkdir(parents=True, exist_ok=True)

    config = MagicMock()
    config.filters.limit = None
    config.filters.date_start = None
    config.filters.date_end = None
    config.components.comments_depth = 0
    config.search.enabled = False
    config.backup.checkpoint_enabled = False
    config.backup.auto_commit_on_interrupt = False
    config.sources = []

    archiver = Archiver.__new__(Archiver)
    archiver.repo_path = tmp_path
    archiver.config = config
    archiver.update_mode = update_mode
    archiver.date_from = None
    archiver.date_to = None
    archiver._processed_video_ids = set()
    archiver._current_run_errors = []
    archiver._current_run_warnings = []
    archiver._current_source_config = None
    archiver._is_initial_backup = is_initial

    archiver.youtube = MagicMock()
    archiver.git_annex = MagicMock()
    archiver.export = MagicMock()

    return archiver


@pytest.mark.ai_generated
def test_playlist_backup_batches_api_metadata(tmp_path: Path) -> None:
    """backup_playlist should batch-fetch API metadata for new videos."""
    archiver = _make_archiver(tmp_path, update_mode="all-force")
    api_client = MagicMock()
    archiver.youtube.api_client = api_client

    new_videos = [_make_video_meta(f"vid{i}") for i in range(5)]

    playlist_mock = MagicMock()
    playlist_mock.video_ids = [f"vid{i}" for i in range(5)]
    archiver.youtube.get_playlist_metadata.return_value = playlist_mock
    archiver.youtube.get_playlist_videos.return_value = new_videos

    # metadata_to_video returns a mock Video with video_id attr
    def make_mock_video(meta, **kwargs):
        v = MagicMock()
        v.video_id = meta.get("id", meta.get("video_id"))
        v.title = meta.get("title", "")
        v.published_at = datetime(2026, 1, 1)
        return v

    archiver.youtube.metadata_to_video.side_effect = make_mock_video

    api_client.batch_enhance_video_metadata.return_value = {
        f"vid{i}": {"license": "youtube"} for i in range(5)
    }

    with (
        patch.object(Archiver, "_process_video", return_value=0),
        patch.object(Archiver, "_save_playlist_metadata", return_value=True),
        patch.object(Archiver, "_get_playlist_path", return_value=tmp_path / "playlists" / "test"),
        patch.object(Archiver, "_invalidate_video_id_map_cache"),
        patch.object(Archiver, "_build_video_id_map", return_value={}),
        patch.object(Archiver, "_update_playlist_symlinks"),
        patch.object(Archiver, "_generate_and_commit_tsvs"),
        patch.object(Archiver, "_has_uncommitted_changes", return_value=False),
        patch.object(Archiver, "_save_unavailable_stubs"),
    ):
        archiver.backup_playlist("https://www.youtube.com/playlist?list=PLtest")

    # Verify batch API was called with all new video IDs
    api_client.batch_enhance_video_metadata.assert_called_once_with(
        [f"vid{i}" for i in range(5)]
    )

    # Verify api_metadata_cache was passed to metadata_to_video
    for c in archiver.youtube.metadata_to_video.call_args_list:
        assert "api_metadata_cache" in c.kwargs
        assert c.kwargs["api_metadata_cache"] is not None


@pytest.mark.ai_generated
def test_playlist_backup_batches_statistics_in_incremental_mode(tmp_path: Path) -> None:
    """backup_playlist should batch-fetch statistics for existing videos in all-incremental."""
    archiver = _make_archiver(tmp_path, update_mode="all-incremental", is_initial=False)
    api_client = MagicMock()
    archiver.youtube.api_client = api_client

    existing_videos = [_make_video_meta("vid0", is_new=False)]

    playlist_mock = MagicMock()
    playlist_mock.video_ids = ["vid0"]
    archiver.youtube.get_playlist_metadata.return_value = playlist_mock
    archiver.youtube.get_playlist_videos.return_value = existing_videos

    def make_mock_video(meta, **kwargs):
        v = MagicMock()
        v.video_id = meta.get("id", meta.get("video_id"))
        v.title = meta.get("title", "")
        v.published_at = datetime(2026, 1, 1)
        return v

    archiver.youtube.metadata_to_video.side_effect = make_mock_video

    api_client.batch_get_video_statistics.return_value = {
        "vid0": {"viewCount": 200, "likeCount": 20, "commentCount": 10}
    }

    with (
        patch.object(Archiver, "_process_video", return_value=0) as mock_process,
        patch.object(Archiver, "_save_playlist_metadata", return_value=True),
        patch.object(Archiver, "_get_playlist_path", return_value=tmp_path / "playlists" / "test"),
        patch.object(Archiver, "_invalidate_video_id_map_cache"),
        patch.object(Archiver, "_build_video_id_map", return_value={}),
        patch.object(Archiver, "_update_playlist_symlinks"),
        patch.object(Archiver, "_generate_and_commit_tsvs"),
        patch.object(Archiver, "_has_uncommitted_changes", return_value=False),
        patch.object(Archiver, "_save_unavailable_stubs"),
    ):
        archiver.backup_playlist("https://www.youtube.com/playlist?list=PLtest")

        # Verify batch statistics was called for existing videos
        api_client.batch_get_video_statistics.assert_called_once_with(["vid0"])

        # Verify prefetched_stats was passed to _process_video
        for c in mock_process.call_args_list:
            assert "prefetched_stats" in c.kwargs


@pytest.mark.ai_generated
def test_playlist_backup_skips_batch_without_api_client(tmp_path: Path) -> None:
    """backup_playlist should not attempt batch calls when no API client configured."""
    archiver = _make_archiver(tmp_path, update_mode="all-force")
    archiver.youtube.api_client = None  # No API key configured

    new_videos = [_make_video_meta("vid0")]

    playlist_mock = MagicMock()
    playlist_mock.video_ids = ["vid0"]
    archiver.youtube.get_playlist_metadata.return_value = playlist_mock
    archiver.youtube.get_playlist_videos.return_value = new_videos

    def make_mock_video(meta, **kwargs):
        v = MagicMock()
        v.video_id = meta.get("id", meta.get("video_id"))
        v.title = meta.get("title", "")
        v.published_at = datetime(2026, 1, 1)
        return v

    archiver.youtube.metadata_to_video.side_effect = make_mock_video

    with (
        patch.object(Archiver, "_process_video", return_value=0),
        patch.object(Archiver, "_save_playlist_metadata", return_value=True),
        patch.object(Archiver, "_get_playlist_path", return_value=tmp_path / "playlists" / "test"),
        patch.object(Archiver, "_invalidate_video_id_map_cache"),
        patch.object(Archiver, "_build_video_id_map", return_value={}),
        patch.object(Archiver, "_update_playlist_symlinks"),
        patch.object(Archiver, "_generate_and_commit_tsvs"),
        patch.object(Archiver, "_has_uncommitted_changes", return_value=False),
        patch.object(Archiver, "_save_unavailable_stubs"),
    ):
        archiver.backup_playlist("https://www.youtube.com/playlist?list=PLtest")

    # api_metadata_cache should be None when no API client
    for c in archiver.youtube.metadata_to_video.call_args_list:
        assert c.kwargs.get("api_metadata_cache") is None
