"""Service for unannexing files to make them directly available in git."""

import json
import logging
import re
import subprocess
from pathlib import Path

from tqdm import tqdm

logger = logging.getLogger(__name__)

# GitHub limits
GITHUB_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
GITHUB_MAX_REPO_SIZE = 100 * 1024 * 1024 * 1024  # 100 GB (soft limit)
GITHUB_RECOMMENDED_REPO_SIZE = 1 * 1024 * 1024 * 1024  # 1 GB


def parse_size(size_str: str) -> int:
    """
    Parse size string to bytes.

    Args:
        size_str: Size string like "10M", "100K", "1G"

    Returns:
        Size in bytes

    Raises:
        ValueError: If size_str format is invalid

    Examples:
        >>> parse_size("10M")
        10485760
        >>> parse_size("100K")
        102400
        >>> parse_size("1G")
        1073741824
    """
    size_str = size_str.strip().upper()

    # Match number and optional unit
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?)B?$', size_str)
    if not match:
        raise ValueError(
            f"Invalid size format: {size_str}. "
            f"Expected format: <number>[K|M|G|T] (e.g., '10M', '100K', '1G')"
        )

    number = float(match.group(1))
    unit = match.group(2)

    multipliers = {
        '': 1,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }

    return int(number * multipliers[unit])


