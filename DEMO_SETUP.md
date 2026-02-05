# GitHub Pages Demo Setup Summary

## Overview

Successfully set up a live demo for annextube that will be deployed to GitHub Pages at **https://con.github.io/annextube/**

## What Was Created

### 1. Demo Directory (`/home/yoh/proj/annextube/demo/`)

A self-contained demonstration archive containing:

- **3 sample videos** from the DataLad YouTube channel (Distribits 2024 conference)
  - "Distribits 2024: Welcome and overview"
  - "Joey Hess: git-annex is complete, right?"
  - "Michael Hanke: DataLad beyond Git: connecting to the rest of the world"

- **Complete metadata** for each video:
  - `metadata.json` - Full video details (title, description, duration, etc.)
  - `thumbnail.jpg` - Video thumbnail
  - `video.en.vtt` - English captions
  - `comments.json` - Video comments
  - `captions.tsv` - Caption summary

- **Archive-level metadata**:
  - `authors.tsv` - Channel authors
  - `videos/videos.tsv` - All videos summary
  - `playlists/playlists.tsv` - Playlists summary
  - `.annextube/config.toml` - Archive configuration

- **Web interface** (`demo/web/`):
  - `index.html` - Main HTML page
  - `assets/` - JavaScript and CSS bundles
  - Client-side application (no server required)

**Total size**: ~1.1 MB (23 files)

### 2. GitHub Actions Workflow (`.github/workflows/deploy-demo.yml`)

Automated deployment workflow that:
- Triggers on push to `master` branch (when `demo/` changes)
- Can be manually triggered via `workflow_dispatch`
- Deploys the `demo/web/` directory to GitHub Pages
- Uses official GitHub Pages actions for deployment

### 3. Documentation

- **`demo/README.md`**: Comprehensive documentation for the demo
- **Main README.md**: Added prominent link to live demo at the top

### 4. Configuration Changes

- **`.gitignore`**: Updated to exclude `web/` directories but allow `demo/web/`

## Key Design Decisions

### 1. Storage Approach

**Decision**: Store all files directly in git (not git-annex)

**Rationale**:
- GitHub Pages requires all files to be directly accessible
- Demo is small enough (~1.1 MB) to commit directly
- Makes deployment simple and reliable
- No need for git-annex complexity in the demo

### 2. Video Content

**Decision**: Store metadata only (no actual video files)

**Rationale**:
- Videos are NOT downloaded - web interface links to YouTube for streaming
- Keeps repository size minimal
- Demonstrates full metadata capabilities
- Videos are still accessible via YouTube

### 3. Sample Content Selection

**Decision**: 3 videos from Distribits 2024 conference (DataLad channel)

**Rationale**:
- Relevant to the target audience (research data management)
- High-quality conference talks with good metadata
- Small number keeps demo focused
- All videos have complete metadata (captions, comments, etc.)

## Deployment Steps

### Initial Setup (Required Once)

1. **Enable GitHub Pages** in repository settings:
   - Go to Settings → Pages
   - Source: GitHub Actions
   - (This is the only manual step required)

2. **Push changes** to trigger deployment:
   ```bash
   git push origin master
   ```

3. **Wait for deployment** (usually 1-2 minutes)
   - Check Actions tab for deployment status
   - Demo will be available at https://con.github.io/annextube/

### Updating the Demo

To update the demo content:

1. **Modify files** in `demo/` directory
2. **Regenerate web UI** (if needed):
   ```bash
   source .venv/bin/activate
   python -m annextube.cli generate-web --output-dir demo
   ```
3. **Commit and push**:
   ```bash
   git add demo/
   git commit -m "Update demo content"
   git push origin master
   ```

The workflow will automatically redeploy the changes.

## File Structure

```
annextube/
├── demo/                           # Demo archive (committed to git)
│   ├── .annextube/
│   │   └── config.toml            # Archive configuration
│   ├── README.md                  # Demo documentation
│   ├── authors.tsv                # Channel authors
│   ├── playlists/
│   │   └── playlists.tsv          # Playlists summary
│   ├── videos/                    # Video directories
│   │   ├── 2024-04-09_*/          # Individual video folders
│   │   │   ├── metadata.json     # Video metadata
│   │   │   ├── thumbnail.jpg     # Thumbnail
│   │   │   ├── video.en.vtt      # Captions
│   │   │   ├── comments.json     # Comments
│   │   │   └── captions.tsv      # Caption summary
│   │   └── videos.tsv             # Videos summary
│   └── web/                       # Generated web interface
│       ├── index.html
│       └── assets/
│           ├── index-*.js         # JavaScript bundle
│           └── index-*.css        # CSS bundle
├── .github/workflows/
│   └── deploy-demo.yml            # GitHub Actions deployment workflow
└── README.md                      # Main README (with demo link)
```

## Commits Created

1. `0ff59e4` - Add GitHub Actions workflow for demo deployment
2. `7baae7a` - Add link to live demo in README
3. `f976bbc` - Add demo for GitHub Pages deployment

All commits are on the `master` branch and ready to push.

## Next Steps

1. **Push to GitHub**:
   ```bash
   git push origin master
   ```

2. **Enable GitHub Pages** (if not already enabled):
   - Go to repository Settings → Pages
   - Select "GitHub Actions" as the source

3. **Verify deployment**:
   - Check the Actions tab for the workflow run
   - Visit https://con.github.io/annextube/ once deployment completes

4. **Test the demo**:
   - Browse videos
   - Test search functionality
   - Check video links (should open YouTube)
   - Verify metadata display

## Technical Notes

### Why Not a Submodule?

Initially, `demo/` was created as a separate git-annex repository. However, for GitHub Pages deployment, it's better to have all files directly in the main repository:
- Simpler deployment workflow
- No submodule complexity
- All files directly accessible to GitHub Actions
- Easier to update and maintain

### Video Streaming

Videos are not included in the demo. The web interface displays metadata and provides links to stream videos directly from YouTube. This is ideal because:
- Keeps repository size minimal
- No copyright/licensing concerns
- Videos are always available (as long as YouTube hosts them)
- Demonstrates the metadata browsing capabilities

### Future Enhancements

Potential improvements to the demo:
- Add more videos (keep under 10-20 MB total)
- Include example of private/unlisted video metadata
- Add playlist examples
- Demonstrate different filtering options
- Add tutorial/walkthrough overlay

## Troubleshooting

### Workflow Fails

If the GitHub Actions workflow fails:
1. Check the Actions tab for error details
2. Verify GitHub Pages is enabled in repository settings
3. Check that `demo/web/` directory exists and has content
4. Ensure workflow file has correct permissions

### Demo Not Loading

If the demo doesn't load at the GitHub Pages URL:
1. Wait 1-2 minutes after deployment completes
2. Clear browser cache and reload
3. Check browser console for errors
4. Verify files were uploaded in Actions artifacts

### Videos Not Playing

The web interface should link to YouTube for video playback. If links don't work:
1. Check that `metadata.json` files have valid `video_id` fields
2. Verify YouTube URLs are correctly formatted
3. Check if videos are still available on YouTube

## Source Data

The demo content was copied from:
- **Source**: `/home/yoh/proj/annextube/test-archives/datalad/`
- **Channel**: DataLad (https://youtube.com/c/datalad)
- **Event**: Distribits 2024 conference
- **Videos**: Public, Creative Commons licensed

All metadata and thumbnails were generated by annextube from the actual YouTube channel.
