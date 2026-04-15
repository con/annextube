"""Unit tests for retroactive caption curation during backup (FR-062a)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from annextube.lib.config import ComponentsConfig, Config, CurationConfig
from annextube.services.archiver import Archiver

FIXTURES = Path(__file__).parent.parent / "fixtures"

_GLOSSARY_YAML = (
    "projects:\n"
    '  - term: "DataLad"\n'
    '    patterns: ["data lad", "data glad"]\n'
    '  - term: "git-annex"\n'
    '    patterns: ["git annex", "get annex"]\n'
)


def _make_archive(tmp_path: Path, *, n_videos: int = 1) -> list[Path]:
    """Create a minimal archive with VTT file(s) lacking curated variants.

    Returns list of created VTT paths.
    """
    vtt_src = FIXTURES / "sample_karaoke.vtt"
    vtt_paths = []
    for i in range(n_videos):
        video_dir = tmp_path / "videos" / "2026" / "01" / f"2026-01-0{i + 1}_Video-{i}"
        video_dir.mkdir(parents=True)
        vtt_dst = video_dir / "video.en.vtt"
        shutil.copy(vtt_src, vtt_dst)
        vtt_paths.append(vtt_dst)

    glossary_dir = tmp_path / ".annextube"
    glossary_dir.mkdir(exist_ok=True)
    (glossary_dir / "captions-glossary.yaml").write_text(_GLOSSARY_YAML)

    return vtt_paths


def _make_archiver(tmp_path: Path, *, enabled: bool = True) -> Archiver:
    config = Config(
        components=ComponentsConfig(thumbnails=False, captions=True, comments_depth=0),
        curation=CurationConfig(
            enabled=enabled,
            glossary_path=".annextube/captions-glossary.yaml",
        ),
    )
    return Archiver(tmp_path, config)


@pytest.mark.ai_generated
def test_curates_uncurated_vtts_across_videos(tmp_path: Path) -> None:
    """Scans all video dirs and curates VTTs missing a curated variant."""
    vtt_paths = _make_archive(tmp_path, n_videos=2)
    archiver = _make_archiver(tmp_path)

    count = archiver._curate_uncurated_captions()

    assert count == 2
    for vtt_path in vtt_paths:
        curated = vtt_path.parent / "video.en-curated.vtt"
        assert curated.exists()
        content = curated.read_text()
        assert "WEBVTT" in content
        assert "DataLad" in content


@pytest.mark.ai_generated
def test_skips_already_curated(tmp_path: Path) -> None:
    """Existing curated variant is neither overwritten nor re-curated."""
    vtt_paths = _make_archive(tmp_path)
    curated_path = vtt_paths[0].parent / "video.en-curated.vtt"
    curated_path.write_text("WEBVTT\n\nexisting curated content\n")

    archiver = _make_archiver(tmp_path)
    count = archiver._curate_uncurated_captions()

    assert count == 0
    assert "existing curated content" in curated_path.read_text()


@pytest.mark.ai_generated
@pytest.mark.parametrize("reason,setup_tweak", [
    ("disabled", "disable"),
    ("no_glossary", "remove_glossary"),
])
def test_early_exit(tmp_path: Path, reason: str, setup_tweak: str) -> None:
    """Returns 0 immediately when curation is disabled or no glossary exists."""
    _make_archive(tmp_path)

    if setup_tweak == "remove_glossary":
        (tmp_path / ".annextube" / "captions-glossary.yaml").unlink()
        archiver = _make_archiver(tmp_path)
    else:
        archiver = _make_archiver(tmp_path, enabled=False)

    assert archiver._curate_uncurated_captions() == 0
