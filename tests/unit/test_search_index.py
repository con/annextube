"""Unit tests for the Pagefind caption search index builder."""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from annextube.services.search_index import (
    VttCue,
    _ensure_pagefind_subdataset,
    _is_git_repo,
    _save_pagefind_subdataset,
    chunk_vtt_cues,
    parse_vtt,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic VTT content
# ---------------------------------------------------------------------------

CURATED_VTT = textwrap.dedent("""\
    WEBVTT
    Kind: captions
    Language: en

    00:00:00.030 --> 00:00:07.589
    I'm<00:00:00.526><c> the</c><00:00:01.021><c> I</c><00:00:01.269><c> work</c><00:00:01.889><c> in</c><00:00:02.261><c> such</c><00:00:02.880><c> a</c><00:00:03.128><c> lab</c><00:00:03.624><c> in</c><00:00:03.995><c> McGovern</c><00:00:05.111><c> Institute</c><00:00:06.350><c> Institute</c>

    00:00:07.020 --> 00:00:10.190
    so<00:00:07.184><c> today</c><00:00:07.512><c> we</c><00:00:07.676><c> will</c><00:00:07.949><c> talk</c><00:00:08.222><c> talk</c><00:00:08.496><c> about</c><00:00:08.824><c> what</c><00:00:09.097><c> we</c><00:00:09.261><c> are</c><00:00:09.479><c> against</c><00:00:09.917><c> something.</c>

    00:00:10.050 --> 00:00:15.179
    about<00:00:10.531><c> the</c><00:00:10.851><c> containers</c><00:00:11.733><c> and</c><00:00:12.054><c> what</c><00:00:12.454><c> kind</c><00:00:12.855><c> of</c><00:00:13.095><c> issue</c><00:00:13.576><c> you</c><00:00:13.897><c> might</c><00:00:14.378><c> you</c><00:00:14.698><c> might</c>
""")

ORIGINAL_VTT = textwrap.dedent("""\
    WEBVTT
    Kind: captions
    Language: en

    00:00:00.030 --> 00:00:05.690 align:start position:0%

    I'm<00:00:00.780><c> the</c><00:00:01.050><c> I</c><00:00:01.589><c> work</c><00:00:01.949><c> in</c><00:00:02.310><c> such</c><00:00:03.210><c> a</c><00:00:03.240><c> lab</c><00:00:04.020><c> in</c><00:00:04.700><c> McGovern</c>

    00:00:05.690 --> 00:00:05.700 align:start position:0%
    I'm the I work in such a lab in McGovern


    00:00:05.700 --> 00:00:08.450 align:start position:0%
    I'm the I work in such a lab in McGovern
    Institute<00:00:06.020><c> so</c><00:00:07.020><c> today</c><00:00:07.589><c> we</c><00:00:07.859><c> will</c><00:00:08.010><c> talk</c><00:00:08.069><c> talk</c>

    00:00:08.450 --> 00:00:08.460 align:start position:0%
    Institute so today we will talk talk


    00:00:08.460 --> 00:00:10.190 align:start position:0%
    Institute so today we will talk talk
    about<00:00:08.670><c> what</c><00:00:08.849><c> we</c><00:00:08.970><c> are</c><00:00:09.000><c> against</c><00:00:09.360><c> something.</c><00:00:09.570><c> about</c><00:00:10.050><c> the</c>
""")


def _write_vtt(path: Path, content: str) -> None:
    """Helper to write VTT content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_metadata(video_dir: Path, **overrides) -> None:
    """Write a minimal metadata.json for testing."""
    meta = {
        "video_id": "test123",
        "title": "Test Video",
        "channel_id": "UCtest",
        "channel_name": "TestChannel",
        "published_at": "2025-06-15T00:00:00",
        "source_url": "https://www.youtube.com/watch?v=test123",
    }
    meta.update(overrides)
    video_dir.mkdir(parents=True, exist_ok=True)
    (video_dir / "metadata.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )


# ── parse_vtt tests ─────────────────────────────────────────────────────────


@pytest.mark.ai_generated
class TestParseVtt:
    """Tests for parse_vtt -- VTT parsing with <c> tag stripping."""

    def test_curated_vtt_extracts_plain_text(self, tmp_path: Path) -> None:
        """Curated VTT cues have <c> tags stripped to plain text."""
        vtt_file = tmp_path / "video.en-curated.vtt"
        _write_vtt(vtt_file, CURATED_VTT)

        cues = parse_vtt(vtt_file)

        assert len(cues) == 3
        # First cue text should have no tags
        assert "<c>" not in cues[0].text
        assert "<00:" not in cues[0].text
        assert "I'm" in cues[0].text
        assert "McGovern" in cues[0].text

    def test_curated_vtt_timestamps(self, tmp_path: Path) -> None:
        """Curated VTT cues have correct start/end timestamps."""
        vtt_file = tmp_path / "video.en-curated.vtt"
        _write_vtt(vtt_file, CURATED_VTT)

        cues = parse_vtt(vtt_file)

        assert cues[0].start == pytest.approx(0.030)
        assert cues[0].end == pytest.approx(7.589)
        assert cues[1].start == pytest.approx(7.020)
        assert cues[1].end == pytest.approx(10.190)

    def test_original_vtt_handles_style_attributes(self, tmp_path: Path) -> None:
        """Original VTT with align:start position:0% is parsed correctly."""
        vtt_file = tmp_path / "video.en.vtt"
        _write_vtt(vtt_file, ORIGINAL_VTT)

        cues = parse_vtt(vtt_file)

        # Near-zero-duration "static" cues (05.690-->05.700, 08.450-->08.460)
        # should be skipped
        assert len(cues) >= 2

        # Tags should be stripped from all cues
        for cue in cues:
            assert "<c>" not in cue.text
            assert "</c>" not in cue.text
            assert "<00:" not in cue.text

    def test_original_vtt_skips_static_cues(self, tmp_path: Path) -> None:
        """Near-zero-duration 'static' cues in original VTTs are skipped."""
        vtt_file = tmp_path / "video.en.vtt"
        _write_vtt(vtt_file, ORIGINAL_VTT)

        cues = parse_vtt(vtt_file)

        # None of the cues should have near-zero duration
        for cue in cues:
            assert (cue.end - cue.start) >= 0.02

    def test_empty_vtt(self, tmp_path: Path) -> None:
        """An empty or header-only VTT returns no cues."""
        vtt_file = tmp_path / "video.en.vtt"
        _write_vtt(vtt_file, "WEBVTT\nKind: captions\nLanguage: en\n\n")

        cues = parse_vtt(vtt_file)
        assert cues == []


# ── chunk_vtt_cues tests ────────────────────────────────────────────────────


@pytest.mark.ai_generated
class TestChunkVttCues:
    """Tests for chunk_vtt_cues -- grouping cues into paragraph chunks."""

    def test_empty_input(self) -> None:
        """Empty cue list returns empty chunk list."""
        assert chunk_vtt_cues([]) == []

    def test_exact_target_size(self) -> None:
        """Cues are grouped in chunks of target_size when no sentence endings."""
        cues = [
            VttCue(text=f"word{i}", start=float(i), end=float(i + 1))
            for i in range(12)
        ]
        chunks = chunk_vtt_cues(cues, target_size=6)

        assert len(chunks) == 2
        assert chunks[0].cue_count == 6
        assert chunks[1].cue_count == 6
        assert chunks[0].start_time == 0.0
        assert chunks[0].end_time == 6.0
        assert chunks[1].start_time == 6.0
        assert chunks[1].end_time == 12.0

    def test_prefers_sentence_boundaries(self) -> None:
        """Chunks break at sentence-ending punctuation within the +/-2 window."""
        cues = [
            VttCue(text="hello", start=0.0, end=1.0),
            VttCue(text="world", start=1.0, end=2.0),
            VttCue(text="this", start=2.0, end=3.0),
            VttCue(text="is a sentence.", start=3.0, end=4.0),  # sentence end at idx 3
            VttCue(text="next", start=4.0, end=5.0),
            VttCue(text="part", start=5.0, end=6.0),
            VttCue(text="here", start=6.0, end=7.0),
            VttCue(text="done!", start=7.0, end=8.0),  # sentence end at idx 7
        ]
        # target=6, window = [4..8], sentence end at idx 3 is within [4..8]?
        # min_size=4, max_size=8. First chunk looks for sentence end at idx 4..7.
        # idx 3 has ".", but range starts at 4 (i + min_size = 0 + 4 = 4).
        # idx 7 has "!" at position 7, which is in range [4,8). best_end=8
        # So first chunk is 0..8, all cues.
        # Actually let's use target=4 for a better test.
        chunks = chunk_vtt_cues(cues, target_size=4)

        # target=4, min=2, max=6.  First chunk: range [2,6).
        # idx 3 "is a sentence." ends sentence -> best_end=4
        assert chunks[0].cue_count == 4
        assert chunks[0].text.endswith("sentence.")

        # Second chunk: starts at idx 4, range [6,10) but only idx 4..7 available
        # idx 7 "done!" ends sentence -> best_end=8
        assert chunks[1].cue_count == 4
        assert chunks[1].text.endswith("done!")

    def test_single_long_cue(self) -> None:
        """A cue with >100 words becomes its own chunk."""
        long_text = " ".join(f"word{i}" for i in range(120))
        cues = [
            VttCue(text=long_text, start=0.0, end=60.0),
            VttCue(text="short", start=60.0, end=61.0),
        ]
        chunks = chunk_vtt_cues(cues, target_size=6)

        assert chunks[0].cue_count == 1
        assert len(chunks[0].text.split()) == 120
        assert chunks[1].cue_count == 1
        assert chunks[1].text == "short"

    def test_small_remainder(self) -> None:
        """Cues that don't fill a full chunk still produce a chunk."""
        cues = [
            VttCue(text="alpha", start=0.0, end=1.0),
            VttCue(text="beta", start=1.0, end=2.0),
        ]
        chunks = chunk_vtt_cues(cues, target_size=6)

        assert len(chunks) == 1
        assert chunks[0].cue_count == 2
        assert chunks[0].text == "alpha beta"

    def test_chunk_text_is_concatenated(self) -> None:
        """Chunk text is the concatenation of its cue texts."""
        cues = [
            VttCue(text="one", start=0.0, end=1.0),
            VttCue(text="two", start=1.0, end=2.0),
            VttCue(text="three", start=2.0, end=3.0),
        ]
        chunks = chunk_vtt_cues(cues, target_size=3)

        assert len(chunks) == 1
        assert chunks[0].text == "one two three"
        assert chunks[0].start_time == 0.0
        assert chunks[0].end_time == 3.0


# ── build_caption_index tests ──────────────────────────────────────────────


def _make_archive(
    tmp_path: Path,
    *,
    has_curated: bool = False,
    has_original: bool = True,
    has_vtt: bool = True,
    video_id: str = "abc123",
    channel_name: str = "TestChannel",
) -> Path:
    """Create a minimal archive layout for testing the index builder."""
    archive = tmp_path / "archive"
    video_dir = archive / "videos" / "2025" / "06" / f"TestVideo_{video_id}"
    _write_metadata(
        video_dir,
        video_id=video_id,
        channel_name=channel_name,
        title="Test Video",
        published_at="2025-06-15T00:00:00",
    )
    if has_vtt:
        if has_curated:
            _write_vtt(video_dir / "video.en-curated.vtt", CURATED_VTT)
        if has_original:
            _write_vtt(video_dir / "video.en.vtt", ORIGINAL_VTT)
    return archive


class _FakeIndex:
    """A fake PagefindIndex that records add_custom_record calls."""

    def __init__(self, config=None):
        self.records: list[dict] = []
        self.written = False
        self._config = config

    async def add_custom_record(self, **kwargs):
        self.records.append(kwargs)

    async def write_files(self, output_path=None):
        self.written = True


class _FakeService:
    """A fake PagefindService for testing."""

    def __init__(self, fake_index):
        self._fake_index = fake_index

    async def create_index(self, config=None):
        self._fake_index._config = config
        return self._fake_index

    async def close(self):
        pass


@pytest.mark.ai_generated
class TestBuildCaptionIndex:
    """Tests for build_caption_index with mocked Pagefind."""

    @pytest.fixture(autouse=True)
    def _mock_pagefind_imports(self):
        """Mock pagefind imports and service creation for all build_caption_index tests."""
        self.fake_index = _FakeIndex()
        fake_service = _FakeService(self.fake_index)

        async def _mock_write(service, index, output_path):
            self.fake_index.written = True

        with (
            patch("annextube.services.search_index.IndexConfig", MagicMock()),
            patch("annextube.services.search_index.PagefindIndex", _FakeIndex),
            patch(
                "annextube.services.search_index._create_pagefind_service",
                AsyncMock(return_value=fake_service),
            ),
            patch(
                "annextube.services.search_index._pagefind_write_files",
                _mock_write,
            ),
        ):
            yield

    @pytest.mark.asyncio
    async def test_curated_preferred_over_original(self, tmp_path: Path) -> None:
        """When both curated and original VTTs exist, curated is indexed."""
        archive = _make_archive(tmp_path, has_curated=True, has_original=True)

        with patch(
            "annextube.services.search_index._current_head",
            return_value="abc123def",
        ):
            from annextube.services.search_index import build_caption_index

            stats = await build_caption_index(archive, force=True)

        assert stats.videos_indexed == 1
        assert stats.videos_curated == 1
        assert stats.videos_original == 0
        assert stats.chunks_created > 0
        assert self.fake_index.written

    @pytest.mark.asyncio
    async def test_original_used_as_fallback(self, tmp_path: Path) -> None:
        """When no curated VTT exists, the original VTT is indexed."""
        archive = _make_archive(tmp_path, has_curated=False, has_original=True)

        with patch(
            "annextube.services.search_index._current_head",
            return_value="abc123def",
        ):
            from annextube.services.search_index import build_caption_index

            stats = await build_caption_index(archive, force=True)

        assert stats.videos_indexed == 1
        assert stats.videos_curated == 0
        assert stats.videos_original == 1
        assert stats.chunks_created > 0

    @pytest.mark.asyncio
    async def test_no_vtt_skipped(self, tmp_path: Path) -> None:
        """Videos with no VTT files are skipped."""
        archive = _make_archive(tmp_path, has_vtt=False)

        with patch(
            "annextube.services.search_index._current_head",
            return_value="abc123def",
        ):
            from annextube.services.search_index import build_caption_index

            stats = await build_caption_index(archive, force=True)

        assert stats.videos_indexed == 0
        assert stats.videos_skipped == 1
        assert stats.chunks_created == 0

    @pytest.mark.asyncio
    async def test_record_url_format(self, tmp_path: Path) -> None:
        """Each record URL follows the #/video/{id}?t={seconds} format."""
        archive = _make_archive(tmp_path, has_curated=True, video_id="myVid42")

        with patch(
            "annextube.services.search_index._current_head",
            return_value="abc123def",
        ):
            from annextube.services.search_index import build_caption_index

            await build_caption_index(archive, force=True)

        assert len(self.fake_index.records) > 0
        for rec in self.fake_index.records:
            assert rec["url"].startswith("#/video/myVid42?t=")
            assert rec["language"] == "en"
            assert rec["meta"]["video_id"] == "myVid42"
            assert rec["meta"]["channel_name"] == "TestChannel"
            assert rec["filters"]["year"] == ["2025"]

    @pytest.mark.asyncio
    async def test_incremental_skip_no_changes(self, tmp_path: Path) -> None:
        """If .build_commit matches HEAD and no VTT changed, skip indexing."""
        archive = _make_archive(tmp_path, has_curated=True)
        pagefind_dir = archive / "web" / "pagefind"
        pagefind_dir.mkdir(parents=True)
        (pagefind_dir / ".build_commit").write_text("deadbeef\n")

        with (
            patch(
                "annextube.services.search_index._current_head",
                return_value="cafebabe",
            ),
            patch(
                "annextube.services.search_index._vtt_changed_since",
                return_value=False,
            ),
        ):
            from annextube.services.search_index import build_caption_index

            stats = await build_caption_index(archive, force=False)

        # Should have been skipped entirely
        assert stats.videos_indexed == 0
        assert stats.chunks_created == 0

    @pytest.mark.asyncio
    async def test_incremental_skip_same_commit(self, tmp_path: Path) -> None:
        """If .build_commit equals HEAD, skip indexing."""
        archive = _make_archive(tmp_path, has_curated=True)
        pagefind_dir = archive / "web" / "pagefind"
        pagefind_dir.mkdir(parents=True)
        (pagefind_dir / ".build_commit").write_text("deadbeef\n")

        with patch(
            "annextube.services.search_index._current_head",
            return_value="deadbeef",
        ):
            from annextube.services.search_index import build_caption_index

            stats = await build_caption_index(archive, force=False)

        assert stats.videos_indexed == 0
        assert stats.chunks_created == 0

    @pytest.mark.asyncio
    async def test_force_rebuild_ignores_build_commit(self, tmp_path: Path) -> None:
        """force=True rebuilds even when .build_commit exists."""
        archive = _make_archive(tmp_path, has_curated=True)
        pagefind_dir = archive / "web" / "pagefind"
        pagefind_dir.mkdir(parents=True)
        (pagefind_dir / ".build_commit").write_text("deadbeef\n")

        with patch(
            "annextube.services.search_index._current_head",
            return_value="deadbeef",
        ):
            from annextube.services.search_index import build_caption_index

            stats = await build_caption_index(archive, force=True)

        assert stats.videos_indexed == 1
        assert stats.chunks_created > 0
        assert self.fake_index.written

    @pytest.mark.asyncio
    async def test_no_subdataset_when_not_git_repo(self, tmp_path: Path) -> None:
        """When archive is not a git repo, no subdataset ops happen."""
        archive = _make_archive(tmp_path, has_curated=True)
        # No .git dir -- not a git repo

        with patch(
            "annextube.services.search_index._current_head",
            return_value="abc123def",
        ):
            from annextube.services.search_index import build_caption_index

            stats = await build_caption_index(archive, force=True)

        assert stats.videos_indexed == 1
        # No datalad module should have been imported


# ── DataLad subdataset helper tests ────────────────────────────────────────


@pytest.mark.ai_generated
class TestDataladSubdatasetHelpers:
    """Tests for DataLad subdataset management helpers."""

    def test_is_git_repo_true(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        assert _is_git_repo(tmp_path) is True

    def test_is_git_repo_false(self, tmp_path: Path) -> None:
        assert _is_git_repo(tmp_path) is False

    def test_ensure_noop_for_non_git(self, tmp_path: Path) -> None:
        """No subdataset created when archive is not a git repo."""
        pagefind_dir = tmp_path / "web" / "pagefind"
        result = _ensure_pagefind_subdataset(tmp_path, pagefind_dir)
        assert result is False
        assert not pagefind_dir.exists()

    def test_ensure_skips_existing(self, tmp_path: Path) -> None:
        """Returns True without re-creating if subdataset already exists."""
        from datalad.api import create

        create(path=str(tmp_path), force=True, result_renderer="disabled")
        pagefind_dir = tmp_path / "web" / "pagefind"
        result1 = _ensure_pagefind_subdataset(tmp_path, pagefind_dir)
        assert result1 is True

        # Second call should be idempotent — no error, still True
        result2 = _ensure_pagefind_subdataset(tmp_path, pagefind_dir)
        assert result2 is True

    def test_ensure_creates_gitattributes(self, tmp_path: Path) -> None:
        """Real DataLad create with cfg_text2git produces .gitattributes in subdataset."""
        from datalad.api import create

        create(path=str(tmp_path), force=True, result_renderer="disabled")

        pagefind_dir = tmp_path / "web" / "pagefind"
        result = _ensure_pagefind_subdataset(tmp_path, pagefind_dir)

        assert result is True
        assert (pagefind_dir / ".git").exists(), "subdataset .git should exist"
        assert (pagefind_dir / ".gitattributes").exists(), (
            "cfg_text2git should create .gitattributes in subdataset"
        )
        gitattributes = (pagefind_dir / ".gitattributes").read_text()
        assert "annex.largefiles" in gitattributes
        # Subdataset should be registered in parent
        assert (tmp_path / ".gitmodules").exists()

    def test_save_noop_when_no_pagefind_git(self, tmp_path: Path) -> None:
        """Save is a no-op when web/pagefind/.git does not exist."""
        (tmp_path / "web" / "pagefind").mkdir(parents=True)
        _save_pagefind_subdataset(tmp_path)

    def test_save_commits_pagefind_subdataset(self, tmp_path: Path) -> None:
        """Save commits files in the pagefind subdataset and updates the parent."""
        from datalad.api import create

        create(path=str(tmp_path), force=True, result_renderer="disabled")
        pagefind_dir = tmp_path / "web" / "pagefind"
        _ensure_pagefind_subdataset(tmp_path, pagefind_dir)

        # Write a file into the subdataset
        (pagefind_dir / "test.js").write_text("// test")
        _save_pagefind_subdataset(tmp_path)

        # Subdataset should be clean
        sub_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(pagefind_dir), capture_output=True, text=True, check=True,
        )
        assert sub_status.stdout.strip() == "", "subdataset should be clean after save"

        # Parent should have the submodule pointer updated
        parent_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(tmp_path), capture_output=True, text=True, check=True,
        )
        assert parent_status.stdout.strip() == "", "parent should be clean after save"

    @pytest.mark.asyncio
    async def test_build_creates_and_saves_subdataset(self, tmp_path: Path) -> None:
        """build_caption_index creates DataLad subdataset at web/pagefind/."""
        from datalad.api import create

        archive = _make_archive(tmp_path, has_curated=True)
        create(path=str(archive), force=True, result_renderer="disabled")
        # Need a commit so _current_head returns something
        subprocess.run(
            ["git", "add", "-A"], cwd=str(archive), capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=str(archive), capture_output=True, check=True,
        )

        fake_index = _FakeIndex()
        fake_service = _FakeService(fake_index)

        async def _mock_write(service, index, output_path):
            fake_index.written = True

        with (
            patch(
                "annextube.services.search_index._create_pagefind_service",
                AsyncMock(return_value=fake_service),
            ),
            patch(
                "annextube.services.search_index._pagefind_write_files",
                _mock_write,
            ),
            patch("annextube.services.search_index.IndexConfig", MagicMock()),
            patch("annextube.services.search_index.PagefindIndex", _FakeIndex),
        ):
            from annextube.services.search_index import build_caption_index

            stats = await build_caption_index(archive, force=True)

        assert stats.videos_indexed == 1
        pagefind_dir = archive / "web" / "pagefind"
        assert (pagefind_dir / ".git").exists(), "subdataset should be created"
        assert (pagefind_dir / ".gitattributes").exists(), (
            "cfg_text2git should create .gitattributes"
        )
