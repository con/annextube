"""Test date filtering functionality."""
from datetime import datetime

import pytest

from annextube.lib.config import Config
from annextube.services.archiver import Archiver


@pytest.mark.ai_generated
def test_should_process_video_by_date_no_filter():
    """Test that videos are processed when no date filter is set."""
    config = Config()
    archiver = Archiver("/tmp/test", config, update_mode="videos-incremental")

    video_meta = {
        "video_id": "test123",
        "published_at": "2026-01-01T00:00:00",
    }

    assert archiver._should_process_video_by_date(video_meta) is True


@pytest.mark.ai_generated
def test_should_process_video_by_date_within_range():
    """Test that videos within date range are processed."""
    config = Config()
    date_from = datetime(2026, 1, 1)
    date_to = datetime(2026, 1, 31)
    archiver = Archiver("/tmp/test", config, update_mode="videos-incremental",
                       date_from=date_from, date_to=date_to)

    # Video within range (ISO format)
    video_meta = {
        "video_id": "test123",
        "published_at": "2026-01-15T00:00:00",
    }
    assert archiver._should_process_video_by_date(video_meta) is True

    # Video within range (yt-dlp format)
    video_meta_ytdlp = {
        "id": "test456",
        "upload_date": "20260115",
    }
    assert archiver._should_process_video_by_date(video_meta_ytdlp) is True


@pytest.mark.ai_generated
def test_should_process_video_by_date_outside_range():
    """Test that videos outside date range are filtered out."""
    config = Config()
    date_from = datetime(2026, 1, 1)
    date_to = datetime(2026, 1, 31)
    archiver = Archiver("/tmp/test", config, update_mode="videos-incremental",
                       date_from=date_from, date_to=date_to)

    # Video before range
    video_meta_before = {
        "video_id": "test_old",
        "published_at": "2025-12-31T00:00:00",
    }
    assert archiver._should_process_video_by_date(video_meta_before) is False

    # Video after range
    video_meta_after = {
        "video_id": "test_future",
        "published_at": "2026-02-01T00:00:00",
    }
    assert archiver._should_process_video_by_date(video_meta_after) is False


@pytest.mark.ai_generated
def test_should_process_video_by_date_from_only():
    """Test filtering with only date_from (no end date)."""
    config = Config()
    date_from = datetime(2026, 1, 15)
    archiver = Archiver("/tmp/test", config, update_mode="videos-incremental",
                       date_from=date_from)

    # Video after date_from
    video_meta_after = {
        "video_id": "test_new",
        "published_at": "2026-01-20T00:00:00",
    }
    assert archiver._should_process_video_by_date(video_meta_after) is True

    # Video before date_from
    video_meta_before = {
        "video_id": "test_old",
        "published_at": "2026-01-10T00:00:00",
    }
    assert archiver._should_process_video_by_date(video_meta_before) is False


@pytest.mark.ai_generated
def test_should_process_video_by_date_missing_date():
    """Test that videos without published date are skipped."""
    config = Config()
    date_from = datetime(2026, 1, 1)
    archiver = Archiver("/tmp/test", config, update_mode="videos-incremental",
                       date_from=date_from)

    # Video without date
    video_meta_no_date = {
        "video_id": "test_no_date",
        "title": "Test Video",
    }
    assert archiver._should_process_video_by_date(video_meta_no_date) is False
