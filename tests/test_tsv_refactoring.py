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
    assert components.comments_depth is None, "Comments should be unlimited by default (None = fetch all)"

    # Test OrganizationConfig
    org = OrganizationConfig()
    assert org.video_path_pattern == "{year}/{month}/{date}_{sanitized_title}", \
        "Default video_path_pattern should use hierarchical organization"
    assert org.playlist_video_pattern == "{video_index:04d}_{video_path_basename}", \
        "Default playlist_video_pattern should use 4-digit index and video basename"


@pytest.mark.ai_generated
def test_videos_tsv_structure(tmp_path: Path):
    """Test videos.tsv has correct structure (location, columns, order)."""
    repo_path = tmp_path
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
    with open(tsv_path) as f:
        lines = f.readlines()

    # Check header - actual TSV structure matches VideoTSVRow interface
    header = lines[0].strip()
    expected_columns = [
        "video_id", "title", "channel_id", "channel_name", "published_at",
        "duration", "view_count", "like_count", "comment_count",
        "thumbnail_url", "download_status", "source_url", "path"
    ]
    actual_columns = header.split("\t")
    assert actual_columns == expected_columns, \
        f"Column order incorrect. Expected {expected_columns}, got {actual_columns}"

    # Check first column is video_id
    assert actual_columns[0] == "video_id", "First column should be 'video_id'"

    # Check 'path' is included
    assert "path" in actual_columns, "Should have 'path' column"

    # Check download_status is included
    assert "download_status" in actual_columns, "Should have 'download_status' column"

    # Check data row
    data_row = lines[1].strip().split("\t")
    video_id_idx = actual_columns.index("video_id")
    title_idx = actual_columns.index("title")
    path_idx = actual_columns.index("path")
    download_status_idx = actual_columns.index("download_status")

    assert data_row[video_id_idx] == "test123", "video_id should match"
    assert data_row[title_idx] == "Test Video", "title should match"
    assert data_row[path_idx] == "2020-01-10_test-video", \
        "path should be relative directory name"
    assert data_row[download_status_idx] == "metadata_only", \
        "download_status should be metadata_only (no video.mkv file)"


@pytest.mark.ai_generated
def test_playlists_tsv_structure(tmp_path: Path):
    """Test playlists.tsv has correct structure (location, columns, order)."""
    repo_path = tmp_path
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
    with open(tsv_path) as f:
        lines = f.readlines()

    # Check header - actual TSV structure matches PlaylistTSVRow interface
    header = lines[0].strip()
    expected_columns = [
        "playlist_id", "title", "channel_id", "channel_name",
        "video_count", "total_duration", "privacy_status",
        "created_at", "last_sync", "path"
    ]
    actual_columns = header.split("\t")
    assert actual_columns == expected_columns, \
        f"Column order incorrect. Expected {expected_columns}, got {actual_columns}"

    # Check first column is playlist_id
    assert actual_columns[0] == "playlist_id", "First column should be 'playlist_id'"

    # Check 'path' is included
    assert "path" in actual_columns, "Should have 'path' column"

    # Check data row
    data_row = lines[1].strip().split("\t")
    playlist_id_idx = actual_columns.index("playlist_id")
    title_idx = actual_columns.index("title")
    path_idx = actual_columns.index("path")

    assert data_row[playlist_id_idx] == "PLtest123", "playlist_id should match"
    assert data_row[title_idx] == "Test Playlist", "title should match"
    assert data_row[path_idx] == "test-playlist", \
        "path should be relative directory name"


