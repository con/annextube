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


class TestFullDescriptionsJson:
    def test_written_next_to_videos_tsv(self, archive: Path):
        service = ExportService(archive)
        tsv_path = service.generate_videos_tsv()
        json_path = tsv_path.parent / "video_fulldescriptions.json"
        assert json_path.exists()

    def test_only_descriptions_not_fitting_one_line(self, archive: Path):
        service = ExportService(archive)
        tsv_path = service.generate_videos_tsv()
        data = json.loads(
            (tsv_path.parent / "video_fulldescriptions.json").read_text(
                encoding="utf-8"
            )
        )
        # Full original text, including newlines beyond the first line
        assert data["aaaaaaaaaaa"] == MULTILINE_DESCRIPTION
        # Single-line descriptions need no entry -- videos.tsv already
        # carries the whole text
        assert "bbbbbbbbbbb" not in data
        # Empty/missing descriptions get no entry either
        assert set(data) == {"aaaaaaaaaaa"}

    def test_deterministic_output(self, archive: Path):
        service = ExportService(archive)
        json_path = (
            service.generate_videos_tsv().parent / "video_fulldescriptions.json"
        )
        first = json_path.read_bytes()
        service.generate_videos_tsv()
        assert json_path.read_bytes() == first

    def test_empty_archive_writes_no_file(self, tmp_path: Path):
        service = ExportService(tmp_path)
        tsv_path = service.generate_videos_tsv()
        assert not (tsv_path.parent / "video_fulldescriptions.json").exists()

    def test_no_file_when_all_descriptions_single_line(self, tmp_path: Path):
        videos_dir = tmp_path / "videos"
        _make_video(
            videos_dir, "2026/01/One_eeeeeeeeeee", "eeeeeeeeeee", "One",
            "Single line only",
        )
        tsv_path = ExportService(tmp_path).generate_videos_tsv()
        assert not (tsv_path.parent / "video_fulldescriptions.json").exists()

    def test_stale_file_removed_when_no_entries_remain(self, tmp_path: Path):
        videos_dir = tmp_path / "videos"
        _make_video(
            videos_dir, "2026/01/Multi_fffffffffff", "fffffffffff", "Multi",
            "First line\n\nSecond paragraph.",
        )
        service = ExportService(tmp_path)
        json_path = service.generate_videos_tsv().parent / "video_fulldescriptions.json"
        assert json_path.exists()

        # Description shrinks to a single line -> file must go away
        meta_path = videos_dir / "2026/01/Multi_fffffffffff" / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["description"] = "Now single line"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        service.generate_videos_tsv()
        assert not json_path.exists()

    def test_not_written_when_disabled(self, archive: Path, tmp_path: Path):
        # Per-playlist videos.tsv exports pass write_fulldescriptions=False
        playlist_dir = tmp_path / "playlists" / "some-playlist"
        playlist_dir.mkdir(parents=True)
        service = ExportService(archive)
        service.generate_videos_tsv(
            base_dir=playlist_dir, write_fulldescriptions=False
        )
        assert not (playlist_dir / "video_fulldescriptions.json").exists()

    def test_overwrites_readonly_symlink(self, archive: Path):
        # Simulate a stale annexed symlink from an archive without the
        # .gitattributes rule -- export must replace it with a regular file
        service = ExportService(archive)
        json_path = archive / "videos" / "video_fulldescriptions.json"
        target = archive / "stale-annex-object"
        target.write_text("{}", encoding="utf-8")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.symlink_to(target)
        service.generate_videos_tsv()
        assert not json_path.is_symlink()
        assert "aaaaaaaaaaa" in json.loads(json_path.read_text(encoding="utf-8"))
