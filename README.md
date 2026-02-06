# annextube Demo

This is a demo annextube archive showcasing the web frontend. It contains a small sample of videos from the [DataLad YouTube channel](https://youtube.com/c/datalad) - specifically, talks from the Distribits 2024 conference.

## Live Demo

View the live demo at: **https://con.github.io/annextube/**

## Contents

This demo includes:

- **3 sample videos** from Distribits 2024 conference:
  - Welcome and overview
  - Joey Hess: "git-annex is complete, right?"
  - Michael Hanke: "DataLad beyond Git: connecting to the rest of the world"

- **Complete metadata**: Video titles, descriptions, thumbnails, captions, comments
- **Web interface**: Browse videos offline with search and filtering
- **Git-annex integration**: All files stored directly in git (no external storage)

## How It Works

1. **Data Storage**: All metadata, thumbnails, and captions are stored directly in git (not in git-annex). This makes the demo self-contained and suitable for GitHub Pages.

2. **Video Streaming**: Videos are not downloaded - the web interface links to YouTube for streaming. This keeps the repository size small while demonstrating the full functionality.

3. **Static Site**: The web interface is a pure client-side application (no server required). It reads the TSV metadata files and renders the UI dynamically.

## Local Development

To browse the demo locally:

```bash
cd demo/web
python3 -m http.server 8000
```

Then open http://localhost:8000/

Note: Do NOT use `file://` URLs - they don't work due to CORS restrictions.

## Regenerating the Web UI

If you modify the metadata, regenerate the web interface:

```bash
# From the repository root
source .venv/bin/activate
python -m annextube.cli generate-web --output-dir demo
```

## About annextube

annextube is a YouTube archival tool that uses git-annex for efficient storage and incremental updates. It supports:

- Complete channel archival (videos, metadata, comments, captions)
- Incremental updates (efficient detection of new content)
- Offline browsing (client-side web interface)
- Flexible filtering (by date, license, playlist, etc.)
- CI/CD automation (GitHub Actions, Codeberg Actions)

See the [main repository](https://github.com/con/annextube) for more information.
