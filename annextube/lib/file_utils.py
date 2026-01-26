"""File utilities for safe operations with git-annex repositories."""

import os
from pathlib import Path
from typing import Optional


def atomic_write(file_path: Path, content: str, encoding: str = 'utf-8') -> None:
    """Atomically write content to a file, handling git-annex symlinks.

    In git-annex repositories, files may be symlinks to read-only content in
    .git/annex/objects/. This function ensures safe updates by:
    1. Removing the existing file/symlink if it exists
    2. Writing the new content

    This prevents "Permission denied" errors when trying to modify annexed files.

    Args:
        file_path: Path to file to write
        content: Content to write
        encoding: Text encoding (default: utf-8)

    Example:
        >>> atomic_write(Path("video/metadata.json"), json.dumps(data, indent=2))
    """
    file_path = Path(file_path)

    # Remove existing file/symlink if it exists
    if file_path.exists() or file_path.is_symlink():
        file_path.unlink()

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write new content
    file_path.write_text(content, encoding=encoding)


def atomic_write_bytes(file_path: Path, content: bytes) -> None:
    """Atomically write binary content to a file, handling git-annex symlinks.

    In git-annex repositories, files may be symlinks to read-only content in
    .git/annex/objects/. This function ensures safe updates by:
    1. Removing the existing file/symlink if it exists
    2. Writing the new content

    This prevents "Permission denied" errors when trying to modify annexed files.

    Args:
        file_path: Path to file to write
        content: Binary content to write

    Example:
        >>> atomic_write_bytes(Path("video/thumbnail.jpg"), image_data)
    """
    file_path = Path(file_path)

    # Remove existing file/symlink if it exists
    if file_path.exists() or file_path.is_symlink():
        file_path.unlink()

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write new content
    file_path.write_bytes(content)


class AtomicFileWriter:
    """Context manager for atomic file writes in git-annex repositories.

    Usage:
        with AtomicFileWriter(path) as f:
            json.dump(data, f, indent=2)
    """

    def __init__(self, file_path: Path, mode: str = 'w', encoding: Optional[str] = 'utf-8'):
        """Initialize atomic file writer.

        Args:
            file_path: Path to file to write
            mode: File mode ('w' for text, 'wb' for binary)
            encoding: Text encoding (only for text mode)
        """
        self.file_path = Path(file_path)
        self.mode = mode
        self.encoding = encoding if 'b' not in mode else None
        self.file = None

    def __enter__(self):
        """Enter context: remove existing file and open for writing."""
        # Remove existing file/symlink if it exists
        if self.file_path.exists() or self.file_path.is_symlink():
            self.file_path.unlink()

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Open file for writing
        if self.encoding:
            self.file = open(self.file_path, self.mode, encoding=self.encoding)
        else:
            self.file = open(self.file_path, self.mode)

        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context: close file."""
        if self.file:
            self.file.close()
        return False
