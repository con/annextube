"""Pagefind-based full-text caption search index builder.

Builds a Pagefind search index from VTT caption files during ``generate-web``.
Curated VTTs are preferred; original VTTs serve as a fallback.  Each VTT is
parsed into cues, grouped into paragraph-sized chunks, and added as custom
records so that Pagefind can serve cross-caption search from static files.

When the archive is a DataLad dataset, the index output at ``web/pagefind/``
is managed as a DataLad subdataset (git submodule) with ``cfg_proc=text2git``
so that text files (JS, JSON, CSS) live in git and binary index fragments go
to git-annex.  This isolates the ~10k derived index files from the main repo.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from datalad.api import Dataset
from datalad.api import create as datalad_create

from annextube.lib.logging_config import get_logger

logger = get_logger(__name__)

# Guard the optional pagefind import -- the package is only required when the
# user opts into search indexing (``--search-index``).
try:
    from pagefind.index import IndexConfig, PagefindIndex
except ImportError:  # pragma: no cover
    PagefindIndex = None  # type: ignore[assignment,misc]
    IndexConfig = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class VttCue:
    """A single VTT cue with plain text and timing."""

    text: str
    start: float
    end: float


@dataclass
class CaptionChunk:
    """A paragraph-sized group of consecutive VTT cues."""

    text: str
    start_time: float
    end_time: float
    cue_count: int


@dataclass
class IndexStats:
    """Statistics from a search index build."""

    videos_indexed: int = 0
    videos_curated: int = 0
    videos_original: int = 0
    videos_skipped: int = 0
    chunks_created: int = 0
    index_size_bytes: int = 0


# ---------------------------------------------------------------------------
# VTT parsing
# ---------------------------------------------------------------------------

# Matches inline word-level timestamps like <00:01:23.456>
_INLINE_TS_RE = re.compile(r"<\d{2}:\d{2}:\d{2}\.\d{3}>")
# Matches <c> and </c> tags
_C_TAG_RE = re.compile(r"</?c>")
# Matches the cue timing line (with optional style attributes)
_TIMING_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})"
)
# Sentence-ending punctuation
_SENTENCE_END_RE = re.compile(r"[.!?]\s*$")


def _ts_to_seconds(ts: str) -> float:
    """Convert ``HH:MM:SS.mmm`` to seconds."""
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _strip_tags(line: str) -> str:
    """Remove ``<c>``, ``</c>`` and inline timestamp tags from *line*."""
    line = _INLINE_TS_RE.sub("", line)
    line = _C_TAG_RE.sub("", line)
    return line.strip()


def parse_vtt(vtt_path: Path) -> list[VttCue]:
    """Parse a VTT file into a list of :class:`VttCue` objects.

    Handles both curated and original YouTube VTTs which use ``<c>`` word-level
    timestamp tags.  Original VTTs additionally contain near-zero-duration
    "static" cue blocks (the previous accumulated text shown as a frozen
    subtitle) and ``align:start position:0%`` style attributes on the timing
    line -- both are handled transparently.

    Parameters
    ----------
    vtt_path:
        Path to a ``.vtt`` file.

    Returns
    -------
    list[VttCue]
        Parsed cues with plain text and start/end times.
    """
    content = vtt_path.read_text(encoding="utf-8")
    blocks = content.split("\n\n")
    cues: list[VttCue] = []

    for block in blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue

        ts_line: str | None = None
        text_lines: list[str] = []
        for line in lines:
            if "-->" in line:
                ts_line = line
            elif ts_line is not None:
                text_lines.append(line)

        if not ts_line or not text_lines:
            continue

        m = _TIMING_RE.search(ts_line)
        if not m:
            continue

        cue_start = _ts_to_seconds(m.group(1))
        cue_end = _ts_to_seconds(m.group(2))

        # Skip near-zero-duration cues (YouTube's "static" subtitle lines)
        if abs(cue_end - cue_start) < 0.02:
            continue

        # Build plain text from all text lines, stripping <c> / timestamp tags
        plain_parts: list[str] = []
        for tl in text_lines:
            stripped = _strip_tags(tl)
            if stripped:
                plain_parts.append(stripped)

        plain_text = " ".join(plain_parts)
        if not plain_text:
            continue

        cues.append(VttCue(text=plain_text, start=cue_start, end=cue_end))

    return cues


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def chunk_vtt_cues(
    cues: list[VttCue],
    target_size: int = 6,
) -> list[CaptionChunk]:
    """Group consecutive cues into paragraph-sized chunks.

    Parameters
    ----------
    cues:
        Ordered list of VTT cues.
    target_size:
        Target number of cues per chunk.  Actual size may vary within
        ``target_size +/- 2`` to prefer sentence-ending boundaries.

    Returns
    -------
    list[CaptionChunk]
    """
    if not cues:
        return []

    chunks: list[CaptionChunk] = []
    i = 0
    n = len(cues)

    while i < n:
        # Single long cue (>100 words) becomes its own chunk
        if len(cues[i].text.split()) > 100:
            chunks.append(CaptionChunk(
                text=cues[i].text,
                start_time=cues[i].start,
                end_time=cues[i].end,
                cue_count=1,
            ))
            i += 1
            continue

        # Determine the window of acceptable chunk sizes
        min_size = max(1, target_size - 2)
        max_size = target_size + 2

        # Collect at most max_size cues, but stop at the end of the list
        end_limit = min(i + max_size, n)

        # Look for a sentence-ending boundary within the window
        best_end = None
        for j in range(i + min_size, end_limit):
            # Check if cue at position j ends a sentence -- that means j
            # should be the *last* cue in this chunk, so the slice is i..j+1.
            if _SENTENCE_END_RE.search(cues[j].text):
                best_end = j + 1
                break

        if best_end is None:
            # No sentence boundary found; use exact target_size (or whatever
            # remains).
            best_end = min(i + target_size, n)

        group = cues[i:best_end]
        chunks.append(CaptionChunk(
            text=" ".join(c.text for c in group),
            start_time=group[0].start,
            end_time=group[-1].end,
            cue_count=len(group),
        ))
        i = best_end

    return chunks


# ---------------------------------------------------------------------------
# Incremental change detection via git
# ---------------------------------------------------------------------------


def _read_build_commit(pagefind_dir: Path) -> str | None:
    """Return the commit hash stored in ``.build_commit``, or *None*."""
    marker = pagefind_dir / ".build_commit"
    if marker.is_file():
        text = marker.read_text().strip()
        return text or None
    return None


def _write_build_commit(pagefind_dir: Path, commit: str) -> None:
    """Write the current HEAD commit hash to ``.build_commit``."""
    marker = pagefind_dir / ".build_commit"
    marker.write_text(commit + "\n")


def _current_head(repo: Path) -> str | None:
    """Return the HEAD commit hash of *repo*, or *None* on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _vtt_changed_since(repo: Path, since_commit: str) -> bool:
    """Return *True* if any ``*.vtt`` file changed between *since_commit* and HEAD."""
    try:
        result = subprocess.run(
            ["git", "diff", "-z", "--name-only", since_commit, "HEAD", "--", "*.vtt"],
            capture_output=True,
            text=True,
            cwd=repo,
            check=True,
        )
        # -z separates with NUL; any non-empty output means changes
        return bool(result.stdout.strip("\0").strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If git fails (e.g. commit not in history), assume changes
        return True


# ---------------------------------------------------------------------------
# DataLad subdataset management
# ---------------------------------------------------------------------------


def _is_git_repo(path: Path) -> bool:
    """Return *True* if *path* is a git repository (has ``.git``)."""
    return (path / ".git").exists()


def _ensure_pagefind_subdataset(archive_path: Path, pagefind_dir: Path) -> bool:
    """Create ``web/pagefind/`` as a DataLad subdataset with ``cfg_text2git``.

    Uses ``datalad create`` which registers the subdataset as a git submodule
    with proper git-annex setup and ``.gitattributes`` (text in git, binary
    fragments in annex).

    Returns *True* if a sub-repository exists (created or pre-existing),
    *False* if the archive is not under version control at all.
    """
    if (pagefind_dir / ".git").exists():
        return True

    if not _is_git_repo(archive_path):
        return False

    top_ds = Dataset(str(archive_path))
    logger.info("Creating DataLad subdataset at %s", pagefind_dir)
    datalad_create(
        path=str(pagefind_dir),
        dataset=top_ds,
        cfg_proc="text2git",
        result_renderer="disabled",
    )
    return True


def _save_pagefind_subdataset(archive_path: Path) -> None:
    """Commit changes in ``web/pagefind/`` sub-repository and update the parent.

    Uses ``datalad save`` with ``recursive=True``.

    No-op if the sub-repository does not exist.
    """
    pagefind_dir = archive_path / "web" / "pagefind"
    if not (pagefind_dir / ".git").exists():
        return

    top_ds = Dataset(str(archive_path))
    logger.info("Saving caption search index via DataLad")
    top_ds.save(
        path="web/pagefind",
        message="Update caption search index",
        recursive=True,
        result_renderer="disabled",
    )


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------


def _find_vtt(video_dir: Path) -> tuple[Path | None, str]:
    """Find the best VTT file in *video_dir*.

    Returns ``(path, source)`` where *source* is ``"curated"`` or ``"original"``.
    If no VTT is found, returns ``(None, "")``.
    """
    # Look for curated first, then original -- any language
    for suffix, source in [("-curated.vtt", "curated"), (".vtt", "original")]:
        # Curated: video.en-curated.vtt  /  Original: video.en.vtt
        # We need to distinguish from curated when looking for original
        for candidate in sorted(video_dir.glob(f"video.*{suffix}")):
            name = candidate.name
            if source == "original" and "-curated.vtt" in name:
                continue
            return candidate, source
    return None, ""


def _read_metadata(video_dir: Path) -> dict | None:
    """Read and return the ``metadata.json`` from *video_dir*, or *None*."""
    meta_path = video_dir / "metadata.json"
    if not meta_path.is_file():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Skipping %s: %s", meta_path, exc)
        return None


def _iter_video_dirs(archive_path: Path, channels: list[str] | None = None):
    """Yield video directories under *archive_path*.

    For single-channel archives the layout is ``videos/YYYY/MM/VIDEO_DIR/``.
    For multi-channel archives each channel has its own subtree.
    """
    if channels:
        roots = [archive_path / ch / "videos" for ch in channels]
    else:
        # Try multi-channel first: directories containing a ``videos/`` subdir
        candidate_roots = []
        multi_channel_root = archive_path
        for child in sorted(multi_channel_root.iterdir()):
            if child.is_dir() and (child / "videos").is_dir():
                candidate_roots.append(child / "videos")

        if not candidate_roots:
            # Single-channel layout
            candidate_roots = [archive_path / "videos"]

        roots = candidate_roots

    for root in roots:
        if not root.is_dir():
            continue
        # Walk year/month/video_dir
        for video_dir in sorted(root.rglob("metadata.json")):
            yield video_dir.parent


async def _create_pagefind_service():
    """Create a PagefindService with stderr discarded.

    The upstream pagefind library merges stderr into stdout
    (``stderr=asyncio.subprocess.STDOUT``) which can corrupt the
    base64-over-comma IPC protocol.  We redirect stderr to ``DEVNULL``
    to eliminate any risk of pipe interlocking between stdout and stderr.

    The polling task is wrapped in an error guard so that exceptions
    (``IncompleteReadError``, JSON decode failures, etc.) cancel all
    pending futures instead of silently dying and leaving callers stuck.
    """
    import os

    from pagefind.service import PagefindService

    service = PagefindService()  # sets _bin, _loop, _responses

    service._backend = await asyncio.create_subprocess_exec(
        service._bin,
        "--service",
        cwd=os.getcwd(),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        limit=2**21,
    )

    # Wrap the poller so exceptions are surfaced, not swallowed
    async def _guarded_poll():
        try:
            await service._wait_for_responses()
        except asyncio.IncompleteReadError:
            logger.debug("Pagefind process closed stdout (normal shutdown)")
        except Exception:
            logger.exception("Pagefind response poller crashed")
            for future in service._responses.values():
                if not future.done():
                    future.cancel()

    service._poll_task = service._loop.create_task(_guarded_poll())
    return service


async def _pagefind_write_files(service, index, output_path: str) -> None:
    """Send ``WriteFiles`` to the pagefind subprocess and read the response.

    The upstream ``PagefindIndex.write_files()`` relies on a background
    polling task (``_wait_for_responses``) that silently dies on parse
    errors, leaving the caller hanging forever.  This helper cancels the
    polling task and performs the IPC exchange directly, giving us full
    control over timeouts and error reporting.
    """
    import base64 as _b64

    # Stop the polling task — we'll read the response ourselves
    service._poll_task.cancel()
    try:
        await service._poll_task
    except (asyncio.CancelledError, Exception):
        pass

    # Send WriteFiles request
    service._message_id += 1
    req = {
        "message_id": service._message_id,
        "payload": {
            "type": "WriteFiles",
            "index_id": index._index_id,
            "output_path": output_path,
        },
    }
    encoded = _b64.b64encode(json.dumps(req).encode("utf-8"))
    assert service._backend.stdin is not None
    service._backend.stdin.write(encoded + b",")
    await service._backend.stdin.drain()
    logger.info("WriteFiles request sent, waiting for pagefind to build index...")

    # Read response directly — no intermediary polling task
    assert service._backend.stdout is not None
    try:
        raw = await asyncio.wait_for(
            service._backend.stdout.readuntil(b","),
            timeout=300,
        )
    except asyncio.TimeoutError:
        rc = service._backend.returncode
        if rc is not None:
            raise RuntimeError(
                f"Pagefind process exited with code {rc} during WriteFiles"
            ) from None
        raise TimeoutError(
            "Pagefind WriteFiles timed out after 300s — "
            f"subprocess (PID {service._backend.pid}) appears stuck"
        ) from None

    resp = json.loads(_b64.b64decode(raw[:-1]))
    payload = resp.get("payload", {})
    resp_type = payload.get("type")
    if resp_type == "Error":
        raise RuntimeError(
            f"Pagefind WriteFiles failed: {payload.get('message')}"
        )
    if resp_type != "WriteFiles":
        raise RuntimeError(f"Unexpected pagefind response type: {resp_type}")


async def build_caption_index(
    archive_path: Path,
    channels: list[str] | None = None,
    force: bool = False,
) -> IndexStats:
    """Build a Pagefind search index from caption VTT files.

    Parameters
    ----------
    archive_path:
        Root of the annextube archive.
    channels:
        Optional list of channel directory names to index (multi-channel).
        *None* means discover automatically.
    force:
        If *True*, rebuild the full index even when no VTT files changed.

    Returns
    -------
    IndexStats
        Summary of the build.
    """
    if PagefindIndex is None:
        raise ImportError(
            "pagefind package required for search index. "
            "Install with: pip install 'annextube[search]'"
        )

    pagefind_dir = archive_path / "web" / "pagefind"
    stats = IndexStats()

    # --- Incremental: skip if nothing changed --------------------------------
    if not force:
        last_commit = _read_build_commit(pagefind_dir)
        if last_commit is not None:
            head = _current_head(archive_path)
            if head and last_commit == head:
                logger.info(
                    "Search index up to date (no new commits since %s)",
                    head[:8],
                )
                return stats
            if head and not _vtt_changed_since(archive_path, last_commit):
                logger.info(
                    "Search index up to date (no caption changes since %s)",
                    last_commit[:8],
                )
                return stats

    # --- Ensure sub-repository exists (DataLad or plain git) -----------------
    logger.info("Checking pagefind sub-repository status")
    is_subdataset = _ensure_pagefind_subdataset(archive_path, pagefind_dir)

    # --- Build index ---------------------------------------------------------
    pagefind_dir.mkdir(parents=True, exist_ok=True)

    logger.debug("Initializing Pagefind index")

    config = IndexConfig(root_selector="main", output_path=str(pagefind_dir))
    logger.info("Starting pagefind subprocess...")
    service = await _create_pagefind_service()
    try:
        index = await service.create_index(config)
        logger.info("Pagefind index initialized, scanning video directories")
        video_count = 0
        for video_dir in _iter_video_dirs(archive_path, channels):
            video_count += 1
            logger.info("Indexing video %d: %s", video_count, video_dir.name)
            meta = _read_metadata(video_dir)
            if meta is None:
                stats.videos_skipped += 1
                continue

            vtt_path, source = _find_vtt(video_dir)
            if vtt_path is None:
                stats.videos_skipped += 1
                continue

            video_id = meta.get("video_id", "")
            title = meta.get("title", "")
            channel_name = meta.get("channel_name", meta.get("uploader", ""))
            upload_date = meta.get("published_at", "")[:10]  # YYYY-MM-DD
            year = upload_date[:4] if upload_date else ""

            # Detect language from filename: video.en.vtt or video.en-curated.vtt
            lang = "en"
            vtt_stem = vtt_path.stem  # e.g. "video.en-curated" or "video.en"
            parts = vtt_stem.split(".")
            if len(parts) >= 2:
                lang_part = parts[-1]  # e.g. "en-curated" or "en"
                lang = lang_part.split("-")[0]  # strip "-curated"

            # Skip annexed VTT files whose content isn't available locally
            if vtt_path.is_symlink() and not vtt_path.exists():
                logger.debug("Skipping %s (annexed, content not available)", vtt_path)
                stats.videos_skipped += 1
                continue

            try:
                cues = parse_vtt(vtt_path)
            except OSError as exc:
                logger.warning("Skipping %s: %s", vtt_path, exc)
                stats.videos_skipped += 1
                continue
            if not cues:
                stats.videos_skipped += 1
                continue

            chunks = chunk_vtt_cues(cues)
            if source == "curated":
                stats.videos_curated += 1
            else:
                stats.videos_original += 1
            stats.videos_indexed += 1
            logger.debug(
                "  Video %s: %d cues -> %d chunks (%s)",
                video_id, len(cues), len(chunks), source,
            )

            for chunk in chunks:
                start_seconds = int(chunk.start_time)
                url = f"#/video/{video_id}?t={start_seconds}"

                await index.add_custom_record(
                    url=url,
                    content=chunk.text,
                    language=lang,
                    meta={
                        "title": title,
                        "video_id": video_id,
                        "channel_name": channel_name,
                        "upload_date": upload_date,
                        "timestamp": str(start_seconds),
                    },
                    filters={
                        "channel_name": [channel_name],
                        "year": [year],
                        "language": [lang],
                    },
                    sort={
                        "date": upload_date,
                    },
                )
                stats.chunks_created += 1

        logger.info(
            "Indexed %d videos, %d chunks — writing index files...",
            stats.videos_indexed, stats.chunks_created,
        )
        await _pagefind_write_files(service, index, str(pagefind_dir))
        logger.info("Index files written successfully")
    finally:
        await service.close()

    # Compute index size
    total = 0
    for f in pagefind_dir.rglob("*"):
        if f.is_file() and f.name != ".build_commit":
            total += f.stat().st_size
    stats.index_size_bytes = total

    # Record build commit for incremental
    head = _current_head(archive_path)
    if head:
        _write_build_commit(pagefind_dir, head)

    # --- Commit within sub-repository and update parent pointer --------------
    if is_subdataset:
        _save_pagefind_subdataset(archive_path)

    logger.info(
        "Caption search index built: %d videos (%d curated, %d original), "
        "%d chunks, %.1f MB",
        stats.videos_indexed,
        stats.videos_curated,
        stats.videos_original,
        stats.chunks_created,
        stats.index_size_bytes / (1024 * 1024),
    )

    return stats
