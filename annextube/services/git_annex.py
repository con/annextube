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

        logger.info("Git-annex repository initialized")

    def configure_gitattributes(self) -> None:
        """Configure .gitattributes for file tracking rules.

        Metadata files (*.json, *.tsv, *.md, *.vtt) → git
        Media files (*.mp4, *.webm, *.jpg, *.png) → git-annex
        """
        gitattributes_path = self.repo_path / ".gitattributes"

        rules = [
            "# annextube file tracking configuration",
            "",
            "# Metadata files → git (text, tracked in git)",
            "*.json annex.largefiles=nothing",
            "*.tsv annex.largefiles=nothing",
            "*.md annex.largefiles=nothing",
            "*.vtt annex.largefiles=nothing",
            "*.txt annex.largefiles=nothing",
            "",
            "# Media files → git-annex (binary, tracked with git-annex)",
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
        self, url: str, file_path: Path, relaxed: bool = True, fast: bool = True
    ) -> None:
        """Add URL to git-annex without downloading content.

        Args:
            url: Video URL to track
            file_path: Path where file would be stored
            relaxed: Use --relaxed mode (track URL without verifying)
            fast: Use --fast mode (no content verification)
        """
        cmd = ["git", "annex", "addurl", url, "--file", str(file_path)]

        if relaxed:
            cmd.append("--relaxed")
        if fast:
            cmd.append("--fast")

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

    def add_and_commit(self, message: str, files: Optional[list[Path]] = None) -> None:
        """Add files and commit changes.

        Args:
            message: Commit message
            files: Optional list of specific files to add (None = add all)
        """
        if files:
            for f in files:
                subprocess.run(["git", "add", str(f)], cwd=self.repo_path, check=True)
        else:
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)

        subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True)

        logger.info(f"Committed changes: {message}")

    def is_annex_repo(self) -> bool:
        """Check if directory is a git-annex repository.

        Returns:
            True if git-annex repo, False otherwise
        """
        git_dir = self.repo_path / ".git"
        annex_dir = git_dir / "annex"
        return git_dir.exists() and annex_dir.exists()
