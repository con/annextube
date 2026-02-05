"""Unit tests for hierarchical video path pattern with year/month subdirectories.

Tests that the new hierarchical structure works correctly:
- Videos are organized in year/month subdirectories
- Playlist symlinks correctly point to hierarchical paths
- Custom patterns can be specified via --video-path-pattern
"""

from datetime import datetime
from pathlib import Path

import pytest

from annextube.lib.config import OrganizationConfig
from annextube.models.video import Video
from annextube.services.archiver import Archiver


@pytest.mark.ai_generated
def test_default_pattern_is_hierarchical() -> None:
    """Verify default video_path_pattern includes year/month hierarchy."""
    config = OrganizationConfig()
    assert config.video_path_pattern == "{year}/{month}/{date}_{sanitized_title}"


@pytest.mark.ai_generated
def test_video_path_with_hierarchical_pattern(tmp_path: Path) -> None:
    """Test that _get_video_path generates year/month subdirectories."""
    from annextube.lib.config import ComponentsConfig, Config

    # Create config with hierarchical pattern
    config = Config(
        components=ComponentsConfig(),
        organization=OrganizationConfig(
            video_path_pattern="{year}/{month}/{date}_{sanitized_title}"
        )
    )

    # Create archiver (doesn't need real git-annex for path testing)
    archiver = Archiver(tmp_path, config)

    # Create video with known date
    video = Video(
        video_id="test123",
        title="Test Video Title",
        description="Test description",
        channel_id="UC123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 28, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=100,
        comment_count=0,
        thumbnail_url="https://example.com/thumb.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=[],
        categories=[],
        captions_available=[],
        has_auto_captions=False,
        download_status="not_downloaded",
        source_url="https://youtube.com/watch?v=test123",
        fetched_at=datetime(2026, 1, 28, 12, 0, 0),
    )

    # Get video path
    video_path = archiver._get_video_path(video)

    # Verify hierarchical structure: videos/2026/01/2026-01-28_Test-Video-Title
    # Note: sanitize_filename preserves original casing
    expected = tmp_path / "videos" / "2026" / "01" / "2026-01-28_Test-Video-Title"
    assert video_path == expected


@pytest.mark.ai_generated
def test_video_path_with_flat_pattern(tmp_path: Path) -> None:
    """Test backward compatibility with flat pattern."""
    from annextube.lib.config import ComponentsConfig, Config

    # Create config with flat pattern (old default)
    config = Config(
        components=ComponentsConfig(),
        organization=OrganizationConfig(
            video_path_pattern="{date}_{sanitized_title}"
        )
    )

    archiver = Archiver(tmp_path, config)

    video = Video(
        video_id="test123",
        title="Test Video Title",
        description="Test description",
        channel_id="UC123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 28, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=100,
        comment_count=0,
        thumbnail_url="https://example.com/thumb.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=[],
        categories=[],
        captions_available=[],
        has_auto_captions=False,
        download_status="not_downloaded",
        source_url="https://youtube.com/watch?v=test123",
        fetched_at=datetime(2026, 1, 28, 12, 0, 0),
    )

    video_path = archiver._get_video_path(video)

    # Verify flat structure: videos/2026-01-28_Test-Video-Title
    # Note: sanitize_filename preserves original casing
    expected = tmp_path / "videos" / "2026-01-28_Test-Video-Title"
    assert video_path == expected


@pytest.mark.ai_generated
def test_video_path_with_custom_pattern(tmp_path: Path) -> None:
    """Test custom pattern with only year (no month)."""
    from annextube.lib.config import ComponentsConfig, Config

    config = Config(
        components=ComponentsConfig(),
        organization=OrganizationConfig(
            video_path_pattern="{year}/{date}_{video_id}"
        )
    )

    archiver = Archiver(tmp_path, config)

    video = Video(
        video_id="test123",
        title="Test Video Title",
        description="Test description",
        channel_id="UC123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 28, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=100,
        comment_count=0,
        thumbnail_url="https://example.com/thumb.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=[],
        categories=[],
        captions_available=[],
        has_auto_captions=False,
        download_status="not_downloaded",
        source_url="https://youtube.com/watch?v=test123",
        fetched_at=datetime(2026, 1, 28, 12, 0, 0),
    )

    video_path = archiver._get_video_path(video)

    # Verify custom structure: videos/2026/2026-01-28_test123
    expected = tmp_path / "videos" / "2026" / "2026-01-28_test123"
    assert video_path == expected


