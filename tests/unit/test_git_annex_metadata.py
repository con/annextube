"""Unit tests for git-annex metadata operations."""

import subprocess
from pathlib import Path

import pytest

from annextube.services.git_annex import GitAnnexService


@pytest.mark.ai_generated
def test_set_metadata_if_changed_skips_non_annexed_file(tmp_path: Path) -> None:
    """Test set_metadata_if_changed skips files not in git-annex."""
    # Initialize git-annex repo
    git_annex = GitAnnexService(tmp_path)
    git_annex.init_repo()

    # Create a regular file (not annexed)
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    # Try to set metadata
    metadata = {"key": "value"}
    result = git_annex.set_metadata_if_changed(test_file, metadata)

    # Should return False (file not in annex)
    assert result is False


@pytest.mark.ai_generated
def test_set_metadata_if_changed_updates_annexed_file(tmp_path: Path) -> None:
    """Test set_metadata_if_changed sets metadata for annexed files."""
    # Initialize git-annex repo
    git_annex = GitAnnexService(tmp_path)
    git_annex.init_repo()

    # Create a file and annex it
    test_file = tmp_path / "test.bin"
    test_file.write_bytes(b"\x00" * 1024)  # 1KB binary file

    # Add to annex
    subprocess.run(["git", "annex", "add", str(test_file)], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add test file"], cwd=tmp_path, check=True)

    # Verify it's annexed (should be a symlink)
    assert test_file.is_symlink()
    assert git_annex.is_annexed(test_file)

    # Set metadata
    metadata = {"video_id": "test123", "title": "Test Video"}
    result = git_annex.set_metadata_if_changed(test_file, metadata)

    # Should return True (metadata updated)
    assert result is True

    # Verify metadata was set
    stored_metadata = git_annex.get_metadata(test_file)
    assert "video_id" in stored_metadata
    assert "test123" in stored_metadata["video_id"]
    assert "title" in stored_metadata
    assert "Test Video" in stored_metadata["title"]


@pytest.mark.ai_generated
def test_set_metadata_if_changed_skips_unchanged_metadata(tmp_path: Path) -> None:
    """Test set_metadata_if_changed doesn't update if metadata unchanged."""
    # Initialize git-annex repo
    git_annex = GitAnnexService(tmp_path)
    git_annex.init_repo()

    # Create and annex a file
    test_file = tmp_path / "test.bin"
    test_file.write_bytes(b"\x00" * 1024)
    subprocess.run(["git", "annex", "add", str(test_file)], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add test file"], cwd=tmp_path, check=True)

    # Set initial metadata
    metadata = {"video_id": "test123"}
    result = git_annex.set_metadata_if_changed(test_file, metadata)
    assert result is True

    # Try to set same metadata again
    result = git_annex.set_metadata_if_changed(test_file, metadata)

    # Should return False (no changes needed)
    assert result is False


@pytest.mark.ai_generated
def test_set_metadata_if_changed_updates_only_changed_fields(tmp_path: Path) -> None:
    """Test set_metadata_if_changed only updates fields that changed."""
    # Initialize git-annex repo
    git_annex = GitAnnexService(tmp_path)
    git_annex.init_repo()

    # Create and annex a file
    test_file = tmp_path / "test.bin"
    test_file.write_bytes(b"\x00" * 1024)
    subprocess.run(["git", "annex", "add", str(test_file)], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add test file"], cwd=tmp_path, check=True)

    # Set initial metadata
    initial = {"video_id": "test123", "title": "Original Title"}
    git_annex.set_metadata_if_changed(test_file, initial)

    # Update only one field
    update = {"video_id": "test123", "title": "New Title", "channel": "TestChannel"}
    result = git_annex.set_metadata_if_changed(test_file, update)

    # Should return True (title and channel changed)
    assert result is True

    # Verify all fields are present
    stored = git_annex.get_metadata(test_file)
    assert "test123" in stored["video_id"]
    assert "New Title" in stored["title"]
    assert "TestChannel" in stored["channel"]


@pytest.mark.ai_generated
def test_is_annexed_detects_symlink_to_annex(tmp_path: Path) -> None:
    """Test is_annexed correctly identifies annexed files."""
    # Initialize git-annex repo
    git_annex = GitAnnexService(tmp_path)
    git_annex.init_repo()

    # Create a regular file
    regular_file = tmp_path / "regular.txt"
    regular_file.write_text("Regular file")

    # Create and annex a binary file
    annexed_file = tmp_path / "annexed.bin"
    annexed_file.write_bytes(b"\x00" * 1024)
    subprocess.run(["git", "annex", "add", str(annexed_file)], cwd=tmp_path, check=True)

    # Test detection
    assert not git_annex.is_annexed(regular_file)
    assert git_annex.is_annexed(annexed_file)


@pytest.mark.ai_generated
def test_get_metadata_returns_empty_for_non_annexed(tmp_path: Path) -> None:
    """Test get_metadata returns empty dict for non-annexed files."""
    # Initialize git-annex repo
    git_annex = GitAnnexService(tmp_path)
    git_annex.init_repo()

    # Create a regular file
    regular_file = tmp_path / "regular.txt"
    regular_file.write_text("Regular file")

    # Get metadata
    metadata = git_annex.get_metadata(regular_file)

    # Should return empty dict
    assert metadata == {}
