"""Tests for annex_utils module."""

import pytest

from annextube.lib.annex_utils import (
    AnnexFileStatus,
    get_annex_file_status,
    is_content_available,
    is_file_tracked,
)


@pytest.mark.ai_generated
class TestGetAnnexFileStatus:
    """Tests for get_annex_file_status function."""

    def test_not_tracked(self, tmp_path):
        """File doesn't exist at all."""
        path = tmp_path / "video.mkv"
        assert get_annex_file_status(path) == AnnexFileStatus.NOT_TRACKED

    def test_tracked_broken_symlink(self, tmp_path):
        """Symlink exists but target doesn't (broken symlink)."""
        path = tmp_path / "video.mkv"
        path.symlink_to("/nonexistent/target/that/does/not/exist")
        assert get_annex_file_status(path) == AnnexFileStatus.TRACKED

    def test_available(self, tmp_path):
        """Symlink exists and resolves to content."""
        target = tmp_path / "content"
        target.write_bytes(b"video content")
        path = tmp_path / "video.mkv"
        path.symlink_to(target)
        assert get_annex_file_status(path) == AnnexFileStatus.AVAILABLE

    def test_regular_file(self, tmp_path):
        """Regular file (not symlink) is considered available."""
        path = tmp_path / "video.mkv"
        path.write_bytes(b"video content")
        assert get_annex_file_status(path) == AnnexFileStatus.AVAILABLE

    def test_accepts_string_path(self, tmp_path):
        """Function accepts string paths as well as Path objects."""
        path = tmp_path / "video.mkv"
        assert get_annex_file_status(str(path)) == AnnexFileStatus.NOT_TRACKED


@pytest.mark.ai_generated
class TestIsContentAvailable:
    """Tests for is_content_available function."""

    def test_not_available(self, tmp_path):
        """File doesn't exist."""
        path = tmp_path / "video.mkv"
        assert is_content_available(path) is False

    def test_broken_symlink_not_available(self, tmp_path):
        """Broken symlink is not available."""
        path = tmp_path / "video.mkv"
        path.symlink_to("/nonexistent/target")
        assert is_content_available(path) is False

    def test_available(self, tmp_path):
        """Regular file is available."""
        path = tmp_path / "video.mkv"
        path.write_bytes(b"content")
        assert is_content_available(path) is True

    def test_symlink_available(self, tmp_path):
        """Symlink to existing file is available."""
        target = tmp_path / "content"
        target.write_bytes(b"content")
        path = tmp_path / "video.mkv"
        path.symlink_to(target)
        assert is_content_available(path) is True


@pytest.mark.ai_generated
class TestIsFileTracked:
    """Tests for is_file_tracked function."""

    def test_not_tracked(self, tmp_path):
        """File doesn't exist at all."""
        path = tmp_path / "video.mkv"
        assert is_file_tracked(path) is False

    def test_tracked_broken_symlink(self, tmp_path):
        """Broken symlink is still tracked."""
        path = tmp_path / "video.mkv"
        path.symlink_to("/nonexistent/target")
        assert is_file_tracked(path) is True

    def test_tracked_valid_symlink(self, tmp_path):
        """Valid symlink is tracked."""
        target = tmp_path / "content"
        target.write_bytes(b"content")
        path = tmp_path / "video.mkv"
        path.symlink_to(target)
        assert is_file_tracked(path) is True

    def test_regular_file_tracked(self, tmp_path):
        """Regular file is tracked."""
        path = tmp_path / "video.mkv"
        path.write_bytes(b"content")
        assert is_file_tracked(path) is True
