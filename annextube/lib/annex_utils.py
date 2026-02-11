"""Utilities for git-annex file operations.

Provides functions to check the status of git-annex managed files
using the difference between os.path.lexists() and os.path.exists().
"""

import os
from enum import Enum
from pathlib import Path


class AnnexFileStatus(Enum):
    """Status of a git-annex managed file."""

    NOT_TRACKED = "not_tracked"  # No symlink exists
    TRACKED = "tracked"  # Symlink exists, content not available
    AVAILABLE = "available"  # Symlink exists and resolves to content


def get_annex_file_status(path: Path | str) -> AnnexFileStatus:
    """Check the status of a git-annex managed file.

    Uses the difference between lexists() and exists() to determine
    if content is available locally:
    - lexists: True if symlink exists (regardless of target)
    - exists: True if symlink target exists (content available)

    Args:
        path: Path to the file (typically video.mkv)

    Returns:
        AnnexFileStatus indicating tracking and availability state
    """
    # Check if symlink exists (file is tracked)
    if not os.path.lexists(path):
        return AnnexFileStatus.NOT_TRACKED

    # Check if symlink target exists (content is available)
    if os.path.exists(path):
        return AnnexFileStatus.AVAILABLE

    # Symlink exists but target doesn't (tracked but not downloaded)
    return AnnexFileStatus.TRACKED


def is_content_available(path: Path | str) -> bool:
    """Check if git-annex content is available locally.

    Simple convenience function for the common case.

    Args:
        path: Path to the file

    Returns:
        True if file exists and content is available
    """
    return os.path.exists(path)


def is_file_tracked(path: Path | str) -> bool:
    """Check if file is tracked in git-annex.

    Args:
        path: Path to the file

    Returns:
        True if symlink exists (regardless of content availability)
    """
    return os.path.lexists(path)
