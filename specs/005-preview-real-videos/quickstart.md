# Quickstart: Curating Real Preview Video Content (maintainer, out-of-band)

This is a **one-time (or occasionally repeated) maintainer action**, run
locally with real YouTube network access — **never** in CI. It is the only
piece of "implementation" this design needs; see `plan.md`'s Note for why no
`con/annextube` code changes alongside it. Nothing here is executed by this
design PR itself.

## Prerequisites

- `yt-dlp` (already an `annextube` dependency) and `ffmpeg`, installed
  locally.
- Write access to `con/annextubetesting` (a separate repository from
  `con/annextube`).
- Real network access to YouTube (this explicitly will not work from a
  datacenter/CI IP — see `docs/content/how-to/troubleshooting.md`).

## Steps

1. Clone `con/annextubetesting` with write access (not the anonymous,
   read-only clone the PR-preview build job uses):

   ```bash
   git clone git@github.com:con/annextubetesting.git
   cd annextubetesting
   ```

2. Pick 1-3 videos from the channel's own Creative-Commons-licensed subset
   (`playlists/All-Creative-Commons-Videos/`) — recommended starting set,
   chosen to also exercise the caption-track code path
   (`VideoPlayer.svelte`'s `<track>` rendering):

   - `videos/2026/02/2026-02-05_Test-Video-Creative-Commons-1/`
     (`video_id=GhGQV_enM8M`) — plain playback, no captions.
   - `videos/2026/02/2026-02-05_Test-Video-Multi-language-Captions/`
     — exercises multi-language `<track>` elements (this one is also
     CC-licensed).

   (`Test-Video-With-English-Captions` is a good third choice but is
   `"standard"`-licensed per its `metadata.json` — see `research.md`'s
   licensing note for why this quickstart sticks to the CC-licensed subset
   for now.)

3. For each chosen video, download at a small resolution and remux straight
   to `.mkv` (the frontend's hardcoded filename — see `research.md`):

   ```bash
   VIDEO_DIR=videos/2026/02/2026-02-05_Test-Video-Creative-Commons-1
   VIDEO_URL=$(python3 -c "import json;print(json.load(open('$VIDEO_DIR/metadata.json'))['source_url'])")

   yt-dlp -f "bv*[height<=320]+ba/b[height<=320]" \
     --remux-video mkv \
     -o "/tmp/curated-%(id)s.%(ext)s" \
     "$VIDEO_URL"
   ```

   If the resulting file is still larger/higher-resolution than desired
   (some of these test uploads may only offer one rendition), downscale it
   explicitly with `ffmpeg` — preserving aspect ratio, not forcing a fixed
   height (see `research.md`'s aspect-ratio decision). Write the result to a
   **scratch path outside the working tree**, not directly into `$VIDEO_DIR`
   — that path is still a dangling git-annex symlink at this point, and
   writing through it is unsafe/undefined:

   ```bash
   ffmpeg -i /tmp/curated-GhGQV_enM8M.mkv \
     -vf "scale=320:-2" -c:v libx264 -preset veryslow -crf 30 \
     /tmp/curated-GhGQV_enM8M-320.mkv
   ```

   Verify the result before committing it:

   ```bash
   ffprobe -v error -show_entries format=duration,size \
     -show_entries stream=width,height,codec_name \
     -of default=noprint_wrappers=1 /tmp/curated-GhGQV_enM8M-320.mkv
   ls -la /tmp/curated-GhGQV_enM8M-320.mkv
   ```

   As a sizing reference (from a real `ffmpeg` prototype run against a
   generic, freely-licensed sample video in this design's own `research.md`,
   **not** against actual YouTube content): a 320-pixel-wide, few-second,
   silent H.264-in-MKV clip lands in the tens-of-kilobytes range. Since
   every real `@AnnexTubeTesting` video is already only 1-5 seconds, expect
   the real curated files to be at least as small.

4. Replace the git-annex symlink with the real file, and add a scoped
   `.gitattributes` override so it's tracked as plain git content (mirrors
   the existing `thumbnail.jpg` override already in that file):

   ```bash
   git rm "$VIDEO_DIR/video.mkv"           # removes the dangling symlink
   cp /tmp/curated-GhGQV_enM8M-320.mkv "$VIDEO_DIR/video.mkv"

   cat >> .gitattributes <<EOF
   $VIDEO_DIR/video.mkv annex.largefiles=nothing
   EOF

   git add "$VIDEO_DIR/video.mkv" .gitattributes
   ```

5. Bump `download_status` to `"downloaded"` for this video. **The field
   that actually matters to the frontend is the `download_status` column in
   `videos/videos.tsv`** — `data-loader.ts` overwrites whatever
   `metadata.json` says with the TSV's value at load time (see
   `research.md`'s correction on this point), and that column already reads
   `"tracked"` for every video today, which already makes "Play from
   Archive"/hover-preview work with zero changes; only the status *badge*
   needs `"downloaded"` specifically. Update both files, but **hand-edit
   only this one video's `videos.tsv` row** — do not run `annextube export`
   (`ExportService.generate_videos_tsv()`) to regenerate the whole file: it
   rescans every video's `metadata.json` and maps anything other than
   `"downloaded"` to `"metadata_only"`, which has its own frontend badge
   (unlike `"tracked"`, which has none). Since the other 9 videos'
   `metadata.json` already say `"not_downloaded"` (stale relative to the
   TSV's `"tracked"`), regenerating would put a spurious "metadata only"
   badge on all of them. This TSV/`metadata.json` drift is a pre-existing
   inconsistency in `con/annextubetesting`, out of scope to fix here:

   ```bash
   python3 - "$VIDEO_DIR/metadata.json" <<'EOF'
   import json, sys
   path = sys.argv[1]
   data = json.load(open(path))
   data["download_status"] = "downloaded"
   json.dump(data, open(path, "w"), indent=2)
   EOF

   # hand-edit only this video's row in videos/videos.tsv, changing its
   # download_status column from "tracked" to "downloaded" -- do NOT run
   # `annextube export` here, per the note above
   ```

   Also add a short note near the `.gitattributes` override (or in that
   repository's README) that this specific file is an intentionally
   downscaled preview copy, not a full-quality archival backup — see
   `research.md`'s "Decision: `download_status` semantics" for why this is
   documented there instead of as a new schema field.

6. Commit and push to `con/annextubetesting`:

   ```bash
   git commit -m "Add downscaled preview video for Test-Video-Creative-Commons-1"
   git push origin master   # con/annextubetesting's actual default branch
   ```

   Note: this push touches `videos/**`/`.gitattributes`, which also
   triggers `con/annextubetesting`'s own `deploy-ghpages.yml` (via
   `con/annextube-action`) — not something this plan modifies or has
   verified the internals of, but worth knowing if that workflow also
   regenerates `videos.tsv` on push (see the note in step 5 above).

7. Verify end-to-end against the *existing*, unmodified preview pipeline —
   no `con/annextube` code changes needed for this step to work, per
   `research.md`:

   ```bash
   WORK_DIR=$(mktemp -d)
   git clone --depth=1 https://github.com/con/annextubetesting.git "$WORK_DIR/src"
   git -C "$WORK_DIR/src" archive HEAD | tar -x -C "$WORK_DIR"
   find "$WORK_DIR" -type l -delete   # same step the real build workflow runs
   uv run annextube generate-web --output-dir "$WORK_DIR"
   cd "$WORK_DIR" && python3 -m http.server 8080
   # Browse to http://localhost:8080/web/, open the curated video, confirm
   # "Play from Archive" is offered and plays.
   ```

   (This mirrors `specs/004-pr-webui-preview/quickstart.md`'s own manual
   verification recipe exactly — the only difference is that this time the
   `find -type l -delete` step deletes only the *other*, not-yet-curated
   videos' symlinks, not the curated one(s), since those are now real
   files.)

8. Open (or push to) any `con/annextube` PR touching `frontend/**`, and
   confirm its automatically-built preview now offers real playback for the
   curated video(s) — this is SC-001 from `spec.md`.

## What this quickstart deliberately does not cover

- Curating more than 1-3 videos, or building a repeatable/automated
  curation pipeline — out of scope for this first increment (`spec.md`
  FR-001/FR-007).
- Adding a `--max-height`/clip-selection option to `annextube`'s own
  download commands — deferred, see `plan.md`'s Complexity Tracking.
- Anything that runs inside `.github/workflows/` — this entire quickstart
  is, by design, something a maintainer runs on their own machine.