def find_annexed_files(
    repo_path: Path,
    patterns: list[str],
    max_size: int | None = None
) -> list[tuple[Path, int]]:
    """
    Find annexed files matching criteria.

    Args:
        repo_path: Path to git-annex repository
        patterns: List of glob patterns
        max_size: Maximum file size in bytes (None = no limit)

    Returns:
        List of (file_path, size_bytes) tuples

    Raises:
        RuntimeError: If git-annex commands fail
    """

    # Find all annexed files
    logger.debug("Finding all annexed files...")
    try:
        result = subprocess.run(
            ['git', 'annex', 'find', '--include', '*'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        annexed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to find annexed files: {e}")

    if not annexed_files:
        logger.debug("No annexed files found")
        return []

    logger.debug(f"Found {len(annexed_files)} annexed files total")

    # Filter by patterns
    matching_files = []
    for file_path_str in annexed_files:
        file_path = Path(file_path_str)

        # Check if file matches any pattern
        if not any(file_path.match(pattern) for pattern in patterns):
            continue

        # Get file size
        try:
            size = get_annexed_file_size(repo_path, file_path)
        except Exception as e:
            logger.warning(f"Failed to get size for {file_path}: {e}")
            continue

        # Check size limit
        if max_size is not None and size > max_size:
            logger.debug(f"Skipping {file_path} (size {size} > {max_size})")
            continue

        matching_files.append((file_path, size))

    logger.debug(f"Found {len(matching_files)} files matching criteria")
    return matching_files


def get_annexed_file_size(repo_path: Path, file_path: Path) -> int:
    """
    Get size of annexed file without downloading it.

    Args:
        repo_path: Path to git-annex repository
        file_path: Relative path to file

    Returns:
        File size in bytes

    Raises:
        RuntimeError: If git-annex info command fails
        ValueError: If size information not available
    """
    try:
        result = subprocess.run(
            ['git', 'annex', 'info', '--json', '--bytes', str(file_path)],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get file info: {e}")

    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse git-annex info output: {e}")

    # Size is in 'size' field (in bytes with --bytes flag)
    if 'size' not in info or info['size'] is None:
        raise ValueError(f"Size information not available for {file_path}")

    return int(info['size'])


def validate_github_limits(
    files: list[tuple[Path, int]],
    repo_path: Path,
    force: bool = False
) -> dict:
    """
    Check if unannexing would violate GitHub limits.

    Args:
        files: List of (file_path, size) tuples
        repo_path: Path to repository
        force: Whether to allow proceeding despite errors

    Returns:
        {
            'ok': bool,
            'warnings': list[str],
            'errors': list[str],
            'total_size': int,
            'large_files': list[tuple[Path, int]]
        }
    """
    result = {
        'ok': True,
        'warnings': [],
        'errors': [],
        'total_size': 0,
        'large_files': []
    }

    # Check individual file sizes
    for file_path, size in files:
        result['total_size'] += size

        if size > GITHUB_MAX_FILE_SIZE:
            result['large_files'].append((file_path, size))
            msg = f"{file_path}: {format_size(size)} exceeds GitHub limit (100 MB)"
            result['errors'].append(msg)
            result['ok'] = False

    # Check total repository size
    current_repo_size = get_repo_size(repo_path)
    projected_size = current_repo_size + result['total_size']

    if projected_size > GITHUB_RECOMMENDED_REPO_SIZE:
        msg = (
            f"Repository size will be {format_size(projected_size)} "
            f"(GitHub recommends <1 GB)"
        )
        result['warnings'].append(msg)

    if projected_size > GITHUB_MAX_REPO_SIZE:
        msg = (
            f"Repository size will be {format_size(projected_size)} "
            f"(GitHub soft limit: 100 GB)"
        )
        result['warnings'].append(msg)

    if not force and not result['ok']:
        result['errors'].append("Use --force to proceed despite size violations")

    return result


def get_repo_size(repo_path: Path) -> int:
    """
    Get current repository size (git objects).

    Args:
        repo_path: Path to repository

    Returns:
        Size in bytes
    """
    git_dir = repo_path / '.git'
    if not git_dir.exists():
        return 0

    total_size = 0
    for item in git_dir.rglob('*'):
        if item.is_file():
            try:
                total_size += item.stat().st_size
            except (OSError, PermissionError):
                # Skip files we can't read
                continue

    return total_size


def unannex_files(
    repo_path: Path,
    files: list[Path],
    update_gitattributes: bool = True,
    dry_run: bool = False
) -> dict:
    """
    Unannex files and optionally update .gitattributes.

    Args:
        repo_path: Path to git-annex repository
        files: List of file paths to unannex
        update_gitattributes: Whether to update .gitattributes
        dry_run: If True, don't make changes

    Returns:
        {
            'unannexed': list[Path],
            'failed': list[tuple[Path, str]],
            'total_size': int
        }

    Raises:
        RuntimeError: If git operations fail
    """
    result = {
        'unannexed': [],
        'failed': [],
        'total_size': 0
    }

    # Progress bar
    with tqdm(total=len(files), desc="Unannexing files", unit="file", disable=dry_run) as pbar:
        for file_path in files:
            try:
                # Get size before unannexing
                size = get_annexed_file_size(repo_path, file_path)

                if not dry_run:
                    # Unannex file
                    subprocess.run(
                        ['git', 'annex', 'unannex', str(file_path)],
                        cwd=repo_path,
                        check=True
                    )

                    # Add to git
                    subprocess.run(
                        ['git', 'add', str(file_path)],
                        cwd=repo_path,
                        check=True
                    )

                result['unannexed'].append(file_path)
                result['total_size'] += size

                pbar.set_postfix_str(format_size(size))
                pbar.update(1)

            except Exception as e:
                logger.error(f"Failed to unannex {file_path}: {e}")
                result['failed'].append((file_path, str(e)))
                pbar.update(1)

    # Update .gitattributes
    if update_gitattributes and not dry_run and result['unannexed']:
        try:
            update_gitattributes_for_unannexed(repo_path, result['unannexed'])
        except Exception as e:
            logger.error(f"Failed to update .gitattributes: {e}")
            # Don't fail the whole operation for this

    return result


def update_gitattributes_for_unannexed(
    repo_path: Path,
    unannexed_files: list[Path]
) -> None:
    """
    Update .gitattributes to prevent re-annexing.

    Adds patterns like:
        videos/*/thumbnail.jpg annex.largefiles=nothing

    Args:
        repo_path: Path to repository
        unannexed_files: List of unannexed file paths
    """
    gitattributes_path = repo_path / '.gitattributes'

    # Extract unique patterns from file list
    patterns = extract_patterns(unannexed_files)
    logger.debug(f"Extracted {len(patterns)} patterns from {len(unannexed_files)} files")

    # Read existing .gitattributes
    if gitattributes_path.exists():
        content = gitattributes_path.read_text()
    else:
        content = ""

    # Append new patterns
    new_lines = []
    for pattern in patterns:
        rule = f"{pattern} annex.largefiles=nothing"
        if rule not in content:
            new_lines.append(rule)
            logger.debug(f"Adding pattern: {pattern}")

    if new_lines:
        if content and not content.endswith('\n'):
            content += '\n'
        content += '\n'.join(new_lines) + '\n'
        gitattributes_path.write_text(content)

        # Add .gitattributes to git
        subprocess.run(['git', 'add', '.gitattributes'], cwd=repo_path, check=True)

        logger.info(f"Updated .gitattributes with {len(new_lines)} new patterns")


def extract_patterns(files: list[Path]) -> set[str]:
    """
    Extract minimal set of patterns covering unannexed files.

    Strategy: Group files by directory structure and extension,
    then use wildcards where applicable.

    Args:
        files: List of file paths

    Returns:
        Set of glob patterns

    Examples:
        >>> extract_patterns([Path('videos/v1/thumb.jpg'), Path('videos/v2/thumb.jpg')])
        {'videos/*/thumb.jpg'}

        >>> extract_patterns([Path('videos/v1/video.mkv')])
        {'videos/v1/video.mkv'}
    """
    patterns = set()

    # Group files by filename and depth
    by_filename = {}
    for file_path in files:
        filename = file_path.name
        depth = len(file_path.parts)
        key = (filename, depth)

        if key not in by_filename:
            by_filename[key] = []
        by_filename[key].append(file_path)

    # Generate patterns
    for (filename, depth), paths in by_filename.items():
        if len(paths) > 1 and depth >= 2:
            # Multiple files with same name at same depth - use wildcard
            # e.g., videos/*/thumbnail.jpg
            sample = paths[0]
            pattern_parts = list(sample.parts[:-1])
            # Replace the variable part(s) with *
            # For depth 3: videos/2026-02-05_Video/thumbnail.jpg -> videos/*/thumbnail.jpg
            if len(pattern_parts) >= 1:
                pattern_parts[-1] = '*'
            pattern = str(Path(*pattern_parts) / filename)
            patterns.add(pattern)
        else:
            # Single file or shallow - use exact paths
            for path in paths:
                patterns.add(str(path))

    return patterns


def format_size(size_bytes: int) -> str:
    """
    Format size in human-readable form.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string

    Examples:
        >>> format_size(1024)
        '1.0 KB'
        >>> format_size(10485760)
        '10.0 MB'
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
