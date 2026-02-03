"""Integration tests for new video component fetching logic."""

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from annextube.lib.config import ComponentsConfig, Config
from annextube.models.video import Video
from annextube.services.archiver import Archiver


@pytest.fixture
def git_annex_test_repo():
    """Create a temporary git-annex repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git and git-annex
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "annex", "init", "test-repo"], cwd=repo_path, check=True, capture_output=True)

        # Configure .gitattributes
        gitattributes = repo_path / ".gitattributes"
        gitattributes.write_text("*.json annex.largefiles=nothing\n*.tsv annex.largefiles=nothing\n")
        subprocess.run(["git", "add", ".gitattributes"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Add .gitattributes"], cwd=repo_path, check=True, capture_output=True)

        yield repo_path


@pytest.fixture
def test_video():
    """Create a test video object."""
    return Video(
        video_id="newvid123",
        title="New Test Video",
        description="Test description",
        channel_id="channel123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 1, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=50,
        comment_count=10,
        thumbnail_url="https://i.ytimg.com/vi/newvid123/maxresdefault.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=["test"],
        categories=["Science & Technology"],
        captions_available=["en"],
        has_auto_captions=True,
        download_status="not_downloaded",
        source_url="https://www.youtube.com/watch?v=newvid123",
        fetched_at=datetime.now(),
    )


@pytest.mark.ai_generated
def test_new_video_gets_all_configured_components_regardless_of_mode(git_annex_test_repo: Path, test_video: Video) -> None:
    """Test that NEW videos get ALL configured components even in component-specific mode."""
    # Configure with all components enabled
    config = Config(
        components=ComponentsConfig(
            thumbnails=True,
            captions=True,
            comments_depth=10000
        )
    )

    # Set update_mode to simulate --update playlists (component-specific mode)
    archiver = Archiver(git_annex_test_repo, config, update_mode="playlists")

    # Mock methods to avoid real API calls and verify they're called
    with patch.object(archiver.youtube, 'download_captions', return_value=['en']) as mock_captions, \
         patch.object(archiver.youtube, 'download_comments', return_value=True) as mock_comments, \
         patch.object(archiver, '_download_thumbnail') as mock_thumbnail, \
         patch.object(archiver.git_annex, 'addurl') as mock_addurl, \
         patch.object(archiver.git_annex, 'set_metadata') as mock_set_metadata, \
         patch.object(archiver.git_annex, 'set_metadata_if_changed') as mock_set_metadata_if_changed:

        # Process the NEW video
        archiver._process_video(test_video)

        # Verify ALL components were fetched for NEW video despite being in "playlists" mode
        mock_addurl.assert_called_once()      # Video URL should be tracked
        mock_thumbnail.assert_called_once()   # Thumbnail should be downloaded
        mock_captions.assert_called_once()    # Captions should be downloaded
        mock_comments.assert_called_once()    # Comments should be downloaded

        # Verify metadata was saved
        video_path = archiver._get_video_path(test_video)
        metadata_path = video_path / "metadata.json"
        assert metadata_path.exists(), "Metadata should be saved for new video"


@pytest.mark.ai_generated
def test_existing_video_respects_component_mode(git_annex_test_repo: Path, test_video: Video) -> None:
    """Test that EXISTING videos respect component-specific mode (e.g., --update playlists)."""
    # Configure with all components enabled
    config = Config(
        components=ComponentsConfig(
            thumbnails=True,
            captions=True,
            comments_depth=10000
        )
    )

    archiver = Archiver(git_annex_test_repo, config, update_mode="playlists")

    # Create existing video metadata
    video_path = archiver._get_video_path(test_video)
    video_path.mkdir(parents=True, exist_ok=True)
    metadata_path = video_path / "metadata.json"
    metadata_path.write_text('{"video_id": "newvid123", "title": "Existing Video"}')

    # Mock methods to verify they're NOT called for existing videos in playlist mode
    with patch.object(archiver.youtube, 'download_captions') as mock_captions, \
         patch.object(archiver.youtube, 'download_comments') as mock_comments, \
         patch.object(archiver, '_download_thumbnail') as mock_thumbnail, \
         patch.object(archiver.git_annex, 'addurl') as mock_addurl, \
         patch.object(archiver.git_annex, 'set_metadata') as mock_set_metadata, \
         patch.object(archiver.git_annex, 'set_metadata_if_changed') as mock_set_metadata_if_changed:

        # Process the EXISTING video
        archiver._process_video(test_video)

        # Verify components respect mode for EXISTING video
        # In "playlists" mode, should NOT fetch captions/comments
        # Note: Video URL is ALWAYS tracked (even in playlist mode), but not downloaded
        mock_addurl.assert_called_once()       # Video URL is always tracked
        mock_thumbnail.assert_not_called()     # Thumbnail not updated in playlists mode
        mock_captions.assert_not_called()      # Captions not updated in playlists mode
        mock_comments.assert_not_called()      # Comments not updated in playlists mode

        # Metadata should still be updated
        assert metadata_path.exists(), "Metadata should exist for existing video"
