# Quickstart: PR Web UI Previews (design phase)

This describes how the feature is expected to work once implemented
(`/speckit.tasks` → `/speckit.implement`, follow-up to this design PR), and
how to manually validate the design's core assumption *today*, before any
workflow code exists.

## Validating the design's core assumption today (no new code needed)

The whole design rests on: *"a working web UI preview can be built from any
branch's code, against the existing `annextubetesting` dataset, without
touching YouTube."* This is already possible manually and is worth
confirming before implementation starts:

```bash
# From a checkout of the PR/branch you want to preview:
WORK_DIR=$(mktemp -d)
git archive annextubetesting | tar -x -C "$WORK_DIR"   # existing dataset, no YouTube fetch
uv run annextube generate-web --output-dir "$WORK_DIR"  # PR's own code generates the UI
cd "$WORK_DIR" && python3 -m http.server 8080  # serve from WORK_DIR itself (not
                                                #   WORK_DIR/web) so the frontend's
                                                #   relative fetches of videos/,
                                                #   playlists/, etc. resolve --
                                                #   see generate-web's own printed
                                                #   instructions; browse to
                                                #   http://localhost:8080/web/
```

This is exactly `tools/deploy-demo.sh`'s existing Step 1–2 logic (see
`research.md`), confirming the implementation phase has a real, working
pattern to parameterize per-PR rather than invent from scratch.

## Expected reviewer experience once implemented

1. Open (or push to) a PR that changes `frontend/**` or the web-UI
   generation code.
2. Wait for CI to finish (includes the new preview build/publish job).
3. Find the preview link in a PR comment (created or updated in place).
4. Click through: browse channels/videos, open a video detail page, use
   search — all against the `@AnnexTubeTesting` sample data.
5. Push another commit → the same comment updates to the new build once it
   publishes (old preview stays live until the new one is ready — no gap).
6. Merge or close the PR → the preview is removed within the next cleanup
   run.

## Expected maintainer experience

- No manual steps for individual PRs — this is fully automated per FR-001–FR-009.
- Periodic sanity check: `gh-pages` branch size doesn't grow unbounded
  (SC-003) — spot-checkable by listing `pr-*/` directories on `gh-pages` and
  confirming they correspond only to currently-open PRs (plus any grace
  period).
