# PRD: Full-Text Caption Search via Pagefind

**Status:** Draft
**Author:** PRD Generator
**Date:** 2026-03-03
**Stakeholders:** annextube maintainers, archive operators, researchers

---

## Context and Why Now

annextube archives YouTube channels into git-annex repositories, preserving video files, metadata, captions, comments, and thumbnails. The caption curation pipeline (`caption_curator.py`) already produces high-quality, cleaned-up `.curated.vtt` files from raw ASR captions -- removing filler words, fixing glossary terms, restoring proper sentence boundaries, and mapping word-level timestamps.

Today, users can search video titles, tags, and descriptions via fuse.js in the Svelte frontend, but **they cannot search inside what was actually said in the videos**. For research and archival use cases, the spoken content is often the most valuable part. A researcher looking for where "reproducibility crisis" was discussed across 500 archived lecture videos currently has no way to find it without manually watching each one.

**Why now:**
- The curated caption pipeline shipped and is stable -- clean text is available for indexing
- The Svelte frontend already has per-video caption browsing with search, highlight, and timestamp seek (CaptionBrowser.svelte) -- the UI patterns exist
- Pagefind (by CloudCannon) reached maturity with a native Python API on PyPI, enabling build-time indexing without a Node dependency
- The frontend runs over HTTP (not file://), which is required for Pagefind's chunked index loading

---

## Users and Jobs To Be Done

**Primary user: Archive operator / researcher**
- "When I search for a term, I want to find not just which video mentions it, but *where* in the video -- so I can jump straight to that moment."
- "When I click a caption search result, I want to land on the video page with the transcript already filtered and the player seeked to the match."

**Secondary user: Archive consumer (viewer)**
- "I remember someone said something about 'git-annex computed' in one of these talks, but I don't remember which one. I want to type it and find it."

**Tertiary user: Archive maintainer**
- "When I add new videos and run `generate-web`, the search index should update without manual steps."

---

## Business Goals and Success Metrics

**Goals:**
- Enable full-text search across all curated captions in an archive
- Deliver sub-second search results with minimal bandwidth overhead
- Maintain the zero-infrastructure, static-file deployment model

**Leading metrics:**
- Index build time under 30 seconds for a 500-video archive
- Search query round-trip under 200ms (index chunk load + search)
- Network payload per query under 300KB (Pagefind's design target)

**Lagging metrics:**
- Reduction in time-to-find for known-content queries (manual benchmark: search vs. browse)
- User engagement: percentage of sessions using caption search (if analytics are added later)

---

## Functional Requirements

### FR-1: Pagefind Index Builder (Python)

Build a Pagefind search index from curated VTT captions during `generate-web`.

**Acceptance criteria:**
- A new module `annextube/services/search_index.py` uses the `pagefind` PyPI package's async Python API (`PagefindIndex`, `add_custom_record()`)
- For each video directory, the builder looks for caption VTT files with this priority:
  1. If `video.{lang}-curated.vtt` exists → index the **curated** version (preferred: cleaned-up text, proper sentences)
  2. If only `video.{lang}.vtt` exists (no curated version) → index the **original** VTT as fallback
- This ensures all captioned videos are searchable, while curated captions provide better search quality where available
- The selected VTT (curated or original) is parsed into cues, grouped into paragraph-sized chunks (see FR-2), and each chunk is added as a custom record via `add_custom_record()`
- Each record includes:
  - `url`: deep-link to the video page with timestamp and query passthrough (see FR-5)
  - `content`: the chunk's plain text (concatenated cue texts)
  - `language`: from the VTT filename (e.g., `"en"`). **Which languages to index is configurable** via `annextube.conf` (e.g., `search_languages = en,es`). Default: all available caption languages.
  - `meta`: `title` (video title), `video_id`, `channel_name`, `upload_date` (YYYY-MM-DD), `timestamp` (start time in seconds of the first cue in the chunk), `thumbnail_url`
  - `filters`: `channel_name` (for per-channel filtering), `year` (extracted from `upload_date`), `language`
  - `sort`: `date` (upload_date as sortable string)
- The index is written to `{archive_root}/web/pagefind/`
- Search indexing is an opt-in feature (similar to caption curation). If indexing is enabled and the `pagefind` package is not installed, `generate-web` must **error out** (not silently skip). If indexing is not enabled, no pagefind dependency is needed.
- The builder reports: number of videos indexed, number of chunks created, total index size

### FR-2: VTT Chunking Strategy

Group consecutive VTT cues into paragraph-sized chunks for indexing.

**Acceptance criteria:**
- Cues are grouped into chunks of approximately N consecutive cues (~30-60 seconds of speech, ~50-120 words). Default N=5-8.
- **Chunk size is configurable** via `annextube.conf` (e.g., `search_chunk_cues = 6`) to allow per-archive tuning
- Each chunk records the start timestamp of its first cue and the end timestamp of its last cue
- Chunk boundaries prefer natural sentence endings (cue text ending with `.`, `!`, `?`) when they fall within the target size window
- Single-cue chunks are allowed when a cue is unusually long (>100 words)
- The chunking logic is a pure function: `chunk_vtt_cues(cues: list[VttCue], target_size: int) -> list[CaptionChunk]` in the search index module, testable in isolation
- Each `CaptionChunk` has: `text` (concatenated cue text), `start_time` (float seconds), `end_time` (float seconds), `cue_count` (int)

**Rationale:** One record per cue would produce too many results for the same passage. One record per video would lose timestamp precision. Paragraph-sized chunks (~40-80 words) give Pagefind enough context for meaningful excerpts with `<mark>` highlights while preserving timestamp granularity to within ~30-60 seconds.

### FR-3: Integration with `generate-web` Command

Wire the index builder into the existing `generate-web` CLI command.

**Acceptance criteria:**
- After deploying the frontend and exporting metadata, `generate-web` calls the search index builder
- Search index building is opt-in, controlled by a CLI flag `--search-index` (off by default) or a config option
- Progress is displayed: `Building caption search index... [ok] 423 videos, 8,291 chunks, 4.2 MB`
- If indexing is enabled and the `pagefind` Python package is not installed, `generate-web` exits with a clear error: `Error: pagefind package required for search index. Install with: pip install 'annextube[search]'`
- The index output goes to `{archive_root}/web/pagefind/`, managed as a **DataLad subdataset** (git submodule) to isolate the ~10,000+ derived index files from the main repository
- On first run, the builder creates the subdataset via `datalad create(dataset=top_ds, path="web/pagefind", cfg_proc="text2git")`
- After writing index files, saves via `top_ds.save(path="web/pagefind", message=..., recursive=True)` — handles both subdataset commit and parent pointer update
- Multi-channel archives: iterate all channel directories and build a single unified index within the same subdataset

### FR-4: Frontend Pagefind Integration

Load Pagefind in the Svelte frontend and display search results.

**Acceptance criteria:**
- The existing search bar in FilterPanel.svelte gains a toggle or tab to switch between "Metadata" (existing fuse.js) and "Captions" (Pagefind)
- When "Captions" mode is active, typing a query calls `pagefind.search(query, { filters })` and displays results
- **Results are grouped by video**: if a query matches multiple chunks in the same video, show one result per video with the best-matching excerpt and a "N matches" badge. Clicking the result navigates to the first (earliest) matching chunk's timestamp.
- Each result shows:
  - Video title (from `meta.title`)
  - Channel name (from `meta.channel_name`)
  - Upload date (from `meta.upload_date`)
  - Best excerpt with `<mark>` highlights (from Pagefind's built-in excerpt)
  - Timestamp badge of the first match (from `meta.timestamp`, formatted as `MM:SS` or `HH:MM:SS`)
  - "N matches" badge when multiple chunks matched (expandable to show all matching excerpts/timestamps)
- Clicking a result navigates to the video page using the deep-link URL of the first matching chunk
- Pagefind JS is loaded dynamically from `/web/pagefind/pagefind.js` only when the user activates caption search (lazy load)
- If the pagefind index does not exist (404 on pagefind.js), the caption search toggle is hidden
- Results support filtering by channel (in multi-channel mode) using Pagefind's filter API
- Results are paginated: load first 10, then "Show more" loads the next 10 (using Pagefind's lazy `data()` pattern)

### FR-5: Deep-Link URL Scheme

Define a URL scheme that carries video ID, timestamp, and search query through navigation.

**Acceptance criteria:**
- Pagefind record URLs use the format:
  - Single-channel: `#/video/{video_id}?t={seconds}&q={query}`
  - Multi-channel: `#/channel/{channel_dir}/video/{video_id}?t={seconds}&q={query}`
- The `t` parameter is the integer start time (seconds) of the matching chunk
- The `q` parameter is the original search query (URL-encoded)
- VideoDetail.svelte already parses `t` and `q` from the hash URL (confirmed in current code: `urlParams.t`, `urlParams.q`) -- this is reused directly
- When navigating from a caption search result, the video page:
  1. Opens with the CaptionBrowser visible (transcript panel)
  2. Passes `q` to the CaptionBrowser as `initialSearchQuery` (already supported)
  3. Seeks the video player to time `t` via `initialTime` (already supported)
  4. The CaptionBrowser highlights all matching cues and scrolls to the first match

### FR-6: CaptionBrowser Query Passthrough

Ensure the existing CaptionBrowser component works correctly with the search query passed from a caption search result.

**Acceptance criteria:**
- This is largely already implemented. VideoDetail.svelte reads `q` from the URL and passes it as `initialSearchQuery` to CaptionBrowser. CaptionBrowser uses it to populate the search input and highlight matching cues.
- Verify that when `initialSearchQuery` is set, the CaptionBrowser:
  1. Populates the search input with the query
  2. Highlights all matching cues
  3. Scrolls to the first matching cue near the timestamp `t`
  4. Sets `filterMode` to false by default (show all cues, dim non-matches) so the user sees context
- If the curated caption language is available, auto-select it (CaptionBrowser already prefers curated variants via `pickPreferredLang()`)
- No changes expected to CaptionBrowser.svelte for this requirement

### FR-7: Git-Based Incremental Indexing

Only re-index captions that changed since the last index build, using git to detect changes.

**Acceptance criteria:**
- The index builder records a marker (e.g., the git commit hash at build time) in `web/pagefind/.build_commit`
- On subsequent runs, it uses `git diff --name-only <last_commit> HEAD -- '*.vtt'` to find changed/added/removed VTT files (both curated and original)
- Only changed captions are re-processed: new chunks are built and the index is updated
- If no VTT files changed since the last build commit, skip indexing entirely with a message: `Search index up to date (no caption changes since {commit_short})`
- A `--force-reindex` flag triggers a full rebuild regardless of git state
- If the `.build_commit` file is missing or the recorded commit is no longer in history, fall back to a full rebuild
- **Note:** Pagefind does not natively support incremental index updates. The builder must still call Pagefind's API to produce the full index, but it can skip the VTT parsing/chunking for unchanged videos by caching the intermediate chunk data (e.g., as JSON alongside the index). The optimization is in avoiding redundant VTT I/O and parsing, while the final Pagefind index write is always a full generation.

---

## Non-Functional Requirements

### Performance

- **Index build:** Under 30 seconds for 500 videos (~2,500 curated VTT files at 5 languages). Pagefind's Rust backend handles the heavy lifting; the Python wrapper adds records via IPC.
- **Search latency:** Under 200ms for a query on a 500-video index (Pagefind's chunked architecture loads only the relevant index chunks).
- **Initial load impact:** Zero. Pagefind JS is loaded on-demand only when the user activates caption search. The main page load is unaffected.

### Scale

- **Target:** Archives up to 10,000 videos with curated captions.
- **Estimated index sizes** (based on Pagefind's published benchmarks of ~300KB per 10,000 pages):
  - 100 videos, ~5 chunks each = 500 records: ~50-100KB index
  - 1,000 videos, ~20 chunks each = 20,000 records: ~500KB-1MB index
  - 10,000 videos, ~20 chunks each = 200,000 records: ~5-10MB total index (only ~100-300KB loaded per query due to chunking)
- Source: [Pagefind homepage](https://pagefind.app/) -- "full-text search on a 10,000 page site with a total network payload under 300kB"

### SLOs / SLAs

- Not applicable (self-hosted static tool, no service uptime commitments).
- **Build-time guarantee:** If search indexing is not enabled, `generate-web` works without pagefind. If search indexing IS enabled, missing pagefind is a hard error (fail-fast, not best-effort).

### Privacy

- The search index is built from locally stored curated captions. No data leaves the archive.
- The index files are static and deployed alongside the frontend. No external search service is contacted.
- Pagefind JS is loaded from the local `/web/pagefind/` directory, not from a CDN.

### Security

- No new attack surface. The index is static files served by the same HTTP server as the frontend.
- The Pagefind Python package executes a pre-built Rust binary. The `pagefind` PyPI package bundles platform-specific binaries; this is consistent with other tools in the dependency chain (e.g., deno, yt-dlp).

### Observability

- Build-time logging: number of videos scanned, number indexed (curated vs original fallback), number skipped (no captions), chunk count, total index size.
- Frontend: console.log when Pagefind loads successfully or fails to load (404).
- No runtime metrics (static site, no backend).

---

## Scope

### In scope

- Pagefind index builder as a Python service module
- VTT chunking logic with tests
- Integration into `generate-web` command
- Frontend: caption search mode in the search bar with Pagefind JS
- Deep-link URL scheme for search result navigation
- Single-channel and multi-channel index support
- `pagefind` as an optional dependency (in a new `[search]` extras group)

### Out of scope

- **Full-text search of non-caption content** (descriptions, comments). Could be added later by indexing additional `add_custom_record()` calls.
- **Real-time / incremental indexing** without running `generate-web`. Pagefind indexes are built at generation time only.
- **file:// protocol support** for caption search. Pagefind requires HTTP to load chunked index files. The frontend already targets HTTP deployment.
- **Search across multiple separate archives.** Each archive has its own index.
- **Stemming / language-specific analysis customization.** Pagefind handles this automatically based on the `language` parameter.
- **Audio search / speech-to-text at query time.** Captions must already exist.
- **Search result ranking tuning.** Use Pagefind's default BM25 ranking initially.
- **Dedicated cross-channel search UI.** Multi-channel uses Pagefind filters; a dedicated aggregated search page is a follow-up.

---

## Rollout Plan

### Phase 1: Index Builder and CLI Integration (Python-side)

1. Add `pagefind` to `[project.optional-dependencies]` as a new `search` extras group
2. Implement `annextube/services/search_index.py`:
   - `build_caption_index(archive_path, output_path, channels=None)` async function
   - `parse_vtt(vtt_path)` to extract cues from VTT (curated or original)
   - `chunk_vtt_cues(cues)` to group cues into paragraph chunks
   - Uses `PagefindIndex` context manager and `add_custom_record()` for each chunk
3. Wire into `generate_web.py`: call `build_caption_index()` after `deploy_frontend()`
4. Add `--search-index` opt-in flag and config option
5. Unit tests for VTT parsing, chunking, record construction (mock Pagefind API)
6. Integration test: build index from test fixtures, verify output files exist

### Phase 2: Frontend Search UI

1. Add Pagefind JS loading utility in `frontend/src/services/pagefind.ts`:
   - `initPagefind()` -- lazy-load `/pagefind/pagefind.js`
   - `searchCaptions(query, filters)` -- wrapper around `pagefind.search()`
   - `loadResult(result)` -- wrapper around `result.data()`
2. Create `frontend/src/components/CaptionSearchResults.svelte`:
   - Displays paginated search results with excerpts, timestamps, video links
   - "Show more" button for pagination
3. Modify `FilterPanel.svelte` or create adjacent `SearchMode` toggle:
   - "Videos" (existing fuse.js) vs "Captions" (Pagefind) mode
   - Caption mode shown only when pagefind index exists
4. Wire deep-link navigation: clicking a result calls `router.navigate('video', {...})` with query params
5. Frontend unit tests for the search results component
6. E2E test: search for a term, verify result appears, click through to video page with correct timestamp and query

### Phase 3: Polish and Multi-Channel

1. Multi-channel index: single unified Pagefind index across all channels, with `channel_name` filter
2. Channel-scoped search: when viewing a single channel, automatically apply the channel filter
3. Year filter in search UI
4. Keyboard shortcuts: `/` to focus search, `Tab` to toggle search mode
5. "No results" state with helpful messaging
6. Performance testing with large archives (1,000+ videos)

### Guardrails

- **Opt-in:** Search indexing is off by default. Enabled via `--search-index` flag or config option. If enabled without pagefind installed, it's a hard error.
- **Graceful frontend degradation:** If the index files are absent at runtime, the frontend hides the caption search toggle. No error shown to end users.
- **Kill switch:** Remove `web/pagefind/` subdataset to disable caption search instantly. No other component depends on it.
- **Rollback:** Since the index is regenerated on each `generate-web` run, there is no migration concern. Remove the code and the subdataset.

---

## Risks and Open Questions

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pagefind PyPI package drops support or becomes unmaintained | Low | High | Pagefind is backed by CloudCannon (commercial company). The index format is stable. The Python wrapper is thin; worst case, call the Rust binary directly. |
| Index size grows too large for very large archives (50,000+ videos) | Low | Medium | Pagefind's chunked loading means users only download ~100-300KB per query regardless of total index size. Disk usage may be the concern; monitor and document. |
| Build time becomes slow for very large archives | Medium | Low | Pagefind's Rust backend is fast. For 10,000+ video archives, consider parallelizing VTT parsing. Git-based incremental indexing (FR-7) avoids redundant work. |
| Curated VTT parsing diverges from caption_curator output format | Low | Medium | Use the same `parse_timestamp()` / VTT parsing logic already in the codebase. Add a contract test that parses real curated VTT output. |

### Resolved Decisions

1. **Chunk size:** Configurable via `annextube.conf` (`search_chunk_cues`). Default 5-8 cues (~30-60s). Operators can tune per-archive.

2. **Languages:** Configurable language list via `annextube.conf` (`search_languages`). Default: all available caption languages. Each language indexed as separate records with appropriate `language` parameter.

3. **Re-indexing:** Git-based incremental. Use `git diff` to detect changed `*.vtt` (curated or original) since last build commit. If no changes, skip entirely. `--force-reindex` for full rebuild. See FR-7. Pagefind's content-addressed fragment filenames mean unchanged videos produce identical output files — only truly changed content generates new fragments.

4. **Result deduplication:** Group by video. One result per video with "N matches" badge. First (earliest timestamp) match is the primary excerpt. Expandable to show all matching chunks.

5. **Pagefind version pinning:** `pagefind>=1.0,<2.0`. The API surface (`add_custom_record`, `write_files`) is stable since 1.0.

---

## Technical Reference

### File Layout After Build

```
archive_root/
  web/
    index.html
    assets/
    pagefind/              # NEW: Pagefind search index
      pagefind.js          # ~100KB, static (changes only on pagefind upgrade)
      pagefind-entry.json  # Entry point metadata
      pagefind.en_xxxx.pf_meta  # Per-language metadata, small
      wasm.en.pagefind     # WASM search engine, static
      fragment/             # One file per indexed chunk, content-addressed
        en_0933ef4.pf_fragment  # ~1-10 KB each
        en_100be25.pf_fragment
        ...
      index/                # Search index split into chunks
        en_22c87b9.pf_index    # ~40 KB each
        en_26afa46.pf_index
        ...
  videos/
    2026/01/My-Video_abc123/
      video.mkv
      video.en.vtt            # Original ASR caption
      video.en-curated.vtt    # Curated caption (preferred for indexing)
      metadata.json
      captions.tsv
```

#### Git-Friendliness of the Index

Pagefind's output is inherently modular and git-friendly:

- **Fragment files are content-addressed** (since Pagefind v1.3.0): if a caption chunk's content hasn't changed between builds, its fragment filename stays identical. Adding new videos creates new fragment files without modifying existing ones.
- **One fragment per record** (~1-10 KB): each caption chunk gets its own `.pf_fragment` file. A 500-video archive with ~20 chunks/video ≈ 10,000 small files, not one monolith.
- **Index chunks are small** (~40 KB each): the inverted index is split across multiple files. Adding new terms may modify some chunks, but the changes are distributed.
- **Static assets** (`pagefind.js`, `wasm.*.pagefind`) only change on Pagefind version upgrades.

**Impact of adding 10 new videos** to a 500-video archive:
- ~200 new fragment files created (10 videos × 20 chunks)
- Existing ~10,000 fragment files: **unchanged** (content-addressed)
- Index chunks: some modified to include new terms (~40 KB each)
- Metadata file: updated (small)

#### DataLad Subdataset Isolation

Despite being modular, the index can easily reach ~10,000+ files for a medium archive. These files are derived artifacts (not primary data) and not useful to typical dataset consumers who just want the videos and metadata. To avoid polluting the main repository:

- **`web/pagefind/` is a DataLad subdataset** (git submodule). The index builder creates it on first run or operates within the existing one.
- Users who don't need search simply never `datalad get web/pagefind/` — the subdataset is registered but not fetched by default.
- Adding 200 new fragments shows as a single submodule pointer update in the parent's `git diff`.
- This follows the standard DataLad pattern for derived/generated content.

**DataLad API usage** (datalad is already a dependency):

```python
from datalad.api import create, save, Dataset

top_ds = Dataset(archive_path)

# First run: create subdataset with text2git config
# (text files like pagefind.js/JSON in git, binary .pf_* files in annex)
if not (archive_path / "web" / "pagefind" / ".git").exists():
    create(
        path=str(archive_path / "web" / "pagefind"),
        dataset=top_ds,
        cfg_proc="text2git",
    )

# ... write index files into web/pagefind/ ...

# Save everything: commits within subdataset, then updates
# submodule pointer in parent — single call handles both levels
top_ds.save(
    path="web/pagefind",
    message="Update caption search index",
    recursive=True,
)
```

**`text2git` config procedure** ensures:
- Text files (`pagefind.js`, `pagefind-entry.json`, `*.css`) are stored directly in git (small, diffable)
- Binary files (`.pf_fragment`, `.pf_index`, `.pf_meta`, `.pagefind` WASM) go into git-annex (content-addressed, deduplicated)

**Implications for the index builder:**
- Must detect whether `web/pagefind/` subdataset already exists before calling `create()`
- Uses `top_ds.save("web/pagefind", recursive=True)` after writing — handles both subdataset commit and parent pointer update in one call
- `--force-reindex` should clean stale fragments before rebuilding (remove files no longer in the new index output)

### Pagefind Record Structure (per chunk)

```python
await index.add_custom_record(
    url="#/video/abc123?t=142",
    content="So the key insight about reproducibility is that you need "
            "to capture not just the code but also the environment, the "
            "data, and the exact sequence of commands that were run.",
    language="en",
    meta={
        "title": "Reproducibility in Neuroimaging",
        "video_id": "abc123",
        "channel_name": "NeuroDataScience",
        "upload_date": "2025-06-15",
        "timestamp": "142",
        "thumbnail_url": "videos/2025/06/Reproducibility_abc123/thumbnail.jpg",
    },
    filters={
        "channel_name": ["NeuroDataScience"],
        "year": ["2025"],
    },
    sort={
        "date": "2025-06-15",
    },
)
```

**Note on `url` field:** The URL stored in the index is `#/video/{video_id}?t={seconds}` — no `q=` param. The frontend appends `&q={query}` dynamically when the user clicks a search result, since the query is not known at index time.

### Curated VTT Format (for reference)

```
WEBVTT
Kind: captions
Language: en

00:00:03.600 --> 00:00:06.869
So<00:00:03.960><c> today</c><00:00:04.320><c> we're</c><00:00:04.560><c> going</c>

00:00:06.869 --> 00:00:11.270
to<00:00:07.200><c> talk</c><00:00:07.560><c> about</c><00:00:07.920><c> reproducibility.</c>
```

The index builder parses this using the existing `vtt-parser.ts` logic (ported to Python) or the already-available `CaptionCurator.parse_youtube_vtt()` which handles the `<c>` tag format. Since curated VTTs also use this format (with word-level `<c>` tags), the existing Python VTT parser works directly.

### Dependency Addition

```toml
# In pyproject.toml [project.optional-dependencies]
search = [
    "pagefind>=1.0,<2.0",
]
devel = [
    "annextube[test]",
    "annextube[search]",   # Add search to devel
    ...
]
```

---

## Implementation TODO

Ordered steps. Each step should be a single commit (or logical unit).

### Phase 1: Python Index Builder

**TODO-1: Add `pagefind` optional dependency**
- Add `search = ["pagefind>=1.0,<2.0"]` to `[project.optional-dependencies]` in `pyproject.toml`
- Add `"annextube[search]"` to `devel` extras
- Run `uv pip install -e ".[devel]"` to verify resolution
- Files: `pyproject.toml`

**TODO-2: Implement VTT parsing and chunking logic**
- Create `annextube/services/search_index.py`
- Implement `parse_vtt(vtt_path: Path) -> list[VttCue]` — reuse/adapt the VTT parsing from `CaptionCurator.parse_youtube_vtt()` which already handles `<c>` word-level tags. Extract plain text + cue timestamps.
- Implement `chunk_vtt_cues(cues: list[VttCue], target_size: int = 6) -> list[CaptionChunk]` — pure function, groups cues into chunks preferring sentence-ending boundaries
- Data classes: `VttCue(text: str, start: float, end: float)`, `CaptionChunk(text: str, start_time: float, end_time: float, cue_count: int)`
- Write unit tests in `tests/unit/test_search_index.py`:
  - Chunking with exact target size
  - Chunking prefers sentence boundaries
  - Single long cue becomes its own chunk
  - Empty input returns empty list
  - Parsing curated VTT with `<c>` tags extracts plain text + timestamps
  - Parsing original VTT (same format) also works
- Files: `annextube/services/search_index.py`, `tests/unit/test_search_index.py`

**TODO-3: Implement Pagefind index builder**
- In `search_index.py`, implement `async build_caption_index(archive_path: Path, channels: list[str] | None = None, force: bool = False) -> IndexStats`
- VTT selection priority: curated → original fallback (per FR-1)
- Language filtering via config (`search_languages`)
- Chunk size via config (`search_chunk_cues`)
- Each chunk → `PagefindIndex.add_custom_record()` with proper url/content/meta/filters/sort
- URL format: `#/video/{video_id}?t={seconds}` (no `q=`)
- Read video metadata from `metadata.json` for title, channel_name, upload_date, thumbnail
- Report stats: videos indexed (curated vs original), chunks, total index size
- Git-based incremental: check `.build_commit` marker, `git diff --name-only <commit> HEAD -- '*.vtt'`, skip if nothing changed
- Write `.build_commit` after successful build
- `force=True` bypasses incremental check
- Unit tests (mock `PagefindIndex`):
  - Curated VTT preferred over original when both exist
  - Original VTT used as fallback when no curated
  - Videos with no VTT at all are skipped
  - Language filtering respects config
  - Incremental skip when no VTT changes
  - Force rebuild ignores `.build_commit`
- Files: `annextube/services/search_index.py`, `tests/unit/test_search_index.py`

**TODO-4: DataLad subdataset management**
- In `search_index.py`, add helper to ensure `web/pagefind/` subdataset exists:
  ```python
  from datalad.api import create, Dataset
  top_ds = Dataset(archive_path)
  if not (archive_path / "web" / "pagefind" / ".git").exists():
      create(path=str(archive_path / "web" / "pagefind"),
             dataset=top_ds, cfg_proc="text2git")
  ```
- After writing index files, save:
  ```python
  top_ds.save(path="web/pagefind", message="Update caption search index",
              recursive=True)
  ```
- On `--force-reindex`, clean stale fragment/index files before rebuilding (remove files not in new Pagefind output)
- Files: `annextube/services/search_index.py`

**TODO-5: Wire into `generate-web` CLI**
- Add `--search-index` flag (opt-in, default False) to `generate_web.py`
- Add config option support (read from `annextube.conf`)
- If enabled: import and call `build_caption_index()` after `deploy_frontend()`
- If enabled and `pagefind` not installed: hard error with install instructions
- Add `--force-reindex` flag (passed through to builder)
- Display progress: `Building caption search index... [ok] N videos, N chunks, N MB`
- Files: `annextube/cli/generate_web.py`

**TODO-6: Integration test with real Pagefind**
- Test that builds an index from VTT fixtures and verifies:
  - `web/pagefind/` directory created with expected file types
  - Fragment files exist for each indexed chunk
  - Index files exist
  - `pagefind.js` present
  - `.build_commit` file written
- Mark as `@pytest.mark.slow` (requires pagefind binary)
- Files: `tests/integration/test_search_index.py`

### Phase 2: Frontend Search UI

**TODO-7: Pagefind JS service wrapper**
- Create `frontend/src/services/pagefind.ts`:
  - `initPagefind()` — lazy-load `/pagefind/pagefind.js`, return null if 404
  - `searchCaptions(query, filters?)` — wrapper returning grouped-by-video results
  - `loadResult(result)` — wrapper around `result.data()` for lazy loading
  - Grouping logic: collect results by `meta.video_id`, keep first (earliest timestamp) as primary, count matches
- Type definitions for Pagefind result shape
- Files: `frontend/src/services/pagefind.ts`

**TODO-8: CaptionSearchResults component**
- Create `frontend/src/components/CaptionSearchResults.svelte`:
  - Grouped results: one card per video with title, channel, date, excerpt, timestamp badge
  - "N matches" badge when multiple chunks matched, expandable
  - Clicking navigates to `#/video/{id}?t={seconds}&q={query}` (append `q=` dynamically)
  - "Show more" pagination (load 10 at a time)
  - Loading state, empty state ("No caption matches")
- Files: `frontend/src/components/CaptionSearchResults.svelte`

**TODO-9: Search mode toggle in FilterPanel**
- Modify `frontend/src/components/FilterPanel.svelte`:
  - Add "Videos" / "Captions" toggle/tab near search bar
  - "Captions" tab only visible if Pagefind index exists (probe via `initPagefind()`)
  - When "Captions" active, replace video grid with `CaptionSearchResults`
  - When switching back to "Videos", restore fuse.js metadata search
- Files: `frontend/src/components/FilterPanel.svelte`, possibly `frontend/src/App.svelte`

**TODO-10: Frontend tests**
- Unit tests for `pagefind.ts` service (mock fetch/import)
- Unit tests for `CaptionSearchResults.svelte` (mock data)
- E2E test: search term → result appears → click → video page with correct `t` and `q` params → CaptionBrowser has query populated
- Files: `frontend/tests/unit/`, `frontend/tests/e2e/`

### Phase 3: Polish

**TODO-11: Multi-channel support**
- Single unified index across all channels in a multi-channel archive
- Channel filter in search UI (auto-applied when viewing single channel)
- Year filter in search UI
- Files: `annextube/services/search_index.py`, `frontend/src/components/CaptionSearchResults.svelte`

**TODO-12: UX polish**
- Keyboard shortcuts: `/` to focus search, `Tab` to toggle mode
- "No results" with helpful messaging
- Performance testing with 1,000+ video fixtures
- Documentation: update CLI reference, add how-to guide
