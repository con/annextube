"""Integration tests for caption search index building with real pagefind.

These tests run the actual pagefind binary (no mocks) to verify the IPC
protocol works end-to-end, including the WriteFiles step that has been
prone to deadlocks.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

SAMPLE_VTT = textwrap.dedent("""\
    WEBVTT
    Kind: captions
    Language: en

    00:00:00.030 --> 00:00:07.589
    Hello<00:00:00.526><c> world</c><00:00:01.021><c> this</c><00:00:01.269><c> is</c><00:00:01.889><c> a</c><00:00:02.261><c> test</c><00:00:02.880><c> of</c><00:00:03.128><c> the</c><00:00:03.624><c> caption</c><00:00:03.995><c> search</c><00:00:05.111><c> index</c><00:00:06.350><c> builder.</c>

    00:00:07.020 --> 00:00:10.190
    Second<00:00:07.184><c> cue</c><00:00:07.512><c> with</c><00:00:07.676><c> some</c><00:00:07.949><c> more</c><00:00:08.222><c> text</c><00:00:08.496><c> about</c><00:00:08.824><c> containers</c><00:00:09.097><c> and</c><00:00:09.261><c> things.</c>

    00:00:10.050 --> 00:00:15.179
    Third<00:00:10.531><c> cue</c><00:00:10.851><c> about</c><00:00:11.733><c> DataLad</c><00:00:12.054><c> and</c><00:00:12.454><c> git</c><00:00:12.855><c> annex</c><00:00:13.095><c> for</c><00:00:13.576><c> data</c><00:00:13.897><c> management.</c>
""")


def _make_video(archive: Path, video_id: str, title: str, vtt: str) -> Path:
    """Create a video directory with metadata and VTT."""
    video_dir = archive / "videos" / "2025" / "06" / f"{title}_{video_id}"
    video_dir.mkdir(parents=True, exist_ok=True)
    (video_dir / "metadata.json").write_text(
        json.dumps({
            "video_id": video_id,
            "title": title,
            "channel_id": "UCtest",
            "channel_name": "TestChannel",
            "published_at": "2025-06-15T00:00:00",
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
        }),
        encoding="utf-8",
    )
    (video_dir / "video.en.vtt").write_text(vtt, encoding="utf-8")
    return video_dir


@pytest.mark.ai_generated
@pytest.mark.timeout(30)
class TestSearchIndexBuildReal:
    """Integration tests that run the real pagefind binary."""

    @pytest.mark.asyncio
    async def test_fresh_build(self, tmp_path: Path) -> None:
        """Fresh build creates index files on disk."""
        from annextube.services.search_index import build_caption_index

        archive = tmp_path / "archive"
        _make_video(archive, "vid1", "First Video", SAMPLE_VTT)

        stats = await build_caption_index(archive, force=True)

        assert stats.videos_indexed == 1
        assert stats.chunks_created > 0
        pagefind_dir = archive / "web" / "pagefind"
        assert pagefind_dir.is_dir()
        # pagefind produces pagefind.js, pagefind-ui.js, and fragment files
        index_files = list(pagefind_dir.rglob("*"))
        assert len(index_files) > 0

    @pytest.mark.asyncio
    async def test_rebuild_same_data(self, tmp_path: Path) -> None:
        """Rebuilding with force on unchanged data succeeds (no stall)."""
        from annextube.services.search_index import build_caption_index

        archive = tmp_path / "archive"
        _make_video(archive, "vid1", "First Video", SAMPLE_VTT)

        stats1 = await build_caption_index(archive, force=True)
        assert stats1.videos_indexed == 1

        # Second build — should complete without stalling
        stats2 = await build_caption_index(archive, force=True)
        assert stats2.videos_indexed == 1
        assert stats2.chunks_created == stats1.chunks_created

    @pytest.mark.asyncio
    async def test_multiple_videos(self, tmp_path: Path) -> None:
        """Building index with several videos completes without IPC issues."""
        from annextube.services.search_index import build_caption_index

        archive = tmp_path / "archive"
        n_videos = 5
        for i in range(n_videos):
            _make_video(archive, f"vid{i}", f"Video {i}", SAMPLE_VTT)

        stats = await build_caption_index(archive, force=True)

        assert stats.videos_indexed == n_videos
        assert stats.chunks_created > 0
        pagefind_dir = archive / "web" / "pagefind"
        assert pagefind_dir.is_dir()

    @pytest.mark.asyncio
    async def test_rebuild_after_adding_video(self, tmp_path: Path) -> None:
        """Adding a new video and rebuilding produces more chunks."""
        from annextube.services.search_index import build_caption_index

        archive = tmp_path / "archive"
        _make_video(archive, "vid1", "First Video", SAMPLE_VTT)

        stats1 = await build_caption_index(archive, force=True)

        # Add another video
        _make_video(archive, "vid2", "Second Video", SAMPLE_VTT)

        stats2 = await build_caption_index(archive, force=True)
        assert stats2.videos_indexed == 2
        assert stats2.chunks_created > stats1.chunks_created

    @pytest.mark.asyncio
    async def test_many_videos_rebuild(self, tmp_path: Path) -> None:
        """Build + rebuild with 20 videos (~60 chunks) exercises IPC heavily."""
        from annextube.services.search_index import build_caption_index

        archive = tmp_path / "archive"
        for i in range(20):
            _make_video(archive, f"v{i:03d}", f"Video {i}", SAMPLE_VTT)

        stats1 = await build_caption_index(archive, force=True)
        assert stats1.videos_indexed == 20
        assert stats1.chunks_created >= 20

        # Rebuild — must not stall
        stats2 = await build_caption_index(archive, force=True)
        assert stats2.videos_indexed == 20
        assert stats2.chunks_created == stats1.chunks_created

    @pytest.mark.asyncio
    async def test_incremental_skip_no_git(self, tmp_path: Path) -> None:
        """Without git, incremental detection is skipped — always rebuilds."""
        from annextube.services.search_index import build_caption_index

        archive = tmp_path / "archive"
        _make_video(archive, "vid1", "First Video", SAMPLE_VTT)

        # force=False but no git → no .build_commit → full rebuild
        stats = await build_caption_index(archive, force=False)
        assert stats.videos_indexed == 1