@pytest.mark.ai_generated
def test_multiple_videos_with_different_metadata(tmp_path: Path):
    """Test that TSV correctly handles multiple videos with varied metadata."""
    repo_path = tmp_path
    export_service = ExportService(repo_path)

    videos_dir = repo_path / "videos"
    videos_dir.mkdir()

    # Test case 1: Minimal metadata
    video_dir_0 = videos_dir / "video-minimal"
    video_dir_0.mkdir()
    with open(video_dir_0 / "metadata.json", "w") as f:
        json.dump({
            "video_id": "vid0",
            "title": "Minimal Video",
        }, f)

    # Test case 2: Full metadata
    video_dir_1 = videos_dir / "video-full"
    video_dir_1.mkdir()
    with open(video_dir_1 / "metadata.json", "w") as f:
        json.dump({
            "video_id": "vid1",
            "title": "Full Video",
            "channel_id": "UC123",
            "channel_name": "Test Channel",
            "published_at": "2020-01-10T00:00:00Z",
            "duration": 300,
            "view_count": 1000,
            "like_count": 50,
            "comment_count": 10,
            "captions_available": ["en"],
        }, f)

    # Test case 3: Video with special characters in title
    video_dir_2 = videos_dir / "video-special"
    video_dir_2.mkdir()
    with open(video_dir_2 / "metadata.json", "w") as f:
        json.dump({
            "video_id": "vid2",
            "title": "Video: Special & Characters!",
        }, f)

    # Generate TSV
    tsv_path = export_service.generate_videos_tsv()

    with open(tsv_path) as f:
        lines = f.readlines()

    # Verify correct number of entries (header + 3 videos)
    assert len(lines) == 4, f"Expected 4 lines (header + 3 videos), got {len(lines)}"

    # Verify all videos are present
    video_ids = []
    for line in lines[1:]:
        fields = line.strip().split("\t")
        video_ids.append(fields[0])  # video_id is first column

    assert "vid0" in video_ids, "Should have minimal video"
    assert "vid1" in video_ids, "Should have full video"
    assert "vid2" in video_ids, "Should have video with special characters"


@pytest.mark.ai_generated
def test_video_path_without_id(tmp_path: Path):
    """Test that video paths don't include video_id by default."""
    from annextube.lib.config import Config
    from annextube.services.archiver import Archiver

    repo_path = tmp_path

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


@pytest.mark.ai_generated
def test_vtt_langs_extraction_with_variants():
    """Test that VTT language extraction preserves variant codes like en-cur1.

    When a video directory contains both video.en.vtt and video.en-cur1.vtt,
    both language codes should appear in captions_available.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        export_service = ExportService(repo_path)

        videos_dir = repo_path / "videos"
        videos_dir.mkdir()

        video_dir = videos_dir / "2026-01-test-video"
        video_dir.mkdir()

        # Create metadata.json with NO captions_available (will be reconciled)
        metadata = {
            "video_id": "test_variants",
            "title": "Caption Variants Test",
        }
        with open(video_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)

        # Create VTT files with various language codes:
        # - simple codes (en, es)
        # - yt-dlp variant codes (en-cur1, en-orig)
        # - standard BCP 47 codes (pt-BR, zh-Hans)
        vtt_content = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nTest\n"
        for lang in ["en", "en-cur1", "en-orig", "es", "pt-BR", "zh-Hans"]:
            vtt_path = video_dir / f"video.{lang}.vtt"
            vtt_path.write_text(vtt_content)

        # Generate TSV (triggers vtt_langs reconciliation)
        export_service.generate_videos_tsv()

        # Read back metadata.json to check captions_available was updated
        with open(video_dir / "metadata.json") as f:
            updated_metadata = json.load(f)

        captions = updated_metadata.get("captions_available", [])
        assert "en" in captions, "Simple code 'en' should be preserved"
        assert "en-cur1" in captions, "Variant code 'en-cur1' should be preserved"
        assert "en-orig" in captions, "Variant code 'en-orig' should be preserved"
        assert "es" in captions, "Simple code 'es' should be preserved"
        assert "pt-BR" in captions, "BCP 47 code 'pt-BR' should be preserved"
        assert "zh-Hans" in captions, "BCP 47 code 'zh-Hans' should be preserved"
        assert len(captions) == 6, f"Expected 6 captions, got {len(captions)}: {captions}"

        # Verify sorted order
        assert captions == sorted(captions), "captions_available should be sorted"


@pytest.mark.ai_generated
def test_vtt_langs_extraction_skips_bare_video_vtt():
    """Test that video.vtt (without language code) is skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        export_service = ExportService(repo_path)

        videos_dir = repo_path / "videos"
        videos_dir.mkdir()

        video_dir = videos_dir / "2026-01-test-video"
        video_dir.mkdir()

        metadata = {
            "video_id": "test_bare",
            "title": "Bare VTT Test",
        }
        with open(video_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)

        vtt_content = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nTest\n"
        # video.vtt has no language code and should be skipped
        (video_dir / "video.vtt").write_text(vtt_content)
        # video.en.vtt has a language code and should be included
        (video_dir / "video.en.vtt").write_text(vtt_content)

        export_service.generate_videos_tsv()

        with open(video_dir / "metadata.json") as f:
            updated_metadata = json.load(f)

        captions = updated_metadata.get("captions_available", [])
        assert captions == ["en"], f"Expected ['en'], got {captions}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
