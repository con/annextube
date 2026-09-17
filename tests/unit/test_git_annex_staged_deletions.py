"""Tests for proper staging of deletions and robustness of the timestamp filter loop.

Regression tests for the scenario observed in YarikOpticTube (2026-02-16):
- A playlist entry was renumbered (old symlink deleted, new one created).
- `git annex add .` staged the new file but left the stale deletion in the index.
- `_filter_timestamp_only_changes` bailed entirely when `git diff <deleted-path>`
  returned exit 128, skipping cleanup of timestamp-only files that came later.
- `git commit` failed with no logged output, making the root cause invisible.
"""

import json
import logging
import subprocess
import unittest.mock
from pathlib import Path

import pytest

from annextube.services.git_annex import GitAnnexService


def _init_repo_with_files(repo: Path, files: dict[str, str]) -> None:
    """Write, add, and commit a set of {relative_path: content} files."""
    for rel, content in files.items():
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=repo, check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# Fix 2: add_and_commit must stage deletions
# ---------------------------------------------------------------------------

@pytest.mark.ai_generated
def test_add_and_commit_stages_deletion_of_renamed_entry(datalad_repo: Path) -> None:
    """Renaming a playlist entry (delete old, create new) must be fully committed.

    Reproduces the YarikOpticTube bug: when a playlist entry is renumbered
    (e.g. 0004_Лисёнок-Вук → 0005_Лисёнок-Вук after a new earlier video is
    inserted), the old symlink is deleted but `git annex add .` does not stage
    that deletion.  The commit therefore omits the deletion, leaving the stale
    index entry forever.
    """
    old_name = "playlists/Kids/0004_2013-02-11_Лисёнок-Вук"
    new_name = "playlists/Kids/0005_2013-02-11_Лисёнок-Вук"
    fake_target = "../../../videos/2013/02/2013-02-11_Лисёнок-Вук"

    _init_repo_with_files(datalad_repo, {old_name: fake_target})

    # Simulate renumbering: delete old, create new — without staging either
    (datalad_repo / old_name).unlink()
    new_path = datalad_repo / new_name
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text(fake_target)

    service = GitAnnexService(datalad_repo)
    result = service.add_and_commit("Backup playlist: Kids (1 video, renumbered)")

    assert result is True, "add_and_commit should report a commit was made"

    # Deletion must be staged and committed: old name gone from index
    ls_old = subprocess.run(
        ["git", "ls-files", old_name],
        cwd=datalad_repo, capture_output=True, text=True, check=True,
    )
    assert ls_old.stdout.strip() == "", (
        f"{old_name!r} still in git index — deletion was not staged"
    )

    # New name must be in index
    ls_new = subprocess.run(
        ["git", "ls-files", new_name],
        cwd=datalad_repo, capture_output=True, text=True, check=True,
    )
    assert ls_new.stdout.strip() != "", (
        f"{new_name!r} missing from git index — new file was not committed"
    )

    # Working tree should be clean after commit
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=datalad_repo, capture_output=True, text=True, check=True,
    )
    assert status.stdout.strip() == "", "Working tree should be clean after commit"


@pytest.mark.ai_generated
def test_add_and_commit_deletion_only_is_committed(datalad_repo: Path) -> None:
    """A plain deletion of a tracked file (no new files) must still be committed."""
    _init_repo_with_files(datalad_repo, {"playlists/old_entry": "target"})

    (datalad_repo / "playlists" / "old_entry").unlink()

    service = GitAnnexService(datalad_repo)
    result = service.add_and_commit("Remove stale playlist entry")

    assert result is True

    ls = subprocess.run(
        ["git", "ls-files", "playlists/old_entry"],
        cwd=datalad_repo, capture_output=True, text=True, check=True,
    )
    assert ls.stdout.strip() == "", "Deleted file should be gone from index"


# ---------------------------------------------------------------------------
# Fix 1: _filter_timestamp_only_changes must not abort when one file's diff fails
# ---------------------------------------------------------------------------

@pytest.mark.ai_generated
def test_filter_continues_and_restores_after_per_file_diff_failure(
    datalad_repo: Path,
) -> None:
    """A per-file git-diff failure must be skipped; other files are still processed.

    Reproduces the scenario where git diff <deleted-annex-symlink> exits 128.
    With the old whole-function try/except the first failure aborted the loop,
    leaving timestamp-only files un-restored.  With the fix, only the failing
    file is skipped (treated as a real change), and the loop continues.
    """
    trouble_path = "playlists/Kids/0004_2013-02-11_Лисёнок-Вук"
    ts_file = "playlists/other/metadata.json"

    initial_data = {"video_id": "abc", "title": "Test", "fetched_at": "2026-01-01T00:00:00"}
    _init_repo_with_files(datalad_repo, {
        trouble_path: "annex-target",
        ts_file: json.dumps(initial_data, indent=2),
    })

    # trouble_path: delete it (simulates deleted-annex-symlink showing in diff)
    (datalad_repo / trouble_path).unlink()

    # ts_file: change only the timestamp — should be restored
    updated = {**initial_data, "fetched_at": "2026-06-01T12:00:00"}
    (datalad_repo / ts_file).write_text(json.dumps(updated, indent=2))

    original_run = subprocess.run

    def _selective_fail(cmd, **kwargs):
        """Fail exactly as git does for a deleted annex symlink (exit 128)."""
        if (
            isinstance(cmd, list)
            and cmd[:2] == ["git", "diff"]
            and len(cmd) == 3
            and cmd[2] == trouble_path
        ):
            raise subprocess.CalledProcessError(128, cmd, "", "fatal: bad object")
        return original_run(cmd, **kwargs)

    service = GitAnnexService(datalad_repo)
    with unittest.mock.patch("subprocess.run", side_effect=_selective_fail):
        result = service._filter_timestamp_only_changes()

    # trouble_path counts as a real change → overall result must be True
    assert result is True, "Should still report real changes (the undiffable deletion)"

    # ts_file had only timestamp changes → must have been restored despite the failure
    diff_out = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=datalad_repo, capture_output=True, text=True, check=True,
    ).stdout
    assert ts_file not in diff_out, (
        f"{ts_file!r} should have been restored (timestamp-only) but wasn't"
    )


# ---------------------------------------------------------------------------
# Fix 3: git commit failure output must be logged before re-raising
# ---------------------------------------------------------------------------

@pytest.mark.ai_generated
def test_add_and_commit_logs_git_commit_failure(
    datalad_repo: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A non-trivial git commit failure must log its stdout/stderr before re-raising."""
    # Stage a real change so we get past the timestamp filter
    new_file = datalad_repo / "new.json"
    new_file.write_text(json.dumps({"video_id": "xyz", "title": "New"}))

    original_run = subprocess.run
    fake_stdout = "pre-commit hook output: something went wrong"
    fake_stderr = "error: hook failed"

    def _fail_commit(cmd, **kwargs):
        if isinstance(cmd, list) and cmd[:2] == ["git", "commit"]:
            raise subprocess.CalledProcessError(
                1, cmd, fake_stdout, fake_stderr
            )
        return original_run(cmd, **kwargs)

    service = GitAnnexService(datalad_repo)
    with caplog.at_level(logging.ERROR, logger="annextube.services.git_annex"):
        with unittest.mock.patch("subprocess.run", side_effect=_fail_commit):
            with pytest.raises(subprocess.CalledProcessError):
                service.add_and_commit("Test commit")

    # The failure details must appear in the log
    combined_log = " ".join(caplog.messages)
    assert fake_stdout in combined_log or fake_stderr in combined_log, (
        "git commit stdout/stderr should be logged before re-raising"
    )
