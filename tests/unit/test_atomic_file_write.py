"""Unit tests for atomic file write utilities."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from annextube.lib.file_utils import AtomicFileWriter, atomic_write, atomic_write_bytes


@pytest.mark.ai_generated
def test_atomic_write_new_file() -> None:
    """Test atomic_write creates a new file successfully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "test.txt"

        content = "Hello, World!"
        atomic_write(file_path, content)

        assert file_path.exists()
        assert file_path.read_text() == content


@pytest.mark.ai_generated
def test_atomic_write_overwrites_existing_file() -> None:
    """Test atomic_write overwrites an existing regular file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "test.txt"

        # Create initial file
        file_path.write_text("Original content")
        assert file_path.read_text() == "Original content"

        # Overwrite with atomic_write
        new_content = "New content"
        atomic_write(file_path, new_content)

        assert file_path.read_text() == new_content


@pytest.mark.ai_generated
def test_atomic_write_handles_symlink() -> None:
    """Test atomic_write removes and replaces a symlink (simulates git-annex)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create a target file (simulates git-annex object)
        target_file = tmpdir / ".git" / "annex" / "objects" / "XX" / "YY" / "test-content"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text("Annexed content")
        # Make it read-only (simulates git-annex behavior)
        os.chmod(target_file, 0o444)

        # Create a symlink to it (simulates annexed file in working tree)
        symlink_path = tmpdir / "test.txt"
        symlink_path.symlink_to(target_file)

        # Verify symlink exists and points to read-only content
        assert symlink_path.is_symlink()
        assert symlink_path.read_text() == "Annexed content"

        # Attempt to write directly would fail due to read-only target
        # But atomic_write should succeed by removing symlink first
        new_content = "Updated content"
        atomic_write(symlink_path, new_content)

        # Verify symlink was replaced with regular file
        assert not symlink_path.is_symlink()
        assert symlink_path.is_file()
        assert symlink_path.read_text() == new_content

        # Original target should be unchanged
        assert target_file.read_text() == "Annexed content"


@pytest.mark.ai_generated
def test_atomic_write_bytes_new_file() -> None:
    """Test atomic_write_bytes creates a new binary file successfully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "test.bin"

        content = b"\x00\x01\x02\x03"
        atomic_write_bytes(file_path, content)

        assert file_path.exists()
        assert file_path.read_bytes() == content


@pytest.mark.ai_generated
def test_atomic_write_bytes_handles_symlink() -> None:
    """Test atomic_write_bytes removes and replaces a symlink."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create a target file (simulates git-annex object)
        target_file = tmpdir / ".git" / "annex" / "objects" / "XX" / "YY" / "test.jpg"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_bytes(b"\xff\xd8\xff\xe0")  # JPEG header
        os.chmod(target_file, 0o444)

        # Create symlink
        symlink_path = tmpdir / "test.jpg"
        symlink_path.symlink_to(target_file)

        # Update with atomic_write_bytes
        new_content = b"\x89\x50\x4e\x47"  # PNG header
        atomic_write_bytes(symlink_path, new_content)

        assert not symlink_path.is_symlink()
        assert symlink_path.read_bytes() == new_content


@pytest.mark.ai_generated
def test_atomic_file_writer_context_manager() -> None:
    """Test AtomicFileWriter context manager for text files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "data.json"

        data = {"key": "value", "number": 42}

        with AtomicFileWriter(file_path) as f:
            json.dump(data, f, indent=2)

        assert file_path.exists()
        loaded_data = json.loads(file_path.read_text())
        assert loaded_data == data


@pytest.mark.ai_generated
def test_atomic_file_writer_replaces_symlink() -> None:
    """Test AtomicFileWriter removes symlink before writing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create target file (simulates git-annex object)
        target_file = tmpdir / ".git" / "annex" / "objects" / "data.json"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text('{"old": true}')
        os.chmod(target_file, 0o444)

        # Create symlink
        symlink_path = tmpdir / "data.json"
        symlink_path.symlink_to(target_file)

        # Write new data with AtomicFileWriter
        new_data = {"new": True, "updated": True}
        with AtomicFileWriter(symlink_path) as f:
            json.dump(new_data, f, indent=2)

        # Verify symlink was replaced
        assert not symlink_path.is_symlink()
        loaded_data = json.loads(symlink_path.read_text())
        assert loaded_data == new_data


@pytest.mark.ai_generated
def test_atomic_file_writer_binary_mode() -> None:
    """Test AtomicFileWriter with binary mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "binary.dat"

        data = b"\x00\x01\x02\x03\x04\x05"

        with AtomicFileWriter(file_path, mode='wb') as f:
            f.write(data)

        assert file_path.read_bytes() == data


@pytest.mark.ai_generated
def test_atomic_file_writer_creates_parent_dirs() -> None:
    """Test AtomicFileWriter creates parent directories if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "a" / "b" / "c" / "file.txt"

        content = "Deep nested file"
        with AtomicFileWriter(file_path) as f:
            f.write(content)

        assert file_path.exists()
        assert file_path.read_text() == content


@pytest.mark.ai_generated
def test_atomic_write_creates_parent_dirs() -> None:
    """Test atomic_write creates parent directories if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        file_path = tmpdir / "x" / "y" / "z" / "file.txt"

        content = "Nested file"
        atomic_write(file_path, content)

        assert file_path.exists()
        assert file_path.read_text() == content
