"""Unit tests for archive discovery utilities."""

from pathlib import Path

import pytest

from annextube.lib.archive_discovery import (
    ArchiveInfo,
    discover_annextube,
    is_annextube_archive,
    is_multi_channel_collection,
    is_single_channel_archive,
    require_annextube_archive,
)


@pytest.fixture
def single_channel_archive(tmp_path):
    """Create a minimal single-channel archive structure."""
    temp_path = tmp_path / "single_channel"
    temp_path.mkdir()
    # Create .git/annex directory structure
    git_dir = temp_path / ".git"
    git_dir.mkdir()
    annex_dir = git_dir / "annex"
    annex_dir.mkdir()
    return temp_path


@pytest.fixture
def multi_channel_collection(tmp_path):
    """Create a minimal multi-channel collection structure."""
    temp_path = tmp_path / "multi_channel"
    temp_path.mkdir()
    # Create channels.tsv
    channels_tsv = temp_path / "channels.tsv"
    channels_tsv.write_text("channel_id\ttitle\n")
    return temp_path


class TestDiscoverAnnextube:
    """Tests for discover_annextube function."""

    def test_discover_single_channel_archive(self, single_channel_archive):
        """Test discovering a single-channel archive."""
        info = discover_annextube(single_channel_archive)

        assert info is not None
        assert info.type == "single-channel"
        assert info.path == single_channel_archive
        assert info.is_git_annex is True
        assert info.channels_tsv is None
        assert info.web_exists is False

    def test_discover_single_channel_with_web(self, single_channel_archive):
        """Test discovering single-channel archive with web UI."""
        # Add web directory
        web_dir = single_channel_archive / "web"
        web_dir.mkdir()

        info = discover_annextube(single_channel_archive)

        assert info is not None
        assert info.type == "single-channel"
        assert info.web_exists is True

    def test_discover_multi_channel_collection(self, multi_channel_collection):
        """Test discovering a multi-channel collection."""
        info = discover_annextube(multi_channel_collection)

        assert info is not None
        assert info.type == "multi-channel"
        assert info.path == multi_channel_collection
        assert info.is_git_annex is False
        assert info.channels_tsv == multi_channel_collection / "channels.tsv"
        assert info.web_exists is False

    def test_discover_multi_channel_with_web(self, multi_channel_collection):
        """Test discovering multi-channel collection with web UI."""
        # Add web directory
        web_dir = multi_channel_collection / "web"
        web_dir.mkdir()

        info = discover_annextube(multi_channel_collection)

        assert info is not None
        assert info.type == "multi-channel"
        assert info.web_exists is True

    def test_discover_not_archive(self, tmp_path):
        """Test discovering non-archive directory."""
        # Empty directory
        info = discover_annextube(tmp_path)
        assert info is None

    def test_discover_nonexistent_path(self, tmp_path):
        """Test discovering nonexistent path."""
        nonexistent = tmp_path / "does-not-exist"
        info = discover_annextube(nonexistent)
        assert info is None

    def test_discover_file_not_directory(self, tmp_path):
        """Test discovering a file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        info = discover_annextube(file_path)
        assert info is None

    def test_multi_channel_takes_precedence(self, tmp_path):
        """Test that multi-channel detection takes precedence over git-annex.

        If both channels.tsv and .git/annex exist (unlikely but possible),
        should be detected as multi-channel.
        """
        # Create both structures
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "annex").mkdir()

        channels_tsv = tmp_path / "channels.tsv"
        channels_tsv.write_text("channel_id\ttitle\n")

        info = discover_annextube(tmp_path)

        assert info is not None
        assert info.type == "multi-channel"


class TestIsAnnextubeArchive:
    """Tests for is_annextube_archive helper."""

    def test_single_channel_is_archive(self, single_channel_archive):
        """Test single-channel archive is detected."""
        assert is_annextube_archive(single_channel_archive) is True

    def test_multi_channel_is_archive(self, multi_channel_collection):
        """Test multi-channel collection is detected."""
        assert is_annextube_archive(multi_channel_collection) is True

    def test_empty_dir_not_archive(self, tmp_path):
        """Test empty directory is not an archive."""
        assert is_annextube_archive(tmp_path) is False


class TestIsSingleChannelArchive:
    """Tests for is_single_channel_archive helper."""

    def test_single_channel_detected(self, single_channel_archive):
        """Test single-channel archive is detected."""
        assert is_single_channel_archive(single_channel_archive) is True

    def test_multi_channel_not_single(self, multi_channel_collection):
        """Test multi-channel collection is not single-channel."""
        assert is_single_channel_archive(multi_channel_collection) is False

    def test_empty_dir_not_single(self, tmp_path):
        """Test empty directory is not single-channel."""
        assert is_single_channel_archive(tmp_path) is False


class TestIsMultiChannelCollection:
    """Tests for is_multi_channel_collection helper."""

    def test_multi_channel_detected(self, multi_channel_collection):
        """Test multi-channel collection is detected."""
        assert is_multi_channel_collection(multi_channel_collection) is True

    def test_single_channel_not_multi(self, single_channel_archive):
        """Test single-channel archive is not multi-channel."""
        assert is_multi_channel_collection(single_channel_archive) is False

    def test_empty_dir_not_multi(self, tmp_path):
        """Test empty directory is not multi-channel."""
        assert is_multi_channel_collection(tmp_path) is False


class TestRequireAnnextubeArchive:
    """Tests for require_annextube_archive helper."""

    def test_require_single_channel_success(self, single_channel_archive):
        """Test requiring single-channel archive succeeds."""
        info = require_annextube_archive(single_channel_archive, allow_multi_channel=False)

        assert info.type == "single-channel"
        assert info.path == single_channel_archive

    def test_require_multi_channel_success(self, multi_channel_collection):
        """Test requiring archive allows multi-channel when enabled."""
        info = require_annextube_archive(multi_channel_collection, allow_multi_channel=True)

        assert info.type == "multi-channel"
        assert info.path == multi_channel_collection

    def test_require_multi_channel_fails_when_not_allowed(self, multi_channel_collection):
        """Test requiring single-channel fails for multi-channel."""
        with pytest.raises(ValueError, match="multi-channel collection.*single-channel archive"):
            require_annextube_archive(multi_channel_collection, allow_multi_channel=False)

    def test_require_fails_for_non_archive(self, tmp_path):
        """Test requiring archive fails for non-archive directory."""
        with pytest.raises(ValueError, match="not an annextube archive"):
            require_annextube_archive(tmp_path)

    def test_require_both_types_allowed_by_default(self, single_channel_archive, multi_channel_collection):
        """Test that allow_multi_channel defaults to False."""
        # Single-channel should work
        info = require_annextube_archive(single_channel_archive)
        assert info.type == "single-channel"

        # Multi-channel should fail by default
        with pytest.raises(ValueError, match="multi-channel collection"):
            require_annextube_archive(multi_channel_collection)


class TestArchiveInfo:
    """Tests for ArchiveInfo dataclass."""

    def test_archive_info_single_channel(self):
        """Test ArchiveInfo for single-channel archive."""
        path = Path("/test/archive")
        info = ArchiveInfo(
            type="single-channel",
            path=path,
            web_exists=True,
            is_git_annex=True,
        )

        assert info.type == "single-channel"
        assert info.path == path
        assert info.web_exists is True
        assert info.is_git_annex is True
        assert info.channels_tsv is None

    def test_archive_info_multi_channel(self):
        """Test ArchiveInfo for multi-channel collection."""
        path = Path("/test/collection")
        channels_tsv = path / "channels.tsv"
        info = ArchiveInfo(
            type="multi-channel",
            path=path,
            web_exists=False,
            channels_tsv=channels_tsv,
        )

        assert info.type == "multi-channel"
        assert info.path == path
        assert info.web_exists is False
        assert info.is_git_annex is False
        assert info.channels_tsv == channels_tsv