@pytest.mark.ai_generated
def test_playlist_symlink_with_hierarchical_paths(tmp_path: Path) -> None:
    """Test that playlist symlinks correctly point to hierarchical video directories.

    This is critical - symlinks must use relative_to() to support subdirectories.
    """
    from annextube.lib.config import ComponentsConfig, Config

    # Create hierarchical config
    config = Config(
        components=ComponentsConfig(),
        organization=OrganizationConfig(
            video_path_pattern="{year}/{month}/{date}_{sanitized_title}",
            playlist_prefix_width=4,
            playlist_prefix_separator="_"
        )
    )

    archiver = Archiver(tmp_path, config)

    # Create a video with hierarchical path
    video = Video(
        video_id="test123",
        title="Test Video",
        description="Test description",
        channel_id="UC123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 28, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=100,
        comment_count=0,
        thumbnail_url="https://example.com/thumb.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=[],
        categories=[],
        captions_available=[],
        has_auto_captions=False,
        download_status="not_downloaded",
        source_url="https://youtube.com/watch?v=test123",
        fetched_at=datetime(2026, 1, 28, 12, 0, 0),
    )

    # Get video path and create the directory
    video_dir = archiver._get_video_path(video)
    video_dir.mkdir(parents=True, exist_ok=True)

    # Create playlist directory
    playlist_dir = tmp_path / "playlists" / "test-playlist"
    playlist_dir.mkdir(parents=True, exist_ok=True)

    # Create symlink (simulating what backup_playlist does)
    prefix = f"{1:04d}_"  # First video, width=4
    symlink_name = f"{prefix}{video_dir.name}"
    symlink_path = playlist_dir / symlink_name

    # Calculate relative target (this is what the code should do)
    relative_target = Path("..") / ".." / video_dir.relative_to(tmp_path)

    # Create symlink
    symlink_path.symlink_to(relative_target)

    # Verify symlink exists and points correctly
    assert symlink_path.exists()
    assert symlink_path.is_symlink()

    # Verify symlink resolves to video directory
    assert symlink_path.resolve() == video_dir.resolve()

    # Verify symlink target is relative (for portability)
    # Expected: ../../videos/2026/01/2026-01-28_Test-Video
    # Note: sanitize_filename preserves original casing
    expected_target = Path("..") / ".." / "videos" / "2026" / "01" / "2026-01-28_Test-Video"
    assert symlink_path.readlink() == expected_target


