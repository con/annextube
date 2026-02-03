"""End-to-end integration test: verify backup produces captions, playlists, clean git status.

Uses real YouTube API (yt-dlp) with small limits to verify all features work.
Videos are NOT downloaded (videos=false) to keep tests fast.

Requires network access and yt-dlp installed.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


def _init_annex_repo(repo_path: Path) -> None:
    """Initialize a git-annex repo at repo_path."""
    cmds = [
        ["git", "init"],
        ["git", "config", "user.name", "Test User"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "annex", "init", "test-repo"],
    ]
    for cmd in cmds:
        subprocess.run(cmd, cwd=repo_path, check=True, capture_output=True)

    # .gitattributes: keep small files in git
    (repo_path / ".gitattributes").write_text(
        "*.json annex.largefiles=nothing\n"
        "*.tsv annex.largefiles=nothing\n"
        "*.vtt annex.largefiles=nothing\n"
    )
    subprocess.run(["git", "add", ".gitattributes"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_path, check=True, capture_output=True)


def _git_status_clean(repo_path: Path) -> bool:
    """Return True if git working tree is clean."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip() == ""


@pytest.mark.ai_generated
@pytest.mark.network
class TestE2EBackupFeatures:
    """End-to-end tests requiring network access to YouTube."""

    def test_channel_backup_metadata_and_captions(self) -> None:
        """Backup a channel (no playlists), verify metadata + captions + thumbnails + clean git."""
        from annextube.lib.config import ComponentsConfig, Config, FiltersConfig, SourceConfig
        from annextube.services.archiver import Archiver

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            _init_annex_repo(repo_path)

            config = Config(
                sources=[
                    SourceConfig(
                        url="https://www.youtube.com/@yarikoptic",
                        type="channel",
                        include_playlists="none",
                    ),
                ],
                components=ComponentsConfig(
                    videos=False,
                    metadata=True,
                    captions=True,
                    thumbnails=True,
                    comments_depth=10,
                ),
                filters=FiltersConfig(limit=2),
            )

            archiver = Archiver(repo_path, config)
            source = config.sources[0]
            archiver.backup_channel(source.url, source)

            # --- Verify videos directory has content ---
            # Note: With hierarchical structure, video dirs are nested (e.g., 2018/11/video_name/)
            videos_dir = repo_path / "videos"
            assert videos_dir.exists(), "videos/ directory should exist"
            video_dirs = [p.parent for p in videos_dir.rglob("metadata.json")]
            assert len(video_dirs) >= 1, f"Should have at least 1 video dir, got {len(video_dirs)}"

            # --- Verify metadata.json exists for each video ---
            for vdir in video_dirs:
                metadata_file = vdir / "metadata.json"
                assert metadata_file.exists(), f"Missing metadata.json in {vdir.relative_to(videos_dir)}"
                data = json.loads(metadata_file.read_text())
                assert "video_id" in data
                assert "title" in data

            # --- Verify captions (may or may not exist depending on channel) ---
            caption_files = list(videos_dir.rglob("*.vtt"))
            captions_tsvs = list(videos_dir.rglob("captions.tsv"))
            if caption_files:
                assert len(captions_tsvs) >= 1, "If .vtt files exist, captions.tsv should too"

            # --- Verify TSV exports ---
            videos_tsv = repo_path / "videos" / "videos.tsv"
            assert videos_tsv.exists(), "videos.tsv should exist"
            lines = videos_tsv.read_text().strip().split("\n")
            assert len(lines) >= 2, "videos.tsv should have header + at least 1 data row"

            # --- Verify thumbnails ---
            thumbnails = list(videos_dir.rglob("thumbnail.jpg"))
            assert len(thumbnails) >= 1, "Expected at least 1 thumbnail"

            # --- Verify git status is clean ---
            assert _git_status_clean(repo_path), (
                "Git working tree should be clean after backup. "
                f"Status: {subprocess.run(['git', 'status', '--porcelain'], cwd=repo_path, capture_output=True, text=True).stdout}"
            )

    def test_playlist_backup_with_captions(self) -> None:
        """Backup a specific playlist, verify captions and symlinks."""
        from annextube.lib.config import ComponentsConfig, Config, FiltersConfig
        from annextube.services.archiver import Archiver

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            _init_annex_repo(repo_path)

            config = Config(
                components=ComponentsConfig(
                    videos=False,
                    metadata=True,
                    captions=True,
                    thumbnails=False,
                    comments_depth=0,  # skip comments for speed
                ),
                filters=FiltersConfig(limit=2),
            )

            archiver = Archiver(repo_path, config)
            # Use a 3Blue1Brown playlist known to have captioned videos
            # "Essence of linear algebra" playlist
            archiver.backup_playlist("https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab")

            # --- Verify videos ---
            videos_dir = repo_path / "videos"
            assert videos_dir.exists(), "videos/ directory should exist"
            video_dirs = [d for d in videos_dir.iterdir() if d.is_dir()]
            assert len(video_dirs) >= 1, f"Should have at least 1 video, got {len(video_dirs)}"

            # --- Verify captions ---
            caption_files = list(videos_dir.rglob("*.vtt"))
            assert len(caption_files) >= 1, (
                f"Expected at least 1 caption file. Video dirs: {[d.name for d in video_dirs]}"
            )

            # --- Verify playlist symlinks ---
            playlists_dir = repo_path / "playlists"
            assert playlists_dir.exists(), "playlists/ directory should exist"
            playlist_dirs = [d for d in playlists_dir.iterdir() if d.is_dir()]
            assert len(playlist_dirs) == 1, f"Expected exactly 1 playlist dir, got {len(playlist_dirs)}"

            pdir = playlist_dirs[0]
            symlinks = [f for f in pdir.iterdir() if f.is_symlink()]
            assert len(symlinks) >= 1, f"Expected playlist symlinks, got {len(symlinks)}"

            # Symlinks should have numeric prefixes (ordered)
            for sl in symlinks:
                assert sl.name[0].isdigit(), f"Symlink should start with digit: {sl.name}"

            # --- Verify playlist.json ---
            pjson = pdir / "playlist.json"
            assert pjson.exists(), "playlist.json should exist"
            pdata = json.loads(pjson.read_text())
            assert "video_ids" in pdata
            assert len(pdata["video_ids"]) >= 1

            # --- Verify git status clean ---
            assert _git_status_clean(repo_path), (
                "Git should be clean after backup. "
                f"Status: {subprocess.run(['git', 'status', '--porcelain'], cwd=repo_path, capture_output=True, text=True).stdout}"
            )
