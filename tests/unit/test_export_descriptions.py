"""Tests for description export (FR-042c, Phase 16).

Covers the videos.tsv ``description`` column (first non-empty line) and the
``video_fulldescriptions.json`` lookup exported next to it.
"""

import csv
import json
from pathlib import Path

import pytest

from annextube.lib.tsv_utils import escape_tsv_field
from annextube.services.export import ExportService, first_description_line

MULTILINE_DESCRIPTION = (
    "First line with \ttab\n"
    "\n"
    "Talk by Halchenko about metadata.\n"
    "More details here.\r\n"
    "Last line."
)


class TestFirstDescriptionLine:
    def test_single_line(self):
        assert first_description_line("Only one line") == "Only one line"

    def test_multiline_lf(self):
        assert first_description_line("First\nSecond\nThird") == "First"

    def test_crlf(self):
        assert first_description_line("First\r\nSecond") == "First"

    def test_cr_only(self):
        assert first_description_line("First\rSecond") == "First"

    def test_leading_blank_lines_skipped(self):
        assert first_description_line("\n\n   \nReal start\nrest") == "Real start"

    def test_empty(self):
        assert first_description_line("") == ""

    def test_none(self):
        assert first_description_line(None) == ""

    def test_whitespace_only(self):
        assert first_description_line("  \n\t\n  ") == ""

    def test_strips_surrounding_whitespace(self):
        assert first_description_line("  padded  \nnext") == "padded"


def _make_video(
    videos_dir: Path, rel: str, video_id: str, title: str, description
) -> None:
    video_dir = videos_dir / rel
    video_dir.mkdir(parents=True)
    metadata = {
        "video_id": video_id,
        "title": title,
        "channel_id": "UC0000000000000000000001",
        "channel_name": "Test Channel",
        "published_at": "2026-01-01T00:00:00Z",
        "duration": 10,
        "view_count": 1,
        "like_count": 0,
        "comment_count": 0,
        "thumbnail_url": "",
    }
    if description is not None:
        metadata["description"] = description
    (video_dir / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    videos_dir = tmp_path / "videos"
    _make_video(
        videos_dir, "2026/01/Multi_aaaaaaaaaaa", "aaaaaaaaaaa", "Multi",
        MULTILINE_DESCRIPTION,
    )
    _make_video(
        videos_dir, "2026/01/Single_bbbbbbbbbbb", "bbbbbbbbbbb", "Single",
        "Only one line",
    )
    _make_video(
        videos_dir, "2026/01/Empty_ccccccccccc", "ccccccccccc", "Empty", ""
    )
    _make_video(
        videos_dir, "2026/01/NoDesc_ddddddddddd", "ddddddddddd", "NoDesc", None
    )
    return tmp_path


def _read_tsv_rows(tsv_path: Path) -> list[dict[str, str]]:
    with open(tsv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


class TestDescriptionColumn:
    def test_header_ends_with_description(self, archive: Path):
        service = ExportService(archive)
        tsv_path = service.generate_videos_tsv()
        header = tsv_path.read_text(encoding="utf-8").splitlines()[0]
        assert header.split("\t")[-1] == "description"

    def test_first_nonempty_line_exported_escaped(self, archive: Path):
        service = ExportService(archive)
        tsv_path = service.generate_videos_tsv()
        rows = {r["video_id"]: r for r in _read_tsv_rows(tsv_path)}

        # Raw TSV field carries the escaped first line (tab -> \t sequence)
        assert rows["aaaaaaaaaaa"]["description"] == escape_tsv_field(
            "First line with \ttab"
        )
        assert rows["bbbbbbbbbbb"]["description"] == "Only one line"
        assert rows["ccccccccccc"]["description"] == ""
        assert rows["ddddddddddd"]["description"] == ""

    def test_empty_archive_header_includes_description(self, tmp_path: Path):
        service = ExportService(tmp_path)
        tsv_path = service.generate_videos_tsv()
        header = tsv_path.read_text(encoding="utf-8").splitlines()[0]
        assert header.split("\t")[-1] == "description"