@pytest.mark.ai_generated
def test_multiple_videos_different_months(tmp_path: Path) -> None:
    """Test that videos from different months go into separate subdirectories."""
    from annextube.lib.config import ComponentsConfig, Config

    config = Config(
        components=ComponentsConfig(),
        organization=OrganizationConfig(
            video_path_pattern="{year}/{month}/{date}_{sanitized_title}"
        )
    )

    archiver = Archiver(tmp_path, config)

    # Video from January 2026
    video1 = Video(
        video_id="jan_video",
        title="January Video",
        description="Test description",
        channel_id="UC123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 15, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=100,
        comment_count=0,
        thumbnail_url="https://example.com/thumb.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=[],
        categories=[],
        captions_available=[],
        has_auto_captions=False,
        download_status="not_downloaded",
        source_url="https://youtube.com/watch?v=jan_video",
        fetched_at=datetime(2026, 1, 15, 12, 0, 0),
    )

    # Video from February 2026
    video2 = Video(
        video_id="feb_video",
        title="February Video",
        description="Test description",
        channel_id="UC123",
        channel_name="Test Channel",
        published_at=datetime(2026, 2, 20, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=100,
        comment_count=0,
        thumbnail_url="https://example.com/thumb.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=[],
        categories=[],
        captions_available=[],
        has_auto_captions=False,
        download_status="not_downloaded",
        source_url="https://youtube.com/watch?v=feb_video",
        fetched_at=datetime(2026, 2, 20, 12, 0, 0),
    )

    path1 = archiver._get_video_path(video1)
    path2 = archiver._get_video_path(video2)

    # Verify they're in different month directories
    # Note: sanitize_filename preserves original casing
    assert path1 == tmp_path / "videos" / "2026" / "01" / "2026-01-15_January-Video"
    assert path2 == tmp_path / "videos" / "2026" / "02" / "2026-02-20_February-Video"

    # Verify they share the same year directory
    assert path1.parent.parent == path2.parent.parent  # Both under videos/2026/


@pytest.mark.ai_generated
def test_config_template_includes_hierarchical_pattern() -> None:
    """Test that generated config template uses hierarchical pattern."""
    from annextube.lib.config import generate_config_template

    template = generate_config_template()

    # Verify template shows hierarchical pattern in config value
    assert 'video_path_pattern = "{year}/{month}/{date}_{sanitized_title}"' in template

    # Verify documentation mentions year and month placeholders (with double braces for escaping)
    assert "{{year}}" in template or "{{{{year}}}}" in template  # Either double or quad braces
    assert "{{month}}" in template or "{{{{month}}}}" in template


@pytest.mark.ai_generated
def test_config_template_with_custom_pattern() -> None:
    """Test that custom pattern is written to config template."""
    from annextube.lib.config import generate_config_template

    custom_pattern = "{date}_{video_id}"
    template = generate_config_template(video_path_pattern=custom_pattern)

    # Verify custom pattern appears in template
    assert f'video_path_pattern = "{custom_pattern}"' in template


@pytest.mark.ai_generated
def test_video_path_with_invalid_placeholder_raises_error(tmp_path: Path) -> None:
    """Test that invalid placeholders in video_path_pattern raise ValueError."""
    from annextube.lib.config import ComponentsConfig, Config

    # Create config with invalid placeholder {invalid_placeholder}
    config = Config(
        components=ComponentsConfig(),
        organization=OrganizationConfig(
            video_path_pattern="{year}/{invalid_placeholder}/{date}_{sanitized_title}"
        )
    )

    archiver = Archiver(tmp_path, config)

    video = Video(
        video_id="test123",
        title="Test Video",
        description="Test description",
        channel_id="UC123",
        channel_name="Test Channel",
        published_at=datetime(2026, 1, 28, 12, 0, 0),
        duration=300,
        view_count=1000,
        like_count=100,
        comment_count=0,
        thumbnail_url="https://example.com/thumb.jpg",
        license="standard",
        privacy_status="public",
        availability="public",
        tags=[],
        categories=[],
        captions_available=[],
        has_auto_captions=False,
        download_status="not_downloaded",
        source_url="https://youtube.com/watch?v=test123",
        fetched_at=datetime(2026, 1, 28, 12, 0, 0),
    )

    # Should raise ValueError with helpful message
    with pytest.raises(ValueError) as exc_info:
        archiver._get_video_path(video)

    error_msg = str(exc_info.value)
    assert "invalid_placeholder" in error_msg
    assert "video_path_pattern" in error_msg
    assert "Valid placeholders:" in error_msg


@pytest.mark.ai_generated
def test_playlist_path_with_invalid_placeholder_raises_error(tmp_path: Path) -> None:
    """Test that invalid placeholders in playlist_path_pattern raise ValueError."""
    from annextube.lib.config import ComponentsConfig, Config
    from annextube.models.playlist import Playlist

    # Create config with invalid placeholder {playlist_name}
    config = Config(
        components=ComponentsConfig(),
        organization=OrganizationConfig(
            playlist_path_pattern="{playlist_name}"  # Should be {playlist_title}
        )
    )

    archiver = Archiver(tmp_path, config)

    playlist = Playlist(
        playlist_id="PLtest123",
        title="Test Playlist",
        description="Test description",
        channel_id="UC123",
        channel_name="Test Channel",
        video_count=5,
        privacy_status="public",
        last_modified=datetime(2026, 1, 28, 0, 0, 0),
        video_ids=["vid1", "vid2"],
        fetched_at=datetime(2026, 1, 28, 0, 0, 0),
    )

    # Should raise ValueError with helpful message
    with pytest.raises(ValueError) as exc_info:
        archiver._get_playlist_path(playlist)

    error_msg = str(exc_info.value)
    assert "playlist_name" in error_msg
    assert "playlist_path_pattern" in error_msg
    assert "Valid placeholders:" in error_msg
    assert "playlist_title" in error_msg  # Should suggest the correct placeholder
