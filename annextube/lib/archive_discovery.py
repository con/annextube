"""Archive discovery and validation utilities.

Provides centralized logic for detecting and validating annextube archives,
whether single-channel (git-annex repo) or multi-channel collections.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from annextube.services.git_annex import GitAnnexService


ArchiveType = Literal["single-channel", "multi-channel"]


@dataclass
class ArchiveInfo:
    """Information about a discovered annextube archive.

    Attributes:
        type: Archive type (single-channel or multi-channel)
        path: Path to archive root directory
        web_exists: Whether web/ directory exists
        channels_tsv: Path to channels.tsv (multi-channel only)
        is_git_annex: Whether this is a git-annex repository
    """

    type: ArchiveType
    path: Path
    web_exists: bool
    channels_tsv: Path | None = None
    is_git_annex: bool = False


def discover_annextube(path: Path) -> ArchiveInfo | None:
    """Discover and validate annextube archive at given path.

    Detection logic:
    1. If channels.tsv exists -> multi-channel collection
    2. If .git/annex exists -> single-channel archive
    3. Otherwise -> not an annextube archive

    Args:
        path: Path to potential archive directory

    Returns:
        ArchiveInfo if valid archive found, None otherwise

    Examples:
        >>> info = discover_annextube(Path("/path/to/archive"))
        >>> if info:
        ...     print(f"Found {info.type} archive")
        ... else:
        ...     print("Not an annextube archive")
    """
    if not path.exists() or not path.is_dir():
        return None

    # Check for multi-channel collection first
    channels_tsv = path / "channels.tsv"
    if channels_tsv.exists():
        return ArchiveInfo(
            type="multi-channel",
            path=path,
            web_exists=(path / "web").exists(),
            channels_tsv=channels_tsv,
            is_git_annex=False,
        )

    # Check for single-channel archive (git-annex repo)
    git_annex = GitAnnexService(path)
    if git_annex.is_annex_repo():
        return ArchiveInfo(
            type="single-channel",
            path=path,
            web_exists=(path / "web").exists(),
            channels_tsv=None,
            is_git_annex=True,
        )

    return None


def is_annextube_archive(path: Path) -> bool:
    """Check if path is any type of annextube archive.

    Args:
        path: Path to check

    Returns:
        True if path is a valid annextube archive (single or multi-channel)
    """
    return discover_annextube(path) is not None


def is_single_channel_archive(path: Path) -> bool:
    """Check if path is a single-channel annextube archive.

    Args:
        path: Path to check

    Returns:
        True if path is a single-channel git-annex archive
    """
    info = discover_annextube(path)
    return info is not None and info.type == "single-channel"


def is_multi_channel_collection(path: Path) -> bool:
    """Check if path is a multi-channel collection.

    Args:
        path: Path to check

    Returns:
        True if path is a multi-channel collection
    """
    info = discover_annextube(path)
    return info is not None and info.type == "multi-channel"


def require_annextube_archive(path: Path, allow_multi_channel: bool = False) -> ArchiveInfo:
    """Require path to be a valid annextube archive, raise if not.

    Args:
        path: Path to validate
        allow_multi_channel: If False, only single-channel archives are allowed

    Returns:
        ArchiveInfo for the discovered archive

    Raises:
        ValueError: If path is not a valid archive or wrong type
    """
    info = discover_annextube(path)

    if info is None:
        raise ValueError(
            f"{path} is not an annextube archive. Run 'annextube init' first."
        )

    if not allow_multi_channel and info.type == "multi-channel":
        raise ValueError(
            f"{path} is a multi-channel collection, not a single-channel archive. "
            "This command only works with single-channel archives."
        )

    return info
