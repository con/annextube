"""Integration tests for periodic checkpoint commits during backup."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from annextube.lib.config import BackupConfig, ComponentsConfig, Config, FiltersConfig, SourceConfig
from annextube.services.archiver import Archiver


def _init_test_repo(repo_path: Path) -> None:
    """Initialize a git-annex repo for testing."""
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
    )
    subprocess.run(["git", "add", ".gitattributes"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_path, check=True, capture_output=True)


def _get_git_commit_messages(repo_path: Path) -> list[str]:
    """Get list of commit messages from git log."""
    result = subprocess.run(
        ["git", "log", "--format=%s"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def _count_metadata_files(repo_path: Path) -> int:
    """Count metadata.json files in videos directory."""
    videos_dir = repo_path / "videos"
    if not videos_dir.exists():
        return 0
    return len(list(videos_dir.rglob("metadata.json")))


def _create_process_video_mock(archiver):
    """Create a mock for _process_video that actually creates files.

    This is needed so that _has_uncommitted_changes() returns True
    and commits are actually created during checkpoints.
    """
    def mock_process_video(video):
        """Mock that creates actual metadata.json files for git to track."""
        import json

        # Get video directory path using archiver's method
        video_dir = archiver._get_video_path(video)
        video_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata.json
        metadata_file = video_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                "video_id": video.video_id,
                "title": video.title,
                "upload_date": video.upload_date
            }, f, indent=2)

        # Return caption count (0 for this mock)
        return 0

    return mock_process_video


@pytest.mark.ai_generated
class TestCheckpointCommits:
    """Tests for checkpoint commit behavior during backup."""

    def test_checkpoint_creates_intermediate_commits(self):
        """Test that checkpoints create commits at specified intervals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            _init_test_repo(repo_path)

            # Configure with small checkpoint interval (every 2 videos)
            config = Config(
                sources=[SourceConfig(url="test-channel", type="channel")],
                components=ComponentsConfig(videos=False, metadata=True, captions=False),
                filters=FiltersConfig(limit=5),
                backup=BackupConfig(checkpoint_interval=2, checkpoint_enabled=True),
            )

            archiver = Archiver(repo_path, config)

            # Mock YouTube service to return 5 videos
            mock_videos = [
                {"id": f"video{i}", "title": f"Video {i}", "upload_date": "20260101"}
                for i in range(1, 6)
            ]

            with patch.object(archiver.youtube, "get_channel_videos", return_value=mock_videos):
                with patch.object(archiver.youtube, "metadata_to_video") as mock_to_video:
                    # Mock video objects
                    def create_mock_video(meta):
                        video = MagicMock()
                        video.video_id = meta["id"]
                        video.title = meta["title"]
                        video.upload_date = "2026-01-01"
                        return video
                    mock_to_video.side_effect = create_mock_video

                    with patch.object(archiver, "_process_video", side_effect=_create_process_video_mock(archiver)):
                        # Run backup
                        archiver.backup_channel("test-channel")

            # Check commit history
            commits = _get_git_commit_messages(repo_path)

            # Should have: init + checkpoint(2) + checkpoint(4) + final(5)
            assert len(commits) >= 4, f"Expected at least 4 commits, got {len(commits)}: {commits}"

            # Verify checkpoint messages exist
            checkpoint_commits = [c for c in commits if "Checkpoint:" in c]
            assert len(checkpoint_commits) >= 2, f"Expected at least 2 checkpoints, got {checkpoint_commits}"

            # Verify checkpoint messages have correct format
            assert any("2/" in c for c in checkpoint_commits), "Should have checkpoint for 2 videos"
            assert any("4/" in c for c in checkpoint_commits), "Should have checkpoint for 4 videos"

    def test_checkpoint_disabled_creates_single_commit(self):
        """Test that disabling checkpoints creates only final commit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            _init_test_repo(repo_path)

            # Disable checkpoints
            config = Config(
                sources=[SourceConfig(url="test-channel", type="channel")],
                components=ComponentsConfig(videos=False, metadata=True, captions=False),
                filters=FiltersConfig(limit=5),
                backup=BackupConfig(checkpoint_enabled=False),
            )

            archiver = Archiver(repo_path, config)

            # Mock YouTube service
            mock_videos = [
                {"id": f"video{i}", "title": f"Video {i}", "upload_date": "20260101"}
                for i in range(1, 6)
            ]

            with patch.object(archiver.youtube, "get_channel_videos", return_value=mock_videos):
                with patch.object(archiver.youtube, "metadata_to_video") as mock_to_video:
                    def create_mock_video(meta):
                        video = MagicMock()
                        video.video_id = meta["id"]
                        video.title = meta["title"]
                        video.upload_date = "2026-01-01"
                        return video
                    mock_to_video.side_effect = create_mock_video

                    with patch.object(archiver, "_process_video", side_effect=_create_process_video_mock(archiver)):
                        archiver.backup_channel("test-channel")

            # Check commit history
            commits = _get_git_commit_messages(repo_path)

            # Should have: init + final backup (no checkpoints)
            checkpoint_commits = [c for c in commits if "Checkpoint:" in c]
            assert len(checkpoint_commits) == 0, f"Expected 0 checkpoints, got {checkpoint_commits}"

            # Should have final backup commit
            backup_commits = [c for c in commits if "Backup channel:" in c]
            assert len(backup_commits) == 1, f"Expected 1 backup commit, got {backup_commits}"

    def test_checkpoint_regenerates_tsvs(self):
        """Test that checkpoints regenerate TSV files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            _init_test_repo(repo_path)

            config = Config(
                sources=[SourceConfig(url="test-channel", type="channel")],
                components=ComponentsConfig(videos=False, metadata=True, captions=False),
                filters=FiltersConfig(limit=4),
                backup=BackupConfig(checkpoint_interval=2, checkpoint_enabled=True),
            )

            archiver = Archiver(repo_path, config)

            mock_videos = [
                {"id": f"video{i}", "title": f"Video {i}", "upload_date": "20260101"}
                for i in range(1, 5)
            ]

            with patch.object(archiver.youtube, "get_channel_videos", return_value=mock_videos):
                with patch.object(archiver.youtube, "metadata_to_video") as mock_to_video:
                    def create_mock_video(meta):
                        video = MagicMock()
                        video.video_id = meta["id"]
                        video.title = meta["title"]
                        video.upload_date = "2026-01-01"
                        return video
                    mock_to_video.side_effect = create_mock_video

                    with patch.object(archiver, "_process_video", side_effect=_create_process_video_mock(archiver)):
                        # Spy on export.generate_all calls
                        original_generate = archiver.export.generate_all
                        generate_calls = []

                        def track_generate():
                            generate_calls.append(_count_metadata_files(repo_path))
                            return original_generate()

                        with patch.object(archiver.export, "generate_all", side_effect=track_generate):
                            archiver.backup_channel("test-channel")

            # Should have called generate_all at least twice (checkpoints)
            assert len(generate_calls) >= 2, f"Expected at least 2 TSV generations, got {len(generate_calls)}"

            # TSV file should exist
            videos_tsv = repo_path / "videos" / "videos.tsv"
            assert videos_tsv.exists(), "videos.tsv should exist after checkpoint"

    def test_keyboard_interrupt_auto_commits(self):
        """Test that Ctrl+C triggers auto-commit of partial progress."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            _init_test_repo(repo_path)

            config = Config(
                sources=[SourceConfig(url="test-channel", type="channel")],
                components=ComponentsConfig(videos=False, metadata=True, captions=False),
                filters=FiltersConfig(limit=5),
                backup=BackupConfig(
                    checkpoint_interval=10,  # Won't trigger during test
                    auto_commit_on_interrupt=True
                ),
            )

            archiver = Archiver(repo_path, config)

            mock_videos = [
                {"id": f"video{i}", "title": f"Video {i}", "upload_date": "20260101"}
                for i in range(1, 6)
            ]

            with patch.object(archiver.youtube, "get_channel_videos", return_value=mock_videos):
                with patch.object(archiver.youtube, "metadata_to_video") as mock_to_video:
                    def create_mock_video(meta):
                        video = MagicMock()
                        video.video_id = meta["id"]
                        video.title = meta["title"]
                        video.upload_date = "2026-01-01"
                        return video
                    mock_to_video.side_effect = create_mock_video

                    # Simulate Ctrl+C after processing 3 videos
                    process_count = [0]
                    base_mock = _create_process_video_mock(archiver)

                    def process_with_interrupt(video):
                        process_count[0] += 1
                        # Create files for first 2 videos
                        if process_count[0] < 3:
                            result = base_mock(video)
                        if process_count[0] == 3:
                            raise KeyboardInterrupt("User interrupted")
                        return 0

                    with patch.object(archiver, "_process_video", side_effect=process_with_interrupt):
                        # Should raise KeyboardInterrupt but auto-commit first
                        with pytest.raises(KeyboardInterrupt):
                            archiver.backup_channel("test-channel")

            # Check commit history
            commits = _get_git_commit_messages(repo_path)

            # Should have partial backup commit
            partial_commits = [c for c in commits if "Partial backup (interrupted)" in c]
            assert len(partial_commits) == 1, f"Expected 1 partial commit, got {partial_commits}"

            # Verify commit message mentions correct video count
            assert "2 videos" in partial_commits[0], f"Expected '2 videos' in commit: {partial_commits[0]}"

    def test_keyboard_interrupt_without_auto_commit(self):
        """Test that disabling auto-commit leaves changes uncommitted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            _init_test_repo(repo_path)

            config = Config(
                sources=[SourceConfig(url="test-channel", type="channel")],
                components=ComponentsConfig(videos=False, metadata=True, captions=False),
                filters=FiltersConfig(limit=5),
                backup=BackupConfig(auto_commit_on_interrupt=False),
            )

            archiver = Archiver(repo_path, config)

            mock_videos = [
                {"id": f"video{i}", "title": f"Video {i}", "upload_date": "20260101"}
                for i in range(1, 6)
            ]

            with patch.object(archiver.youtube, "get_channel_videos", return_value=mock_videos):
                with patch.object(archiver.youtube, "metadata_to_video") as mock_to_video:
                    def create_mock_video(meta):
                        video = MagicMock()
                        video.video_id = meta["id"]
                        video.title = meta["title"]
                        video.upload_date = "2026-01-01"
                        return video
                    mock_to_video.side_effect = create_mock_video

                    process_count = [0]
                    base_mock = _create_process_video_mock(archiver)

                    def process_with_interrupt(video):
                        process_count[0] += 1
                        # Create files for first 2 videos
                        if process_count[0] < 3:
                            result = base_mock(video)
                        if process_count[0] == 3:
                            raise KeyboardInterrupt("User interrupted")
                        return 0

                    with patch.object(archiver, "_process_video", side_effect=process_with_interrupt):
                        with pytest.raises(KeyboardInterrupt):
                            archiver.backup_channel("test-channel")

            # Check commit history - should NOT have partial commit
            commits = _get_git_commit_messages(repo_path)
            partial_commits = [c for c in commits if "Partial backup" in c]
            assert len(partial_commits) == 0, f"Expected 0 partial commits, got {partial_commits}"

            # But should have uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            assert result.stdout.strip() != "", "Should have uncommitted changes"


