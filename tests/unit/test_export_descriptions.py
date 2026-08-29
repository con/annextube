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

    def test_contains_full_text_for_nonempty_only(self, archive: Path):
        service = ExportService(archive)
        tsv_path = service.generate_videos_tsv()
        data = json.loads(
            (tsv_path.parent / "video_fulldescriptions.json").read_text(
                encoding="utf-8"
            )
        )
        # Full original text, including newlines beyond the first line
        assert data["aaaaaaaaaaa"] == MULTILINE_DESCRIPTION
        # Single-line descriptions are included too (self-contained lookup)
        assert data["bbbbbbbbbbb"] == "Only one line"
        # Empty/missing descriptions get no entry
        assert set(data) == {"aaaaaaaaaaa", "bbbbbbbbbbb"}

    def test_deterministic_output(self, archive: Path):
        service = ExportService(archive)
        json_path = (
            service.generate_videos_tsv().parent / "video_fulldescriptions.json"
        )
        first = json_path.read_bytes()
        service.generate_videos_tsv()
        assert json_path.read_bytes() == first

    def test_empty_archive_writes_empty_dict(self, tmp_path: Path):
        service = ExportService(tmp_path)
        tsv_path = service.generate_videos_tsv()
        json_path = tsv_path.parent / "video_fulldescriptions.json"
        assert json.loads(json_path.read_text(encoding="utf-8")) == {}

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


class TestGitattributesRule:
    RULE = "video_fulldescriptions.json annex.largefiles=nothing"

    def test_rule_appended_to_existing_gitattributes(self, archive: Path):
        gitattributes = archive / ".gitattributes"
        gitattributes.write_text("*.tsv annex.largefiles=nothing\n")
        ExportService(archive).generate_videos_tsv()
        content = gitattributes.read_text()
        assert "*.tsv annex.largefiles=nothing" in content
        assert self.RULE in content

    def test_rule_created_when_gitattributes_missing(self, archive: Path):
        ExportService(archive).generate_videos_tsv()
        assert self.RULE in (archive / ".gitattributes").read_text()

    def test_rule_appended_idempotently(self, archive: Path):
        service = ExportService(archive)
        service.generate_videos_tsv()
        service.generate_videos_tsv()
        content = (archive / ".gitattributes").read_text()
        assert content.count("video_fulldescriptions.json") == 1

    def test_existing_rule_left_untouched(self, archive: Path):
        gitattributes = archive / ".gitattributes"
        existing = "video_fulldescriptions.json annex.largefiles=nothing\n"
        gitattributes.write_text(existing)
        ExportService(archive).generate_videos_tsv()
        assert gitattributes.read_text() == existing

    def test_configure_gitattributes_includes_rule(self, tmp_path: Path):
        from annextube.services.git_annex import GitAnnexService

        GitAnnexService(tmp_path).configure_gitattributes()
        assert self.RULE in (tmp_path / ".gitattributes").read_text()
