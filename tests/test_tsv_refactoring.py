"""Test TSV refactoring and new features.

Tests:
- Configuration defaults (caption_languages, video_path_pattern, separator)
- TSV column order and naming
- Caption count (not boolean)
- Video renaming logic
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from annextube.lib.config import ComponentsConfig, OrganizationConfig
from annextube.models.video import Video
from annextube.services.export import ExportService


@pytest.mark.ai_generated
def test_config_defaults():
    """Test new configuration defaults."""
    # Test ComponentsConfig
    components = ComponentsConfig()
    assert components.caption_languages == ".*", "Default caption_languages should be '.*'"
    assert components.comments_depth == 10000, "Comments should be enabled with default depth 10000"

    # Test OrganizationConfig
    org = OrganizationConfig()
    assert org.video_path_pattern == "{date}_{sanitized_title}", \
        "Default video_path_pattern should not include video_id"
    assert org.playlist_prefix_separator == "_", \
        "Default playlist_prefix_separator should be underscore"
    assert org.playlist_prefix_width == 4, \
        "Default playlist_prefix_width should be 4"


@pytest.mark.ai_generated
def test_videos_tsv_structure():
    """Test videos.tsv has correct structure (location, columns, order)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        export_service = ExportService(repo_path)

        # Create mock video data
        videos_dir = repo_path / "videos"
        videos_dir.mkdir()

        # Create a mock video directory with metadata
        video_dir = videos_dir / "2020-01-10_test-video"
        video_dir.mkdir()

        metadata = {
            "video_id": "test123",
            "title": "Test Video",
            "channel_name": "Test Channel",
            "published_at": "2020-01-10T00:00:00Z",
            "duration": 300,
            "view_count": 1000,
            "like_count": 50,
            "comment_count": 10,
            "captions_available": ["en", "es", "fr"],  # 3 captions
        }

        with open(video_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)

        # Generate TSV
        tsv_path = export_service.generate_videos_tsv()

        # Verify location
        assert tsv_path == repo_path / "videos" / "videos.tsv", \
            "TSV should be in videos/videos.tsv"
        assert tsv_path.exists(), "TSV file should be created"

        # Verify structure
        with open(tsv_path, "r") as f:
            lines = f.readlines()

        # Check header
        header = lines[0].strip()
        expected_columns = [
            "title", "channel", "published", "duration", "views",
            "likes", "comments", "captions", "path", "video_id"
        ]
        actual_columns = header.split("\t")
        assert actual_columns == expected_columns, \
            f"Column order incorrect. Expected {expected_columns}, got {actual_columns}"

        # Check first column is title
        assert actual_columns[0] == "title", "First column should be 'title'"

        # Check last column is video_id
        assert actual_columns[-1] == "video_id", "Last column should be 'video_id'"

        # Check 'path' not 'file_path'
        assert "path" in actual_columns, "Should have 'path' column"
        assert "file_path" not in actual_columns, "Should not have 'file_path' column"

        # Check 'captions' not 'has_captions'
        assert "captions" in actual_columns, "Should have 'captions' column"
        assert "has_captions" not in actual_columns, \
            "Should not have 'has_captions' column"

        # Check data row
        data_row = lines[1].strip().split("\t")
        assert data_row[0] == "Test Video", "Title should be first field"
        assert data_row[-1] == "test123", "video_id should be last field"
        assert data_row[7] == "3", "captions should be count (3), not boolean"
        assert data_row[8] == "2020-01-10_test-video", \
            "path should be relative directory name"


