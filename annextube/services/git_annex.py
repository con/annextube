"""Git-annex service using datasalad for command execution."""

import subprocess
from pathlib import Path
from typing import Optional

from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)


class GitAnnexService:
    """Wrapper around git-annex operations using datasalad patterns."""

    def __init__(self, repo_path: Path):
        """Initialize GitAnnexService.

        Args:
            repo_path: Path to git-annex repository
        """
        self.repo_path = repo_path

    def init_repo(self, description: str = "annextube archive") -> None:
        """Initialize git and git-annex repository.

        Args:
            description: Repository description
        """
        logger.info(f"Initializing git repository at {self.repo_path}")

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=self.repo_path, check=True)

        # Initialize git-annex with URL backend
        subprocess.run(
            ["git", "annex", "init", description],
            cwd=self.repo_path,
            check=True,
        )

        # Configure git-annex to allow yt-dlp access to any IP addresses
        # This is needed for git-annex addurl --no-raw to work with YouTube URLs
        subprocess.run(
            ["git", "config", "annex.security.allowed-ip-addresses", "all"],
            cwd=self.repo_path,
            check=True,
        )

        logger.info("Git-annex repository initialized")

    def configure_gitattributes(self) -> None:
        """Configure .gitattributes for file tracking rules.

        Default: Binary files and files >10k → git-annex
        Large text files (.vtt captions, comments.json) → git-annex
        Small metadata files (.tsv, .md, README) → git
        """
        gitattributes_path = self.repo_path / ".gitattributes"

        rules = [
            "# annextube file tracking configuration",
            "",
            "# Default: Binary files and files >10k go to git-annex",
            "* annex.largefiles=(((mimeencoding=binary)and(largerthan=0))or(largerthan=10k))",
            "",
            "# Small metadata files → git (override default)",
            "*.tsv annex.largefiles=nothing",
            "*.md annex.largefiles=nothing",
            "README* annex.largefiles=nothing",
            "LICENSE* annex.largefiles=nothing",
            ".gitignore annex.largefiles=nothing",
            ".gitattributes annex.largefiles=nothing",
            "",
            "# Sensitive data files → git-annex (contains personal information)",
            "authors.tsv annex.largefiles=anything",
            "comments.json annex.largefiles=anything",
            "",
            "# Large text files → git-annex (VTT captions)",
            "*.vtt annex.largefiles=anything",
            "",
            "# Media files → git-annex (covered by default, explicit for clarity)",
            "*.mp4 annex.largefiles=anything",
            "*.webm annex.largefiles=anything",
            "*.mkv annex.largefiles=anything",
            "*.jpg annex.largefiles=anything",
            "*.jpeg annex.largefiles=anything",
            "*.png annex.largefiles=anything",
            "*.webp annex.largefiles=anything",
        ]

        with open(gitattributes_path, "w") as f:
            f.write("\n".join(rules))

        logger.info("Configured .gitattributes for file tracking")

    def addurl(
        self, url: str, file_path: Path, relaxed: bool = True, fast: bool = True, no_raw: bool = True
    ) -> None:
        """Add URL to git-annex without downloading content.

        Args:
            url: Video URL to track
            file_path: Path where file would be stored
            relaxed: Use --relaxed mode (track URL without verifying)
            fast: Use --fast mode (no content verification)
            no_raw: Use --no-raw mode (ensure yt-dlp is used, not raw download)
        """
        cmd = ["git", "annex", "addurl", url, "--file", str(file_path)]

        if relaxed:
            cmd.append("--relaxed")
        if fast:
            cmd.append("--fast")
        if no_raw:
            cmd.append("--no-raw")

        logger.debug(f"Adding URL to git-annex: {url} -> {file_path}")

        subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True)

    def get_file(self, file_path: Path) -> None:
        """Download content for a tracked file.

        Args:
            file_path: Path to file to download
        """
        logger.info(f"Downloading content: {file_path}")
        subprocess.run(
            ["git", "annex", "get", str(file_path)],
            cwd=self.repo_path,
            check=True,
        )

    def _is_timestamp_only_change(self) -> bool:
        """Check if staged changes are only timestamp updates.

        Returns:
            True if only timestamp fields changed, False otherwise
        """
        try:
            # Get diff of staged changes
            result = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            diff_output = result.stdout
            if not diff_output:
                return False  # No changes staged

            # Check if ALL changed lines are timestamp-only updates
            # Timestamp fields: fetched_at, updated_at, last_modified, last_updated
            timestamp_patterns = [
                '"fetched_at":',
                '"updated_at":',
                '"last_modified":',
                '\tlast_updated\t',  # TSV column
            ]

            lines = diff_output.split('\n')
            changed_lines = [l for l in lines if l.startswith('+') or l.startswith('-')]
            # Filter out diff metadata lines (+++, ---)
            changed_lines = [l for l in changed_lines if not (l.startswith('+++') or l.startswith('---'))]

            if not changed_lines:
                return False  # No actual content changes

            # Check if all changed lines are timestamp updates
            timestamp_changes = 0
            for line in changed_lines:
                if any(pattern in line for pattern in timestamp_patterns):
                    timestamp_changes += 1

            # If all changed lines are timestamp-related, this is timestamp-only
            return timestamp_changes == len(changed_lines)

        except subprocess.CalledProcessError:
            # If we can't check, assume it's not timestamp-only (safer to commit)
            return False

    def add_and_commit(self, message: str, files: Optional[list[Path]] = None) -> bool:
        """Add files and commit changes.

        Uses 'git annex add' to let git-annex decide based on .gitattributes
        whether to commit to git or annex (prevents thumbnails from being
        committed in unlocked mode to git).

        Args:
            message: Commit message
            files: Optional list of specific files to add (None = add all)

        Returns:
            True if commit was made, False if nothing to commit or only timestamps changed
        """
        # Sync filesystem to ensure all writes are flushed to disk
        # This prevents race conditions where git-annex tries to add files
        # that are still being written or buffered in OS caches
        import os
        try:
            os.sync()
        except (OSError, AttributeError):
            # sync() may not be available on all platforms or may fail
            # Fall back to just waiting a moment for buffers to flush
            import time
            time.sleep(0.1)

        if files:
            for f in files:
                subprocess.run(["git", "annex", "add", str(f)], cwd=self.repo_path, check=True)
        else:
            subprocess.run(["git", "annex", "add", "."], cwd=self.repo_path, check=True)

        # Check if only timestamps changed
        if self._is_timestamp_only_change():
            logger.info("Skipping commit - only timestamp fields changed (no real content updates)")
            # Unstage the changes
            subprocess.run(["git", "reset", "HEAD"], cwd=self.repo_path, check=False,
                         capture_output=True)
            return False

        try:
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True,
                         capture_output=True, text=True)
            logger.info(f"Committed changes: {message}")

            # Ensure sensitive files have proper metadata
            self.ensure_sensitive_metadata()

            return True
        except subprocess.CalledProcessError as e:
            # Check if it's just "nothing to commit"
            if "nothing to commit" in e.stdout or "nothing to commit" in e.stderr:
                logger.debug("No changes to commit")
                return False
            # Re-raise if it's a real error
            raise

    def is_annex_repo(self) -> bool:
        """Check if directory is a git-annex repository.

        Returns:
            True if git-annex repo, False otherwise
        """
        git_dir = self.repo_path / ".git"
        annex_dir = git_dir / "annex"
        return git_dir.exists() and annex_dir.exists()

    def set_metadata(self, file_path: Path, metadata: dict[str, str]) -> None:
        """Set git-annex metadata for a file.

        Args:
            file_path: Path to file
            metadata: Dictionary of metadata key-value pairs
        """
        for key, value in metadata.items():
            cmd = ["git", "annex", "metadata", str(file_path), "-s", f"{key}={value}"]
            logger.debug(f"Setting metadata: {key}={value} for {file_path}")
            subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True)

    def set_metadata_if_changed(self, file_path: Path, metadata: dict[str, str]) -> bool:
        """Set git-annex metadata for a file, only updating changed fields.

        Only operates on files in git-annex. Silently skips files in git.
        Compares new metadata with existing and only updates changed fields.

        Args:
            file_path: Path to file (relative to repo root or absolute)
            metadata: Dictionary of metadata key-value pairs to set

        Returns:
            True if metadata was updated, False if skipped (not in annex or no changes)
        """
        # Check if file is in annex
        if not self.is_annexed(file_path):
            logger.debug(f"Skipping metadata for {file_path} (not in git-annex)")
            return False

        # Get existing metadata
        existing = self.get_metadata(file_path)

        # Find fields that need updating
        updates = {}
        for key, new_value in metadata.items():
            existing_values = existing.get(key, [])
            # git-annex stores values as lists, compare as sets
            if new_value not in existing_values:
                updates[key] = new_value

        # Update only changed fields
        if updates:
            for key, value in updates.items():
                cmd = ["git", "annex", "metadata", str(file_path), "-s", f"{key}={value}"]
                subprocess.run(cmd, cwd=self.repo_path, check=True, capture_output=True)
            logger.debug(f"Updated {len(updates)} metadata field(s) for {file_path}")
            return True

        logger.debug(f"No metadata changes for {file_path}")
        return False

    def get_metadata(self, file_path: Path) -> dict[str, list[str]]:
        """Get git-annex metadata for a file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary mapping metadata keys to lists of values
            Empty dict if file has no metadata or is not in annex
        """
        cmd = ["git", "annex", "metadata", "--json", str(file_path)]
        try:
            result = subprocess.run(
                cmd, cwd=self.repo_path, check=True, capture_output=True, text=True
            )
            if result.stdout:
                import json
                data = json.loads(result.stdout)
                # git-annex metadata JSON format: {"fields": {"key": ["value1", "value2"]}}
                return data.get("fields", {})
            return {}
        except subprocess.CalledProcessError:
            # File not in annex or no metadata
            return {}

    def is_annexed(self, file_path: Path) -> bool:
        """Check if a file is managed by git-annex (symlink to annex object).

        Args:
            file_path: Path to file (relative to repo root or absolute)

        Returns:
            True if file is a symlink to git-annex object store
        """
        full_path = self.repo_path / file_path if not file_path.is_absolute() else file_path

        if not full_path.is_symlink():
            return False

        # Check if symlink target points to .git/annex/objects
        try:
            target = full_path.readlink()
            # Resolve relative symlink
            if not target.is_absolute():
                target = (full_path.parent / target).resolve()
            return ".git/annex/objects" in str(target)
        except (OSError, ValueError):
            return False

    def ensure_sensitive_metadata(self) -> None:
        """Ensure sensitive files have proper git-annex metadata.

        Checks all comments.json, captions (*.vtt), and authors.tsv files.
        For each file in git-annex:
        1. Sensitive files: Sets distribution-restrictions=sensitive
        2. For comments.json: Also sets video_id, title, channel, published, filetype
        3. For captions: Sets video_id, title, channel, published, filetype, language, etc.
           by reading metadata from adjacent captions.tsv file

        This should be called after commits to ensure proper metadata tagging.
        """
        import csv
        import glob
        import json

        sensitive_patterns = [
            "videos/**/comments.json",  # Comments in videos/ directory only (not playlist symlinks)
            "authors.tsv",              # Top-level authors file
        ]

        # Also process caption files for video metadata
        caption_patterns = [
            "videos/**/*.vtt",  # All caption files in videos/ directory
        ]

        files_tagged = 0

        # Process sensitive files (comments.json, authors.tsv)
        for pattern in sensitive_patterns:
            for file_str in glob.glob(str(self.repo_path / pattern), recursive=True):
                file_path = Path(file_str).relative_to(self.repo_path)

                # Skip if this is a symlink to another directory (playlist symlinks)
                # We only want to set metadata on the original files in videos/
                if file_path.is_symlink() and "../" in str(file_path.readlink()):
                    logger.debug(f"Skipping {file_path} (symlink to other directory)")
                    continue

                # Only process if file is in git-annex
                if not self.is_annexed(file_path):
                    logger.debug(f"Skipping {file_path} (not in git-annex)")
                    continue

                # Check existing metadata
                existing = self.get_metadata(file_path)
                distribution = existing.get("distribution-restrictions", [])

                # Prepare metadata to set
                new_metadata = {}

                # Always ensure distribution-restrictions
                if "sensitive" not in distribution:
                    new_metadata["distribution-restrictions"] = "sensitive"

                # For comments.json, also set comprehensive video metadata
                if file_path.name == "comments.json":
                    # Try to read video metadata from adjacent metadata.json
                    metadata_file = file_path.parent / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(self.repo_path / metadata_file) as f:
                                video_meta = json.load(f)

                            # Set video metadata if not present or different
                            video_fields = {
                                "video_id": video_meta.get("video_id", ""),
                                "title": video_meta.get("title", ""),
                                "channel": video_meta.get("channel_name", ""),
                                "published": video_meta.get("published_at", "")[:10] if video_meta.get("published_at") else "",
                                "filetype": "comments",
                            }

                            for key, value in video_fields.items():
                                if value and value not in existing.get(key, []):
                                    new_metadata[key] = value

                        except Exception as e:
                            logger.debug(f"Could not read metadata.json for {file_path}: {e}")

                # Set metadata if any fields need updating
                if new_metadata:
                    for key, value in new_metadata.items():
                        self.set_metadata(file_path, {key: value})
                    logger.debug(f"Updated {len(new_metadata)} metadata field(s) for {file_path}")
                    files_tagged += 1

        # Process caption files for comprehensive video metadata
        for pattern in caption_patterns:
            for file_str in glob.glob(str(self.repo_path / pattern), recursive=True):
                file_path = Path(file_str).relative_to(self.repo_path)

                # Skip if this is a symlink to another directory (playlist symlinks)
                if file_path.is_symlink() and "../" in str(file_path.readlink()):
                    logger.debug(f"Skipping {file_path} (symlink to other directory)")
                    continue

                # Only process if file is in git-annex
                if not self.is_annexed(file_path):
                    logger.debug(f"Skipping {file_path} (not in git-annex)")
                    continue

                # Read caption metadata from adjacent captions.tsv
                video_dir = file_path.parent
                captions_tsv = self.repo_path / video_dir / "captions.tsv"
                metadata_json = self.repo_path / video_dir / "metadata.json"

                if not captions_tsv.exists() or not metadata_json.exists():
                    logger.debug(f"Skipping {file_path} (missing captions.tsv or metadata.json)")
                    continue

                try:
                    # Get video metadata
                    with open(metadata_json) as f:
                        video_meta = json.load(f)

                    # Parse captions.tsv to get caption-specific metadata
                    caption_meta = None
                    with open(captions_tsv) as f:
                        reader = csv.DictReader(f, delimiter="\t")
                        for row in reader:
                            # Match by filename (last component of file_path)
                            row_filename = Path(row.get("file_path", "")).name
                            if row_filename == file_path.name:
                                caption_meta = row
                                break

                    if not caption_meta:
                        logger.debug(f"Skipping {file_path} (not found in captions.tsv)")
                        continue

                    # Get language code
                    lang_code = caption_meta.get("language_code", "unknown")

                    # Prepare comprehensive metadata
                    new_metadata = {
                        "video_id": video_meta.get("video_id", ""),
                        "title": video_meta.get("title", ""),
                        "channel": video_meta.get("channel_name", ""),
                        "published": video_meta.get("published_at", "")[:10] if video_meta.get("published_at") else "",
                        "language": lang_code,
                        "filetype": f"caption.{lang_code}",
                    }

                    # Add flags for auto-generated/auto-translated
                    if caption_meta.get("auto_generated") == "True":
                        new_metadata["auto_generated"] = "true"
                    if caption_meta.get("auto_translated") == "True":
                        new_metadata["auto_translated"] = "true"

                    # Check existing metadata
                    existing = self.get_metadata(file_path)

                    # Update only changed fields
                    updates = {}
                    for key, value in new_metadata.items():
                        if value and value not in existing.get(key, []):
                            updates[key] = value

                    if updates:
                        for key, value in updates.items():
                            self.set_metadata(file_path, {key: value})
                        logger.debug(f"Updated {len(updates)} metadata field(s) for {file_path}")
                        files_tagged += 1

                except Exception as e:
                    logger.debug(f"Could not set metadata for {file_path}: {e}")

        if files_tagged > 0:
            logger.info(f"Tagged {files_tagged} file(s) with metadata")
