"""Shared test fixtures for annextube tests.

Provides two fixtures that use production initialization code instead of
manual git init + git annex init:

- annextube_archive: Full CLI init (for Archiver-based integration tests)
- datalad_repo: Lightweight Python API init (for GitAnnexService unit tests)
"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def annextube_archive(tmp_path: Path) -> Path:
    """Create an annextube archive using the production CLI init.

    Runs ``annextube init --datalad`` with minimal component settings,
    producing a repository identical to what a real user would get.

    Use this fixture for integration tests that create an Archiver and
    run backup / update workflows.
    """
    subprocess.run(
        [
            sys.executable, "-m", "annextube", "init",
            str(tmp_path),
            "--datalad",
            "--no-videos",
            "--comments-depth", "0",
            "--no-captions",
            "--no-thumbnails",
        ],
        check=True,
        capture_output=True,
    )
    return tmp_path


@pytest.fixture
def datalad_repo(tmp_path: Path) -> Path:
    """Create a lightweight DataLad dataset using the Python API.

    Calls ``GitAnnexService.init_datalad_dataset()`` followed by
    ``configure_gitattributes()`` and commits the result.

    Use this fixture for unit tests that need a git-annex repo as
    infrastructure but don't exercise the full Archiver pipeline.
    """
    from annextube.services.git_annex import GitAnnexService

    svc = GitAnnexService(tmp_path)
    svc.init_datalad_dataset()
    svc.configure_gitattributes()
    svc.add_and_commit("Initial repository setup")
    return tmp_path
