# Design: Searchable Descriptions and Unified Full-Text Search

**Status:** Accepted — transferred into spec-kit artifacts of feature `001-youtube-backup`
**Date:** 2026-08-28
**Feature:** `specs/001-youtube-backup/` — this design refines the FR-042 search
requirement family:
- Requirements: **FR-042d–FR-042g** in `specs/001-youtube-backup/spec.md`
- Data model: `videos.tsv` `description` column + `video_fulldescriptions.json`
  in `specs/001-youtube-backup/data-model.md`
- Tasks: **Phase 16 (T142–T153)** in `specs/001-youtube-backup/tasks.md`

This document remains the design rationale (the HOW and the trade-offs), like
its companion PRD `.specify/specs/caption-search-pagefind.md` did for caption
search.

**Related:** `.specify/specs/caption-search-pagefind.md` (Pagefind caption search),
issue observed on ReproTube: searching `Halchenko` in
`#/channel/ABCD-ReproNim_Course?search=Halchenko` returns nothing although the
name appears in a video description.

---

## Problem

The frontend metadata search (fuse.js) is configured with keys `title`,
`channel_name`, `tags`, `description` — but the objects it indexes come from
`videos.tsv`, which carries neither `description` nor `tags`. The frontend's
`parseTSVVideo()` hard-codes `tags: []` and leaves `description` unset, so two
of the four search keys are dead. In practice search matches **titles only**
(plus channel name, which is constant within a channel view). Descriptions
exist only in per-video `metadata.json`, lazy-loaded when a video page opens —
never at search time. The Pagefind index covers captions only, so descriptions
are not searchable anywhere in the UI.

Serializing full multi-line descriptions into `videos.tsv` is undesirable: the
TSV is a human-greppable summary table, and escaped multi-KB description blobs
would dominate it while being useful only to the search index.

## Approach (two-fold)

1. **Split description storage between two exported files:**
   - `videos.tsv` gains a `description` column holding only the **first line**
     of the description — small, useful in the summary table itself.
   - A new **`videos/video_fulldescriptions.json`** — a `{video_id: full
     description}` lookup dict — is exported next to `videos.tsv` and loaded by
     the frontend in one additional HTTP request, feeding full descriptions
     into the fuse.js index.

2. **Extend the Pagefind index with per-video metadata records** (title +
   description + tags), and rename the search modes:
   - "Videos" → **"Metadata"** (fuse.js over TSV + full descriptions)
   - "Captions" → **"Full"** (Pagefind over metadata records **and** caption
     chunks — everything).

---

## Part A — Backend export (`annextube/services/export.py`)

### A1: `description` column in `videos.tsv`

- New column `description`, appended **last** (after `path`). Both the frontend
  (`parseTSV`) and backend (`csv.DictReader`) parse header-based, so column
  position is free and old/new readers stay compatible in both directions.
- Value: the **first non-empty line** of the description, stripped:

  ```python
  def first_description_line(text: str) -> str:
      return next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
  ```

  `str.splitlines()` handles `\n`, `\r\n`, and `\r` (and Unicode line
  boundaries). Taking the first *non-empty* line makes the column useful when a
  description begins with blank lines. Remaining tabs are handled by the
  existing `escape_tsv_field()`.
- Source: `metadata.get("description", "")` — already read during the export
  walk; no extra I/O.

### A2: `videos/video_fulldescriptions.json`

- **Location:** sibling of `videos.tsv`:
  - single-channel: `videos/video_fulldescriptions.json`
  - multi-channel: `<channel_dir>/videos/video_fulldescriptions.json`
    (per channel, mirroring `videos.tsv`; the collection root has neither).
- **Format:** flat JSON object `{"<video_id>": "<full description>", ...}`.
  - Only videos whose description does **not fit on the single TSV line** get
    an entry (i.e. the stripped description differs from its first non-empty
    line); for the rest `videos.tsv` already carries the whole text. The entry
    holds the **complete** description, not a delta.
  - With no such videos the file is **not written at all**, and a stale one
    from an earlier export is removed.
  - Written with `sort_keys=True`, `ensure_ascii=False`, and a small indent
    (one entry per line) so re-exports produce deterministic, diffable output.
- **Size:** ~1–2 KB average per description → well under 1 MB for a
  ~400-video channel (ReproTube scale). Loaded in parallel with `videos.tsv`,
  so wall-clock impact on initial load is ~zero.
- Written by a new `_write_fulldescriptions_json()` alongside
  `_write_videos_tsv()` in the same export pass.

### A3: storage — global rules, no special-casing

