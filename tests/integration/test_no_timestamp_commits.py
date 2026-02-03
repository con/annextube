"""Integration test: Verify no commits are created for timestamp-only changes."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from annextube.services.git_annex import GitAnnexService


@pytest.fixture
def git_annex_repo():
    """Create a temporary git-annex repository for integration testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)

        # Initialize git-annex
        subprocess.run(["git", "annex", "init", "test-repo"], cwd=repo_path, check=True, capture_output=True)

        # Configure .gitattributes to keep JSON files in git (not annex)
        gitattributes = repo_path / ".gitattributes"
        gitattributes.write_text("*.json annex.largefiles=nothing\n")
        subprocess.run(["git", "add", ".gitattributes"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Add .gitattributes"], cwd=repo_path, check=True, capture_output=True)

        yield repo_path


@pytest.mark.ai_generated
def test_no_commit_for_timestamp_only_changes(git_annex_repo: Path) -> None:
    """Integration test: add_and_commit should not create commits for timestamp-only changes."""
    service = GitAnnexService(git_annex_repo)

    # Create initial video metadata
    video_dir = git_annex_repo / "videos" / "vid1"
    video_dir.mkdir(parents=True)
    metadata_file = video_dir / "metadata.json"

    initial_data = {
        "video_id": "test123",
        "title": "Test Video",
        "description": "Test description",
        "fetched_at": "2026-01-01T00:00:00"
    }
    metadata_file.write_text(json.dumps(initial_data, indent=2))

    # First commit (should succeed - initial data)
    result = service.add_and_commit("Initial video metadata")
    assert result is True, "First commit should succeed"

    # Get commit count
    commit_count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=git_annex_repo,
        capture_output=True,
        text=True,
        check=True
    )
    initial_commit_count = int(commit_count.stdout.strip())

    # Modify only timestamp
    updated_data = {
        "video_id": "test123",
        "title": "Test Video",
        "description": "Test description",
        "fetched_at": "2026-01-26T10:00:00"
    }
    metadata_file.write_text(json.dumps(updated_data, indent=2))

    # Try to commit timestamp-only change (should be skipped)
    result = service.add_and_commit("Timestamp update only")
    assert result is False, "Should return False for timestamp-only changes"

    # Verify no new commit was created
    commit_count_after = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=git_annex_repo,
        capture_output=True,
        text=True,
        check=True
    )
    final_commit_count = int(commit_count_after.stdout.strip())

    assert final_commit_count == initial_commit_count, "No new commit should be created for timestamp-only changes"

    # Verify working directory is clean (timestamp changes were restored)
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=git_annex_repo,
        capture_output=True,
        text=True,
        check=True
    )
    assert status_result.stdout.strip() == "", "Working directory should be clean after timestamp-only change"


@pytest.mark.ai_generated
def test_commit_created_for_real_changes(git_annex_repo: Path) -> None:
    """Integration test: add_and_commit should create commits for real content changes."""
    service = GitAnnexService(git_annex_repo)

    # Create initial video metadata
    video_dir = git_annex_repo / "videos" / "vid1"
    video_dir.mkdir(parents=True)
    metadata_file = video_dir / "metadata.json"

    initial_data = {
        "video_id": "test123",
        "title": "Test Video",
        "description": "Test description",
        "fetched_at": "2026-01-01T00:00:00"
    }
    metadata_file.write_text(json.dumps(initial_data, indent=2))

    # First commit
    service.add_and_commit("Initial video metadata")

    # Get commit count
    commit_count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=git_annex_repo,
        capture_output=True,
        text=True,
        check=True
    )
    initial_commit_count = int(commit_count.stdout.strip())

    # Modify title AND timestamp (real change)
    updated_data = {
        "video_id": "test123",
        "title": "Updated Video Title",
        "description": "Test description",
        "fetched_at": "2026-01-26T10:00:00"
    }
    metadata_file.write_text(json.dumps(updated_data, indent=2))

    # Commit real change (should succeed)
    result = service.add_and_commit("Update video title")
    assert result is True, "Should return True for real content changes"

    # Verify new commit was created
    commit_count_after = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=git_annex_repo,
        capture_output=True,
        text=True,
        check=True
    )
    final_commit_count = int(commit_count_after.stdout.strip())

    assert final_commit_count == initial_commit_count + 1, "New commit should be created for real changes"


@pytest.mark.ai_generated
def test_mixed_changes_commit_only_real_files(git_annex_repo: Path) -> None:
    """Integration test: Only files with real changes should be committed."""
    service = GitAnnexService(git_annex_repo)

    # Create two video metadata files
    video1_dir = git_annex_repo / "videos" / "vid1"
    video2_dir = git_annex_repo / "videos" / "vid2"
    video1_dir.mkdir(parents=True)
    video2_dir.mkdir(parents=True)

    metadata1 = video1_dir / "metadata.json"
    metadata2 = video2_dir / "metadata.json"

    data1 = {"video_id": "vid1", "title": "Video 1", "fetched_at": "2026-01-01T00:00:00"}
    data2 = {"video_id": "vid2", "title": "Video 2", "fetched_at": "2026-01-01T00:00:00"}

    metadata1.write_text(json.dumps(data1, indent=2))
    metadata2.write_text(json.dumps(data2, indent=2))

    # First commit
    service.add_and_commit("Initial videos")

    # Video 1: timestamp-only change
    updated_data1 = {"video_id": "vid1", "title": "Video 1", "fetched_at": "2026-01-26T10:00:00"}
    metadata1.write_text(json.dumps(updated_data1, indent=2))

    # Video 2: real change (title + timestamp)
    updated_data2 = {"video_id": "vid2", "title": "Updated Title", "fetched_at": "2026-01-26T10:00:00"}
    metadata2.write_text(json.dumps(updated_data2, indent=2))

    # Commit (should only include video 2)
    result = service.add_and_commit("Update video 2 title")
    assert result is True, "Should return True when at least one file has real changes"

    # Verify only video 2 is in the last commit
    diff_result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--name-only"],
        cwd=git_annex_repo,
        capture_output=True,
        text=True,
        check=True
    )

    changed_files = diff_result.stdout.strip().split('\n')
    assert "videos/vid1/metadata.json" not in changed_files, "Timestamp-only file should not be committed"
    assert "videos/vid2/metadata.json" in changed_files, "Real change should be committed"
