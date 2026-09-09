"""Unit tests for the `annextube prepare-ghpages` subpath/source-dir extension.

Covers the behavior added for per-PR web UI previews (specs/004-pr-webui-preview):
publishing under a `--subpath` without touching sibling subpaths or the
branch root, and reading frontend/data files from an explicit `--source-dir`
instead of the usual build-output search / `origin/master` checkout.
"""

from pathlib import Path

import pytest

from annextube.cli.prepare_ghpages import (
    build_frontend_for_ghpages,
    copy_data_to_ghpages,
    copy_frontend_to_ghpages,
)


def _make_source_dir(tmp_path: Path) -> Path:
    """Build a fake CI-artifact-shaped source directory: web/ + data files."""
    source = tmp_path / "source"
    web = source / "web"
    web.mkdir(parents=True)
    (web / "index.html").write_text("<html>preview</html>")

    videos = source / "videos" / "chan" / "vid1"
    videos.mkdir(parents=True)
    (videos / "video.mkv").write_text("fake video bytes")

    playlists = source / "playlists"
    playlists.mkdir()
    (playlists / "playlists.tsv").write_text("id\tname\n")

    (source / "authors.tsv").write_text("id\tname\n")
    return source


@pytest.mark.ai_generated
def test_copy_frontend_to_ghpages_source_dir_and_subpath(tmp_path: Path) -> None:
    """--source-dir + --subpath copies web/ contents into <repo>/<subpath>/."""
    source = _make_source_dir(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()

    copy_frontend_to_ghpages(
        repo, "gh-pages", was_built=False, subpath="pr-42", source_dir=source
    )

    assert (repo / "pr-42" / "index.html").read_text() == "<html>preview</html>"
    # nothing written at the branch root
    assert not (repo / "index.html").exists()


@pytest.mark.ai_generated
def test_copy_frontend_to_ghpages_missing_web_dir_raises(tmp_path: Path) -> None:
    """A --source-dir without a web/ subdirectory is a clear error, not a silent no-op."""
    source = tmp_path / "source"
    source.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(FileNotFoundError, match="web"):
        copy_frontend_to_ghpages(
            repo, "gh-pages", was_built=False, subpath="pr-1", source_dir=source
        )


@pytest.mark.ai_generated
def test_copy_data_to_ghpages_source_dir_and_subpath(tmp_path: Path) -> None:
    """--source-dir + --subpath copies data files into <repo>/<subpath>/ only."""
    source = _make_source_dir(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()

    copy_data_to_ghpages(repo, "gh-pages", subpath="pr-42", source_dir=source)

    assert (repo / "pr-42" / "authors.tsv").read_text() == "id\tname\n"
    assert (repo / "pr-42" / "playlists" / "playlists.tsv").exists()
    assert (
        repo / "pr-42" / "videos" / "chan" / "vid1" / "video.mkv"
    ).read_text() == "fake video bytes"
    # nothing written at the branch root
    assert not (repo / "authors.tsv").exists()


@pytest.mark.ai_generated
def test_copy_data_to_ghpages_subpath_isolation(tmp_path: Path) -> None:
    """Publishing pr-2 must not touch an existing pr-1 (or the branch root)."""
    source = _make_source_dir(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()

    # pre-existing content for another PR's preview, and at the root
    existing_pr1 = repo / "pr-1" / "authors.tsv"
    existing_pr1.parent.mkdir(parents=True)
    existing_pr1.write_text("pr-1 content")
    root_marker = repo / "authors.tsv"
    root_marker.write_text("root content")

    copy_data_to_ghpages(repo, "gh-pages", subpath="pr-2", source_dir=source)

    assert (repo / "pr-2" / "authors.tsv").read_text() == "id\tname\n"
    assert existing_pr1.read_text() == "pr-1 content"
    assert root_marker.read_text() == "root content"


@pytest.mark.ai_generated
def test_copy_data_to_ghpages_missing_item_warns_and_continues(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A source-dir missing one of the expected data items skips it, not crashes."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "web").mkdir()
    (source / "authors.tsv").write_text("id\tname\n")
    # deliberately no videos/ or playlists/

    repo = tmp_path / "repo"
    repo.mkdir()

    with caplog.at_level("WARNING"):
        copy_data_to_ghpages(repo, "gh-pages", subpath="pr-3", source_dir=source)

    assert (repo / "pr-3" / "authors.tsv").exists()
    assert not (repo / "pr-3" / "videos").exists()
    assert "videos" in caplog.text


@pytest.mark.ai_generated
def test_build_frontend_base_path_with_subpath(monkeypatch, tmp_path: Path) -> None:
    """Base path includes the subpath when one is given, matching the URL it's served at."""
    captured_env = {}

    def fake_run(cmd, cwd=None, env=None, check=None):  # noqa: ANN001
        captured_env.update(env or {})

        class Result:
            returncode = 0

        return Result()

    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "package.json").write_text("{}")
    (frontend_dir / "node_modules").mkdir()  # skip npm install branch

    monkeypatch.setenv("ANNEXTUBE_FRONTEND_DIR", str(frontend_dir))
    monkeypatch.setattr(
        "annextube.cli.prepare_ghpages.subprocess.run", fake_run
    )

    build_frontend_for_ghpages(tmp_path / "repo", "annextube", subpath="pr-7")

    assert captured_env["VITE_BASE_PATH"] == "/annextube/pr-7/"


@pytest.mark.ai_generated
def test_build_frontend_base_path_without_subpath(monkeypatch, tmp_path: Path) -> None:
    """No subpath falls back to the existing whole-branch base path."""
    captured_env = {}

    def fake_run(cmd, cwd=None, env=None, check=None):  # noqa: ANN001
        captured_env.update(env or {})

        class Result:
            returncode = 0

        return Result()

    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "package.json").write_text("{}")
    (frontend_dir / "node_modules").mkdir()

    monkeypatch.setenv("ANNEXTUBE_FRONTEND_DIR", str(frontend_dir))
    monkeypatch.setattr(
        "annextube.cli.prepare_ghpages.subprocess.run", fake_run
    )

    build_frontend_for_ghpages(tmp_path / "repo", "annextube")

    assert captured_env["VITE_BASE_PATH"] == "/annextube/"