The file follows the archive's **existing** `.gitattributes` rules: small ones
land in git, larger ones are annexed by the default
`* annex.largefiles=(...largerthan=10k)` rule. No dedicated rule is added and
no `.gitattributes` migration is performed — annexed copies simply have their
content deposited alongside the rest of the archive.

Because an annexed file's content may be absent on a given remote, the
frontend logs a warning when the file cannot be read (HTTP error, or an annex
symlink/pointer served in place of the JSON) and falls back to the TSV
first-line column. See B1.

---

## Part B — Frontend loading and Metadata search

### B1: DataLoader (`frontend/src/services/data-loader.ts`)

- `loadVideos()` and `loadChannelVideos()` fetch `videos.tsv` and
  `video_fulldescriptions.json` **in parallel** (`Promise.all`) and merge
  before returning:

  ```
  video.description = fulldescriptions[video_id] ?? row.description  // ?? undefined
  ```

  A 404, an annex pointer served instead of JSON, or a parse failure degrades
  to the TSV first line (new archives) or no description at all (old
  archives) — never an error, but a console warning names the cause so an
  archive whose annexed content was never deposited is diagnosable.
- Full-descriptions dicts are cached per channel (mirroring `videosCache`).
- `loadAllChannelVideos()` (cross-channel search) inherits this per channel —
  N parallel JSON fetches alongside the N TSV fetches it already does.
- `VideoTSVRow` gains `description?: string`; the `Video` model already has
  `description?`.

### B2: Metadata search (fuse.js)

No changes to `search.ts`: the configured keys (`title` 0.4, `channel_name`
0.2, `tags` 0.3, `description` 0.1) now receive real descriptions. This alone
fixes the motivating case: `?search=Halchenko` matches the talk whose
description names the author.

`tags` remains empty (not exported to TSV) — see Out of scope.

---

## Part C — Pagefind metadata records (`annextube/services/search_index.py`)

### C1: One metadata record per video

During `build_caption_index()` (to be renamed `build_search_index()`), for
**every** video with a `metadata.json` — including videos with no captions,
which are currently absent from the index entirely — add one custom record:

```python
await index.add_custom_record(
    url=f"#/video/{video_id}",                 # no ?t= — not a timestamped match
    content=f"{title}\n\n{description}\n\n{', '.join(tags)}",
    language=meta.get("language") or "en",
    meta={
        "title": title,
        "video_id": video_id,
        "channel_name": channel_name,
        "upload_date": upload_date,
        "record_type": "metadata",
    },
    filters={
        "record_type": ["metadata"],
        "channel_name": [channel_name],
        "year": [year],
        "language": [lang],
    },
    sort={"date": upload_date},
)
```

- Channel name is deliberately **not** in `content` — it is a filter/meta
  field; putting it in content would make every video of a channel match a
  query for the channel's name in Full mode.
- Caption chunk records gain the symmetric `record_type: "caption"` in both
  `meta` and `filters`. The filter enables future scoping (captions-only /
  metadata-only) without a rebuild.
- `IndexStats` gains a `metadata_records` counter; `videos_skipped` now means
  "no metadata.json" only (missing VTT no longer skips the whole video).

### C2: Incremental rebuild detection

`_vtt_changed_since()` currently diffs `-- '*.vtt'` only; description edits
would never trigger a rebuild. Generalize to
`git diff --name-only <commit> HEAD -- '*.vtt' '*metadata.json'`
(rename to `_content_changed_since()`).

### C3: Index compatibility

- **New frontend + old index:** records lack `record_type` → treated as
  captions (exact current behavior).
- **Old frontend + new index:** metadata records would render as caption
  matches at `00:00`. Cosmetic only, and rare: `generate-web --search-index`
  deploys frontend and index together, so a version skew doesn't persist.

---

## Part D — Frontend "Metadata" / "Full" search modes

### D1: Mode naming and URL state

- `SearchMode` becomes `'metadata' | 'full'` (was `'videos' | 'captions'`).
- URL param: `mode=full` (absent = metadata, the default).
  `url-state.ts` maps the **legacy value `mode=captions` to `full`** so shared
  links keep working; `videos`/absent → metadata.
- Toggle labels: **Metadata** | **Full**. Placeholders:
  - Metadata: `Search titles, descriptions, tags...`
  - Full: `Search metadata and captions...`
- When no Pagefind index exists (`initPagefind()` fails), the toggle stays
  hidden and Metadata search is the only mode — unchanged degradation.

### D2: Full-mode results (`pagefind.ts` + results component)

- `searchCaptions()` → `searchFull()`. Grouping by `video_id` is preserved;
  each loaded result is classified by `data.meta.record_type ?? 'caption'`.
