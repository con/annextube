"""File utilities for safe operations with git-annex repositories."""

from pathlib import Path
from typing import IO, Any


def _prepare_atomic_target(file_path: Path) -> Path:
    """Ready ``file_path`` for a fresh write in a git-annex repo.

    git-annex files are symlinks to read-only content under
    ``.git/annex/objects/``; overwriting the target directly raises
    "Permission denied".  This helper unlinks any existing file or
    symlink at ``file_path`` and ensures the parent directory exists,
    returning the normalized ``Path``.
    """
    file_path = Path(file_path)
    if file_path.exists() or file_path.is_symlink():
        file_path.unlink()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path


def atomic_write(file_path: Path, content: str, encoding: str = 'utf-8') -> None:
    """Atomically write text content to a file, handling git-annex symlinks.

    Args:
        file_path: Path to file to write
        content: Content to write
        encoding: Text encoding (default: utf-8)

    Example:
        >>> atomic_write(Path("video/metadata.json"), json.dumps(data, indent=2))
    """
    _prepare_atomic_target(file_path).write_text(content, encoding=encoding)


def atomic_write_bytes(file_path: Path, content: bytes) -> None:
    """Atomically write binary content to a file, handling git-annex symlinks.

    Args:
        file_path: Path to file to write
        content: Binary content to write

    Example:
        >>> atomic_write_bytes(Path("video/thumbnail.jpg"), image_data)
    """
    _prepare_atomic_target(file_path).write_bytes(content)


class AtomicFileWriter:
    """Context manager for atomic file writes in git-annex repositories.

    Usage:
        with AtomicFileWriter(path) as f:
            json.dump(data, f, indent=2)
    """

    def __init__(self, file_path: Path, mode: str = 'w', encoding: str | None = 'utf-8'):
        """Initialize atomic file writer.

        Args:
            file_path: Path to file to write
            mode: File mode ('w' for text, 'wb' for binary)
            encoding: Text encoding (only for text mode)
        """
        self.file_path = Path(file_path)
        self.mode = mode
        self.encoding = encoding if 'b' not in mode else None
        self.file: IO[Any] | None = None

    def __enter__(self):
        """Enter context: remove existing file and open for writing."""
        _prepare_atomic_target(self.file_path)
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