@pytest.mark.ai_generated
def test_playlists_tsv_structure():
    """Test playlists.tsv has correct structure (location, columns, order)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        export_service = ExportService(repo_path)

        # Create mock playlist data
        playlists_dir = repo_path / "playlists"
        playlists_dir.mkdir()

        # Create a mock playlist directory with metadata
        playlist_dir = playlists_dir / "test-playlist"
        playlist_dir.mkdir()

        metadata = {
            "playlist_id": "PLtest123",
            "title": "Test Playlist",
            "channel_name": "Test Channel",
            "last_modified": "2020-01-10T00:00:00Z",
        }

        with open(playlist_dir / "playlist.json", "w") as f:
            json.dump(metadata, f)

        # Generate TSV
        tsv_path = export_service.generate_playlists_tsv()

        # Verify location
        assert tsv_path == repo_path / "playlists" / "playlists.tsv", \
            "TSV should be in playlists/playlists.tsv"
        assert tsv_path.exists(), "TSV file should be created"

        # Verify structure
        with open(tsv_path, "r") as f:
            lines = f.readlines()

        # Check header
        header = lines[0].strip()
        expected_columns = [
            "title", "channel", "video_count", "total_duration",
            "last_updated", "path", "playlist_id"
        ]
        actual_columns = header.split("\t")
        assert actual_columns == expected_columns, \
            f"Column order incorrect. Expected {expected_columns}, got {actual_columns}"

        # Check first column is title
        assert actual_columns[0] == "title", "First column should be 'title'"

        # Check last column is playlist_id
        assert actual_columns[-1] == "playlist_id", \
            "Last column should be 'playlist_id'"

        # Check 'path' not 'folder_name'
        assert "path" in actual_columns, "Should have 'path' column"
        assert "folder_name" not in actual_columns, \
            "Should not have 'folder_name' column"

        # Check data row
        data_row = lines[1].strip().split("\t")
        assert data_row[0] == "Test Playlist", "Title should be first field"
        assert data_row[-1] == "PLtest123", "playlist_id should be last field"
        assert data_row[5] == "test-playlist", \
            "path should be relative directory name"


@pytest.mark.ai_generated
def test_caption_count_not_boolean():
    """Test that captions column is count, not boolean."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        export_service = ExportService(repo_path)

        videos_dir = repo_path / "videos"
        videos_dir.mkdir()

        # Test case 1: No captions
        video_dir_0 = videos_dir / "video-no-captions"
        video_dir_0.mkdir()
        with open(video_dir_0 / "metadata.json", "w") as f:
            json.dump({
                "video_id": "vid0",
                "title": "No Captions",
                "captions_available": [],
            }, f)

        # Test case 2: One caption
        video_dir_1 = videos_dir / "video-one-caption"
        video_dir_1.mkdir()
        with open(video_dir_1 / "metadata.json", "w") as f:
            json.dump({
                "video_id": "vid1",
                "title": "One Caption",
                "captions_available": ["en"],
            }, f)

        # Test case 3: Multiple captions
        video_dir_3 = videos_dir / "video-multi-captions"
        video_dir_3.mkdir()
        with open(video_dir_3 / "metadata.json", "w") as f:
            json.dump({
                "video_id": "vid3",
                "title": "Multi Captions",
                "captions_available": ["en", "es", "fr", "de"],
            }, f)

        # Generate TSV
        tsv_path = export_service.generate_videos_tsv()

        with open(tsv_path, "r") as f:
            lines = f.readlines()

        # Parse captions values
        header = lines[0].strip().split("\t")
        captions_idx = header.index("captions")

        caption_values = [line.strip().split("\t")[captions_idx] for line in lines[1:]]

        # Verify counts (not booleans)
        assert "0" in caption_values, "Should have '0' for no captions"
        assert "1" in caption_values, "Should have '1' for one caption"
        assert "4" in caption_values, "Should have '4' for four captions"
        assert "true" not in caption_values and "false" not in caption_values, \
            "Should not have boolean values"


@pytest.mark.ai_generated
def test_video_path_without_id():
    """Test that video paths don't include video_id by default."""
    from annextube.services.archiver import Archiver, sanitize_filename
    from annextube.lib.config import Config

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create config with default pattern
        config = Config(
            organization=OrganizationConfig(
                video_path_pattern="{date}_{sanitized_title}"
            )
        )

        archiver = Archiver(repo_path, config)

        # Create mock video with all required fields
        video = Video(
            video_id="test_id_123",
            title="Test Video Title",
            description="Test description",
            channel_id="channel123",
            channel_name="Test Channel",
            published_at=datetime(2020, 1, 10),
            duration=300,
            view_count=1000,
            like_count=50,
            comment_count=10,
            thumbnail_url="https://example.com/thumb.jpg",
            license="standard",
            privacy_status="public",
            availability="public",
            tags=[],
            categories=[],
            captions_available=[],
            has_auto_captions=False,
            download_status="not_downloaded",
            source_url="https://youtube.com/watch?v=test_id_123",
            fetched_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Get expected path
        path = archiver._get_video_path(video)

        # Verify path does NOT contain video_id
        path_str = path.name
        assert "test_id_123" not in path_str, \
            "Path should not contain video_id by default"
        assert "2020-01-10" in path_str, "Path should contain date"
        assert "Test-Video-Title" in path_str, "Path should contain sanitized title (with preserved casing)"

        # Expected format: {date}_{sanitized_title}
        expected = "2020-01-10_Test-Video-Title"
        assert path_str == expected, \
            f"Expected '{expected}', got '{path_str}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