- `GroupedCaptionResult` → `GroupedSearchResult`:
  - `allMatches: CaptionMatch[]` — caption matches, sorted by timestamp (as
    today);
  - new `descriptionMatch?: { excerpt: string }` — at most one per video;
  - `matchCount` = caption matches + (1 if description matched).
- `CaptionSearchResults.svelte` → `FullSearchResults.svelte` (`git mv`):
  - A description match renders as a labeled row (badge `description`, no
    timestamp) above the caption matches; its click target is plain
    `#/video/{id}` (no `t`/`q`/`filter` params — those drive the caption
    browser).
  - Caption match rows unchanged (timestamp badge, `?t=&q=&filter=1`).
  - Copy updates: "Searching captions..." → "Searching...", "N videos with
    caption matches" → "N videos with matches", empty state accordingly.

---

## Compatibility matrix

| Frontend | Archive data | Behavior |
|---|---|---|
| new | old (no column, no JSON, old index) | Same as today: title search; JSON 404 tolerated; Full mode = captions only |
| new | new | Full description search in Metadata mode; metadata + caption records in Full mode |
| old | new | Extra TSV column ignored (header-based parsing); JSON unused; metadata records shown as `00:00` caption matches until `generate-web` redeploys the frontend |

`file://` protocol: the extra JSON fetch behaves like the existing TSV fetch;
on failure the loader degrades as above. Pagefind still requires HTTP
(unchanged).

---

## Testing plan (TDD)

**Backend unit** (`tests/unit/`):
- `first_description_line`: LF / CRLF / CR, leading blank lines, empty
  description, single-line, embedded tabs (escaped in TSV).
- Export writes `description` as the last TSV column; round-trips through
  escaping.
- `video_fulldescriptions.json`: entries only for non-empty descriptions;
  full text preserved; deterministic output (sorted keys) across re-exports.
- `.gitattributes` migration: rule appended once, idempotent.
- `search_index`: metadata record emitted for every video (with and without
  VTT); caption records carry `record_type: caption`; content is
  title + description + tags; `metadata.json` change triggers rebuild;
  no-change still skips.

**Frontend unit** (`frontend/tests/`):
- `parseTSV` with the new column; `parseTSVVideo` maps it.
- DataLoader: merge precedence (JSON over TSV first line), 404 fallback,
  per-channel caching.
- Search: a term present only in a full description matches (the Halchenko
  regression test); a term only in the first line also matches on old-style
  archives without the JSON.
- `url-state`: `mode=captions` parses as `full`; `full` round-trips.
- `searchFull` grouping: mixed record types split into `descriptionMatch` +
  `allMatches`; missing `record_type` treated as caption.
- `FullSearchResults`: description row rendering, click targets.

**E2E** (`frontend/tests/e2e/`, `@AnnexTubeTesting` fixtures):
- Metadata mode: search a description-only term → video listed.
- Full mode: same term → result card with description badge; caption term →
  timestamped result (existing flow still works).

---

## Out of scope / follow-ups

- **`tags` in `videos.tsv`** — would light up the remaining dead fuse key and
  the tag filter UI. Same pattern (joined column), separate change.
- **Comments in Full search** — further `add_custom_record()` calls; deferred.
- **Playlist descriptions** — `playlists.tsv` untouched.
- Existing, unrelated gaps noticed while designing (tracked separately, not
  changed here): Pagefind record URLs lack the `#/channel/<dir>` prefix in
  multi-channel archives; `thumbnail_url` is absent from caption record meta
  although the frontend reads it.

---

## Implementation order (one logical change per commit)

Tracked as **Phase 16, T142–T153** in `specs/001-youtube-backup/tasks.md`:

1. **T142** — Backend: `first_description_line()` + `description` TSV column + tests.
2. **T143** — Backend: `video_fulldescriptions.json` export (entries only for
   descriptions that do not fit the TSV line; no file when empty) + tests.
3. **T144** — Frontend: DataLoader parallel load/merge +
   `VideoTSVRow.description` + tests — *this commit fixes the motivating bug*.
4. **T145** — Backend: Pagefind metadata records + `record_type` + incremental
   detection over `metadata.json` + tests.
5. **T146** — Frontend: `searchFull()` grouping with `record_type` + tests.
6. **T147** — Frontend: Metadata/Full rename (modes, URL state with legacy
   mapping, `FullSearchResults.svelte`) + tests.
7. **T148/T149** — E2E tests + docs (`docs/content/how-to/search.md`).
8. **T150–T153** — follow-ups found after the first pass: the `parseHash`
   route fix, the review changes to how the JSON is stored and scoped, the
   reconciliation with PR #7 (approximate matches) and its renumbering, and
   the empty-score classification fix.