@pytest.mark.ai_generated
def test_checkpoint_interval_zero_disables_checkpoints():
    """Test that checkpoint_interval=0 disables checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        _init_test_repo(repo_path)

        config = Config(
            sources=[SourceConfig(url="test-channel", type="channel")],
            components=ComponentsConfig(videos=False, metadata=True, captions=False),
            filters=FiltersConfig(limit=5),
            backup=BackupConfig(checkpoint_interval=0),  # Disabled
        )

        archiver = Archiver(repo_path, config)

        mock_videos = [
            {"id": f"video{i}", "title": f"Video {i}", "upload_date": "20260101"}
            for i in range(1, 6)
        ]

        with patch.object(archiver.youtube, "get_channel_videos", return_value=mock_videos):
            with patch.object(archiver.youtube, "metadata_to_video") as mock_to_video:
                def create_mock_video(meta):
                    video = MagicMock()
                    video.video_id = meta["id"]
                    video.title = meta["title"]
                    video.upload_date = "2026-01-01"
                    return video
                mock_to_video.side_effect = create_mock_video

                with patch.object(archiver, "_process_video", side_effect=_create_process_video_mock(archiver)):
                    archiver.backup_channel("test-channel")

        commits = _get_git_commit_messages(repo_path)
        checkpoint_commits = [c for c in commits if "Checkpoint:" in c]
        assert len(checkpoint_commits) == 0, "checkpoint_interval=0 should disable checkpoints"
