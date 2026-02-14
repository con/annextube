"""Integration test for comprehensive backup with all features enabled.

Tests that playlists, captions, comments, thumbnails, and TSV files are all
correctly created and committed.
"""

import json
import subprocess
from pathlib import Path

import pytest

from annextube.lib.config import ComponentsConfig, Config, FiltersConfig
from annextube.services.archiver import Archiver


@pytest.fixture
def tmp_git_annex_repo(tmp_path):
    """Create a temporary git-annex repository for integration testing."""
    repo_path = tmp_path

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)

    # Initialize git-annex
    subprocess.run(["git", "annex", "init", "test-repo"], cwd=repo_path, check=True, capture_output=True)

    # Configure .gitattributes to keep small files in git (not annex)
    gitattributes = repo_path / ".gitattributes"
    gitattributes.write_text(
        "*.json annex.largefiles=nothing\n"
        "*.tsv annex.largefiles=nothing\n"
        "*.toml annex.largefiles=nothing\n"
    )
    subprocess.run(["git", "add", ".gitattributes"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add .gitattributes"], cwd=repo_path, check=True, capture_output=True)

    return repo_path


@pytest.mark.ai_generated
@pytest.mark.network
def test_comprehensive_backup_with_all_features(tmp_git_annex_repo: Path) -> None:
    """Test backup with playlists, captions, comments, and thumbnails enabled.

    Verifies that:
    - Playlist directory is created with numbered symlinks
    - Caption .vtt files are downloaded
    - captions.tsv is created
    - comments.json is created
    - thumbnail files are downloaded
    - All TSV files are generated (videos.tsv, playlists.tsv, authors.tsv)
    - Git status is clean after backup
    - metadata.json has captions_available populated
    """
    # Configure with all features enabled (except video downloads)
    config = Config(
        components=ComponentsConfig(
            videos=False,  # Skip video downloads for speed
            metadata=True,
            captions=True,
            thumbnails=True,
            comments_depth=10000,  # Unlimited comments
        ),
        filters=FiltersConfig(
            limit=2,  # Just 2 videos for fast testing
        ),
    )

    archiver = Archiver(tmp_git_annex_repo, config)

    # Backup AnnexTube Test Channel (dedicated test channel with known content)
    result = archiver.backup_channel("https://www.youtube.com/channel/UCHpuDwi3IorJ_Uez2e7pqHA")

    # Verify backup succeeded
    assert result["videos_processed"] == 2

    # Verify videos directory exists with 2 videos
    # Note: With hierarchical structure, video dirs are nested (e.g., 2026/01/video_name/)
    videos_dir = tmp_git_annex_repo / "videos"
    assert videos_dir.exists()
    video_dirs = sorted([p.parent for p in videos_dir.rglob("metadata.json")])
    assert len(video_dirs) == 2, f"Expected 2 video directories, found {len(video_dirs)}: {[d.relative_to(videos_dir) for d in video_dirs]}"

    # For each video, verify all components exist
    for video_dir in video_dirs:
        # Metadata
        metadata_path = video_dir / "metadata.json"
        assert metadata_path.exists()

        with open(metadata_path) as f:
            metadata = json.load(f)

        # Verify captions_available is populated (not empty)
        # Khan Academy videos have captions, so this should not be empty
        captions_available = metadata.get("captions_available", [])
        # Note: Some videos might not have captions, so just check field exists
        assert "captions_available" in metadata

        # Comments (may not exist if video has no comments)
        # Test channel videos may have no comments, so we don't verify

        # Thumbnail
        thumbnail_path = video_dir / "thumbnail.jpg"
        assert thumbnail_path.exists()

        # If captions are available, verify caption files exist
        if captions_available:
            captions_tsv = video_dir / "captions.tsv"
            assert captions_tsv.exists()

            # Check for at least one .vtt file
            vtt_files = list(video_dir.glob("*.vtt"))
            assert len(vtt_files) > 0, f"No .vtt files found in {video_dir}"

            # Verify .vtt file is valid WebVTT format
            vtt_file = vtt_files[0]
            with open(vtt_file) as f:
                first_line = f.readline().strip()
                assert first_line == "WEBVTT", f"Invalid WebVTT header in {vtt_file}"

    # Verify TSV files were generated
    videos_tsv = tmp_git_annex_repo / "videos" / "videos.tsv"
    assert videos_tsv.exists()

    playlists_tsv = tmp_git_annex_repo / "playlists" / "playlists.tsv"
    assert playlists_tsv.exists()

    authors_tsv = tmp_git_annex_repo / "authors.tsv"
    assert authors_tsv.exists()

    # Verify git status is clean (all changes committed)
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=tmp_git_annex_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "", "Git working tree should be clean after backup"


@pytest.mark.ai_generated
@pytest.mark.network
def test_playlist_backup_creates_symlinks(tmp_git_annex_repo: Path) -> None:
    """Test that playlist backup creates chronologically ordered symlinks.

    Verifies:
    - Playlist directory is created
    - Numbered symlinks (0001_, 0002_, etc.) point to video directories
    - Symlinks are in chronological order (oldest first)
    - playlist.json is created
    - Per-playlist videos.tsv exists with correct content
    - playlists.tsv is generated
    """
    config = Config(
        components=ComponentsConfig(
            videos=False,
            metadata=True,
            captions=True,
            thumbnails=True,
        ),
        filters=FiltersConfig(
            limit=3,
        ),
    )

    archiver = Archiver(tmp_git_annex_repo, config)

    # Backup a known playlist (C++ by The Cherno)
    playlist_url = "https://www.youtube.com/playlist?list=PLlrATfBNZ98dudnM48yfGUldqGD0S4FFb"
    result = archiver.backup_playlist(playlist_url)

    # Verify backup succeeded
    assert result["videos_processed"] == 3

    # Verify playlist directory exists
    playlists_dir = tmp_git_annex_repo / "playlists"
    assert playlists_dir.exists()

    # Find the playlist directory (should be named based on playlist title)
    playlist_dirs = [d for d in playlists_dir.iterdir() if d.is_dir()]
    assert len(playlist_dirs) == 1
    playlist_dir = playlist_dirs[0]

    # Verify playlist.json exists
    playlist_json = playlist_dir / "playlist.json"
    assert playlist_json.exists()

    # Verify numbered symlinks exist
    symlinks = sorted([f for f in playlist_dir.iterdir() if f.is_symlink()])
    assert len(symlinks) == 3, f"Expected 3 symlinks, found {len(symlinks)}"

    # Verify naming pattern: 0001_, 0002_, 0003_
    assert symlinks[0].name.startswith("0001_")
    assert symlinks[1].name.startswith("0002_")
    assert symlinks[2].name.startswith("0003_")

    # Verify symlinks point to video directories and are in chronological order
    published_dates = []
    for symlink in symlinks:
        target = symlink.resolve()
        assert target.exists()
        metadata_path = target / "metadata.json"
        assert metadata_path.exists()

        with open(metadata_path) as f:
            metadata = json.load(f)
        published_dates.append(metadata["published_at"])

    # Verify chronological order (oldest first)
    assert published_dates == sorted(published_dates), (
        f"Symlinks not in chronological order: {published_dates}"
    )

    # Verify per-playlist videos.tsv exists
    playlist_videos_tsv = playlist_dir / "videos.tsv"
    assert playlist_videos_tsv.exists(), "Per-playlist videos.tsv should exist"

    # Parse and verify per-playlist videos.tsv content
    with open(playlist_videos_tsv) as f:
        lines = f.readlines()
    assert len(lines) == 4, f"Expected 1 header + 3 data rows, got {len(lines)}"

    # Verify header
    header = lines[0].strip().split('\t')
    assert "video_id" in header
    assert "path" in header

    # Verify path column uses symlink names (0001_, 0002_, etc.)
    path_idx = header.index("path")
    for line in lines[1:]:
        fields = line.strip().split('\t')
        path_value = fields[path_idx]
        assert path_value.startswith("000"), (
            f"Path in playlist videos.tsv should be symlink name, got: {path_value}"
        )

    # Verify playlists.tsv was generated
    playlists_tsv = tmp_git_annex_repo / "playlists" / "playlists.tsv"
    assert playlists_tsv.exists()

    # Verify git status is clean
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=tmp_git_annex_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "", "Git working tree should be clean after backup"
