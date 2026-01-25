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
            "# Large text files → git-annex (VTT captions, JSON comments)",
            "*.vtt annex.largefiles=anything",
            "comments.json annex.largefiles=anything",
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

    def add_and_commit(self, message: str, files: Optional[list[Path]] = None) -> bool:
        """Add files and commit changes.

        Args:
            message: Commit message
            files: Optional list of specific files to add (None = add all)

        Returns:
            True if commit was made, False if nothing to commit
        """
        if files:
            for f in files:
                subprocess.run(["git", "add", str(f)], cwd=self.repo_path, check=True)
        else:
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)

        try:
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True,
                         capture_output=True, text=True)
            logger.info(f"Committed changes: {message}")
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
