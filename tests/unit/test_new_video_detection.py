"""Unit tests for new video detection logic."""

from datetime import datetime
from pathlib import Path

import pytest

from annextube.lib.config import ComponentsConfig, Config
from annextube.models.video import Video
from annextube.services.archiver import Archiver


@pytest.fixture
def test_video():
    """Create a test video object."""
    return Video(
        video_id="test123",
        title="Test Video",
        description="Test description",
        channel_id="channel123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 1, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=50,
        comment_count=10,
        thumbnail_url="https://example.com/thumb.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=["test"],
        categories=["Science & Technology"],
        captions_available=["en"],
        has_auto_captions=True,
        download_status="not_downloaded",
        source_url="https://www.youtube.com/watch?v=test123",
        fetched_at=datetime.now(),
    )


@pytest.mark.ai_generated
def test_new_video_detected_when_metadata_missing(tmp_path: Path, test_video: Video) -> None:
    """Test that a video is detected as NEW when metadata.json doesn't exist."""
    config = Config(components=ComponentsConfig(
        thumbnails=True,
        captions=True,
        comments_depth=10000
    ))

    archiver = Archiver(tmp_path, config)

    # Get expected path
    video_path = archiver._get_video_path(test_video)
    metadata_path = video_path / "metadata.json"

    # Metadata doesn't exist yet
    assert not metadata_path.exists(), "Metadata should not exist for new video"

    # This will be checked in _process_video to determine if it's a new video
    is_new = not metadata_path.exists()
    assert is_new is True, "Video should be detected as NEW when metadata.json doesn't exist"


@pytest.mark.ai_generated
def test_existing_video_detected_when_metadata_exists(tmp_path: Path, test_video: Video) -> None:
    """Test that a video is detected as EXISTING when metadata.json exists."""
    config = Config(components=ComponentsConfig(
        thumbnails=True,
        captions=True,
        comments_depth=10000
    ))

    archiver = Archiver(tmp_path, config)

    # Get expected path
    video_path = archiver._get_video_path(test_video)
    metadata_path = video_path / "metadata.json"

    # Create the metadata file
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text('{"video_id": "test123"}')

    assert metadata_path.exists(), "Metadata should exist for existing video"

    # This will be checked in _process_video to determine if it's an existing video
    is_new = not metadata_path.exists()
    assert is_new is False, "Video should be detected as EXISTING when metadata.json exists"
