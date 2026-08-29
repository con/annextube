---
title: "Search the Web Interface"
description: "How the Metadata and Full search modes work, and how to enable them"
weight: 30
---

# Search the Web Interface

The annextube web interface offers two search modes, selectable with the
toggle next to the search box:

- **Metadata** (default) — instant client-side search over video titles,
  channel names, tags, and **full video descriptions**. Works everywhere,
  including archives opened via `file://`.
- **Full** — full-text search over video metadata **and spoken caption
  content**, with results that deep-link to the exact timestamp in the
  video. Requires a Pagefind search index and HTTP serving.

## How Metadata search gets descriptions

`annextube export` (run automatically during `backup`/`update`) writes two
files next to each other:

- `videos/videos.tsv` — the summary table, including a `description` column
  with the **first non-empty line** of each description
- `videos/video_fulldescriptions.json` — a `{video_id: full description}`
  lookup with the complete text

The web interface loads both (one extra request) and feeds the full
descriptions into the Metadata search index, so a search for a speaker's
name mentioned only in a talk's description finds the talk.

In multi-channel collections both files live per channel
(`<channel>/videos/`).

### Older archives

Archives exported before this feature simply lack the files — search then
falls back to matching titles only. To enable description search, re-run
the export:

```bash
annextube export --output-dir ~/my-archive
```

The export also adds a `.gitattributes` rule keeping
`video_fulldescriptions.json` in git (not git-annex), so the file is always
readable by the web interface on clones.

## Enabling Full search

Full search needs the Pagefind index (requires `pip install
'annextube[search]'`):

```bash
# During backup
annextube backup --output-dir ~/my-archive --search-index

# Or standalone
annextube build-search-index --output-dir ~/my-archive
```

The index contains, for every video:

- one **metadata record** (title, description, tags) — so videos without
  captions are still findable, and
- **caption chunks** from the VTT files (curated captions preferred),
  each deep-linking to its timestamp.

The index rebuilds incrementally: it is refreshed when captions *or*
`metadata.json` files (titles, descriptions, tags) changed since the last
build.

In Full mode, a match in a description shows a green `description` badge
instead of a timestamp and opens the video page; caption matches show
their timestamp and jump straight to that moment with the transcript
filtered to the query.

## Shareable URLs

The active mode is part of the URL (`&mode=full`), so search links can be
shared. Links created before the modes were renamed (`&mode=captions`)
keep working and open in Full mode.
