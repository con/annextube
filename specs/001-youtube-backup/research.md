# Research: YouTube Archive System

**Feature**: 001-youtube-backup
**Date**: 2026-01-24
**Purpose**: Resolve technical unknowns and establish best practices for implementation

## Research Tasks

### 1. Frontend Framework Selection

**Question**: Which frontend framework should be used for the client-side web interface?

**Context**:
- Must work offline via file:// protocol
- Must support ES6+ JavaScript
- Client-side only (no backend server)
- Load and parse TSV/JSON metadata files
- Video playback with caption support
- Search and filtering functionality
- Similar to mykrok project (referenced in spec)

**Research**:

Evaluating three primary options: React, Vue, and Svelte.

**React**:
- Pros: Largest ecosystem, excellent TypeScript support, mature testing tools, extensive documentation
- Cons: Larger bundle size, requires build tooling, more boilerplate
- Offline file:// support: ✅ Works with proper build configuration
- TypeScript integration: ✅ Excellent (first-class support)
- Testing: ✅ Mature (React Testing Library, Jest/Vitest, Playwright)
- Bundle size: ~45-50KB (minified + gzipped with React 18)

**Vue 3**:
- Pros: Progressive framework, smaller bundle, good TypeScript support, simpler learning curve
- Cons: Smaller ecosystem than React, composition API still evolving
- Offline file:// support: ✅ Works with proper build configuration
- TypeScript integration: ✅ Good (improving with Vue 3)
- Testing: ✅ Solid (Vue Testing Library, Vitest recommended, Playwright)
- Bundle size: ~35-40KB (minified + gzipped with Vue 3)

**Svelte**:
- Pros: Smallest bundle size, compiles to vanilla JS, no virtual DOM overhead, excellent performance
- Cons: Smaller ecosystem, less mature tooling, fewer component libraries
- Offline file:// support: ✅ Works excellently (compiles to vanilla JS)
- TypeScript integration: ✅ Good (SvelteKit has built-in support)
- Testing: ⚠️ Less mature (Vitest works, Playwright for E2E)
- Bundle size: ~15-20KB (minified + gzipped)

**File:// Protocol Considerations**:
- All three frameworks work with file:// protocol when built properly
- Key requirement: Use relative paths (no absolute paths from root)
- Avoid features requiring CORS (all data must be local)
- Use hash-based routing (not history API which fails on file://)

**Decision**: **Svelte**

**Rationale**:
- **Smallest bundle size** (15-20KB vs 35-50KB) - critical for offline use and distribution
- **Compiles to vanilla JS** - no runtime framework overhead, better for file:// protocol
- **Excellent performance** - no virtual DOM, faster rendering for large video lists
- **Similar to mykrok** - if mykrok used client-side approach, Svelte aligns well
- **Simple learning curve** - easier for contributors to understand
- **Constitution alignment**: Resource Efficiency (Principle XI) - minimal CPU/memory/network overhead

**Alternatives considered**:
- React rejected: Larger bundle size, more overhead for client-side-only app
- Vue rejected: Good middle ground but Svelte's performance benefits are more valuable for this use case

---

### 2. Frontend Testing Framework

**Question**: What testing framework should be used for the frontend?

**Context**:
- Frontend is Svelte-based (from research task 1)
- Need unit tests (components in isolation)
- Need integration tests (component interactions, state management)
- Need E2E tests (user workflows)
- Must align with Constitution Principle IV (Integration Testing)

**Research**:

**Unit Testing Options**:

1. **Vitest**:
   - Fast, Vite-native test runner
   - ESM support (modern standard)
   - Compatible with Jest API
   - Excellent Svelte support
   - Bundle size analysis built-in
   - Pros: Fast, modern, Svelte-friendly
   - Cons: Newer (less mature than Jest)

2. **Jest**:
   - Industry standard, mature ecosystem
   - Extensive documentation and community
   - Svelte support via svelte-jester or @testing-library/svelte
   - Pros: Mature, well-documented
   - Cons: Slower than Vitest, ESM support requires config

**Component Testing**:
- **@testing-library/svelte**: Recommended for both Vitest and Jest
- Focuses on testing user interactions (not implementation details)
- Aligns with Testing Library philosophy
- Works with both Vitest and Jest

**E2E Testing Options**:

1. **Playwright**:
   - Modern, cross-browser (Chrome, Firefox, Safari, Edge)
   - Excellent developer experience
   - Auto-wait for elements (reduces flakiness)
   - Supports file:// protocol testing ✅
   - Pros: Modern, reliable, multi-browser
   - Cons: Heavier than Cypress

2. **Cypress**:
   - Popular, mature ecosystem
   - Great developer experience (time-travel debugging)
   - file:// protocol support: ⚠️ Limited (requires workarounds)
   - Pros: Mature, excellent DX
   - Cons: file:// protocol issues, single-browser testing (recent versions support more)

**Decision**: **Vitest + @testing-library/svelte + Playwright**

**Rationale**:
- **Vitest**: Fast, modern, Svelte-native support, aligns with resource efficiency
- **@testing-library/svelte**: Industry best practice, focuses on user behavior
- **Playwright**: Multi-browser, excellent file:// protocol support (critical for offline use case)
- **Constitution alignment**:
  - Principle IV: Integration Testing - Playwright covers E2E workflows
  - Principle XI: Resource Efficiency - Vitest is faster than Jest

**Alternatives considered**:
- Jest rejected: Slower, more configuration overhead for ESM/Svelte
- Cypress rejected: file:// protocol support issues are a dealbreaker for this project

**Testing Structure**:
```
frontend/tests/
├── unit/              # Vitest + @testing-library/svelte
│   ├── VideoList.test.ts
│   ├── VideoPlayer.test.ts
│   ├── FilterPanel.test.ts
│   └── CommentView.test.ts
├── integration/       # Vitest + @testing-library/svelte
│   ├── video-filtering.test.ts
│   ├── state-management.test.ts
│   └── schema-validation.test.ts
└── e2e/              # Playwright
    ├── browse-archive.spec.ts
    ├── search-videos.spec.ts
    └── play-video-with-captions.spec.ts
```

---

### 3. datasalad Best Practices

**Question**: How to effectively use datasalad for git/git-annex operations?

**Context**:
- Spec clarification: Use datasalad as core library for git/git-annex command execution
- Need efficient command execution patterns
- Constitution Principle VIII: DRY - avoid reimplementing git/git-annex logic

**Research**:

**datasalad Overview** (from https://hub.datalad.org/datalad/datasalad):
- Provides efficient interfaces for external command execution
- Designed for git and git-annex operations
- Prioritizes external command execution over pure-Python implementations where possible
- Part of the DataLad ecosystem

**Best Practices**:

1. **Use datasalad's command execution interfaces**:
   - Prioritize datasalad APIs for git/git-annex operations
   - Avoid direct subprocess calls to git/git-annex where datasalad provides equivalent
   - Leverage datasalad's error handling and output parsing

2. **Command patterns**:
   - Use datasalad for:
     - Repository initialization
     - Git operations (add, commit, status, log)
     - Git-annex operations (init, addurl, metadata, get, drop)
     - File tracking configuration (.gitattributes)
   - Direct yt-dlp integration still needed (datasalad doesn't wrap yt-dlp)

3. **Error handling**:
   - datasalad provides structured command result objects
   - Parse stderr/stdout via datasalad interfaces
   - Implement retry logic on top of datasalad (not reimplementing command execution)

4. **Performance considerations**:
   - Batch operations where possible (git-annex supports batch modes)
   - Use git-annex metadata in batch mode for large-scale metadata operations
   - Streaming output for long-running commands

**Decision**: Use datasalad as primary interface for all git/git-annex operations

**Rationale**:
- Avoids reimplementing git/git-annex command execution (DRY Principle)
- Leverages tested, efficient implementation from DataLad ecosystem
- Aligns with spec clarification (prioritize datasalad interfaces)

**Implementation pattern**:
```python
# annextube/services/git_annex.py
from datasalad import <appropriate modules>

class GitAnnexService:
    """Wrapper around datasalad for git-annex operations."""

    def init_repo(self, path, git_annex_config):
        # Use datasalad to initialize git-annex repo
        pass

    def add_url(self, url, file_path, backend='URL'):
        # Use datasalad to add URL to git-annex
        pass

    def set_metadata(self, file_path, metadata):
        # Use datasalad for git-annex metadata operations
        pass
```

---

### 4. yt-dlp Integration Patterns

**Question**: How should yt-dlp be integrated for YouTube downloads and metadata extraction?

**Context**:
- yt-dlp is the primary dependency for YouTube operations
- Need metadata extraction, video downloads, comment fetching, caption downloads
- Must respect rate limits and handle errors gracefully

**Research**:

**yt-dlp Capabilities**:
- Video metadata extraction (title, description, views, likes, etc.)
- Comment extraction with threading support
- Caption/subtitle extraction in multiple formats (VTT, SRT, etc.)
- Playlist and channel enumeration
- Archive file support (track downloaded items)
- Post-processing hooks
- Rate limiting built-in

**Best Practices**:

1. **Use yt-dlp's Python API** (not CLI):
   ```python
   import yt_dlp

   ydl_opts = {
       'writeinfojson': True,
       'writesubtitles': True,
       'writeautomaticsub': True,
       'subtitleslangs': ['all'],
       'getcomments': True,
       # ... other options
   }

   with yt_dlp.YoutubeDL(ydl_opts) as ydl:
       info = ydl.extract_info(url, download=False)
   ```

2. **Archive file pattern** for tracking:
   - yt-dlp supports `--download-archive` to track downloaded items
   - Store archive file in .git/annex/ or repo config
   - Enables efficient incremental updates (skip already-processed videos)

3. **Lazy download strategy**:
   - `download=False` for metadata-only extraction
   - Download videos only when explicitly requested or filters match
   - Aligns with FR-004 (track URLs without downloading content)

4. **Error handling and retries**:
   - yt-dlp has built-in retry logic
   - Configure via `retries`, `fragment_retries`, `sleep_interval`
   - Catch exceptions for deleted/private videos gracefully

5. **Rate limiting**:
   - Use `sleep_interval` and `max_sleep_interval` options
   - Respect YouTube's rate limits (built into yt-dlp)
   - Consider `playlist_items` for filtering (reduce API calls)

**Decision**: Use yt-dlp Python API with lazy download strategy and archive file tracking

**Rationale**:
- Python API provides better control and error handling than CLI
- Archive file enables efficient incremental updates (Principle XI: Resource Efficiency)
- Lazy download aligns with FR-004 and storage efficiency

**Implementation pattern**:
```python
# annextube/services/youtube.py
import yt_dlp

class YouTubeService:
    """Wrapper around yt-dlp for YouTube operations."""

    def __init__(self, archive_file, rate_limit):
        self.archive_file = archive_file
        self.rate_limit = rate_limit

    def get_channel_videos(self, channel_url, filters):
        # Extract channel metadata
        # Apply filters (date, license, etc.)
        # Return video list without downloading
        pass

    def get_video_metadata(self, video_id):
        # Extract full metadata for a video
        # Download=False (metadata only)
        pass

    def download_video_content(self, video_id, output_path):
        # Download video file via git-annex addurl
        # Use yt-dlp to get direct URL, pass to git-annex
        pass

    def get_comments(self, video_id):
        # Extract comments with threading
        pass

    def get_captions(self, video_id, output_dir):
        # Download all available captions
        pass
```

---

### 5. Hugo Documentation with Congo Theme

**Question**: How to set up Hugo documentation following Diataxis framework?

**Context**:
- Spec requires Hugo static site generator with Congo theme
- Diataxis framework: Tutorial, How-to, Reference, Explanation
- Documentation must be served via GitHub Pages

**Research**:

**Hugo + Congo Setup**:
1. **Install Hugo** (extended version for Sass support)
2. **Add Congo theme** as git submodule or Hugo module
3. **Configure for GitHub Pages**:
   - Build to `docs/` directory or use `gh-pages` branch
   - Set `baseURL` correctly for GitHub Pages URL

**Diataxis Structure in Hugo**:
```
docs/content/
├── tutorial/          # Learning-oriented (getting started)
│   ├── _index.md
│   ├── 01-installation.md
│   └── 02-first-archive.md
├── how-to/            # Task-oriented (practical guides)
│   ├── _index.md
│   ├── backup-channel.md
│   ├── filter-by-license.md
│   └── setup-ci-workflow.md
├── reference/         # Information-oriented (API docs, CLI reference)
│   ├── _index.md
│   ├── cli-commands.md
│   ├── api-reference.md
│   └── configuration.md
└── explanation/       # Understanding-oriented (concepts, architecture)
    ├── _index.md
    ├── architecture.md
    ├── git-annex-integration.md
    └── incremental-updates.md
```

**Congo Theme Configuration**:
- Supports modern Hugo features (menus, taxonomies, search)
- Dark mode support built-in
- Responsive design
- Syntax highlighting for code blocks

**Decision**: Use Hugo extended + Congo theme with Diataxis structure

**Rationale**:
- Aligns with spec requirements (Hugo + Congo)
- Diataxis provides clear documentation organization
- GitHub Pages deployment straightforward with Hugo

**Implementation checklist**:
- [ ] Initialize Hugo site in `docs/`
- [ ] Add Congo theme as submodule
- [ ] Configure `config.toml` for GitHub Pages
- [ ] Create Diataxis content structure
- [ ] Set up GitHub Actions workflow for auto-deployment

---

### 6. Git-annex Special Remotes for CI/CD

**Question**: How should git-annex special remotes be configured for automated CI/CD workflows?

**Context**:
- FR-086: Support git-annex special remotes (S3, WebDAV, directory, etc.)
- FR-085: Two CI modes (index-only vs full backup)
- Need authentication handling in CI environments

**Research**:

**Git-annex Special Remote Types**:

1. **S3**: AWS S3 or compatible (Wasabi, Backblaze B2, MinIO)
   - Pros: Scalable, cheap, widely supported
   - Auth: Access key + secret (via environment variables)
   - Configuration: `git annex initremote s3remote type=S3 ...`

2. **WebDAV**: WebDAV-compatible storage (Nextcloud, ownCloud)
   - Pros: Self-hosted option, FOSS-friendly
   - Auth: Username + password (via environment variables)
   - Configuration: `git annex initremote webdav type=webdav url=...`

3. **Directory**: Local or network-mounted directory
   - Pros: Simple, no external dependencies
   - Auth: File system permissions
   - Configuration: `git annex initremote backup type=directory directory=/path/to/backup`

4. **Rclone**: Bridge to any cloud provider (100+ supported)
   - Pros: Maximum flexibility, supports everything
   - Auth: Rclone config file
   - Configuration: `git annex initremote rclone type=external externaltype=rclone ...`

**CI/CD Authentication Pattern**:
```yaml
# .github/workflows/update-archive.yml
env:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
  AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
  # or
  WEBDAV_USERNAME: ${{ secrets.WEBDAV_USERNAME }}
  WEBDAV_PASSWORD: ${{ secrets.WEBDAV_PASSWORD }}

steps:
  - name: Setup git-annex special remote
    run: |
      git annex enableremote s3remote
      # or git annex initremote if first time
```

**Two-Mode CI Strategy**:

**Mode 1: Index-only (fast, frequent)**:
```yaml
# Runs daily
- Fetch metadata, comments, captions (small files)
- Commit to git (not git-annex)
- Push to GitHub/Codeberg (just git repo)
- No video downloads, no special remote interaction
```

**Mode 2: Full backup (slow, less frequent)**:
```yaml
# Runs weekly or on-demand
- Fetch all content including videos
- Add to git-annex
- Push content to special remote
- Push git index to GitHub/Codeberg
```

**Decision**: Support directory, S3, and rclone special remotes with two-mode CI workflows

**Rationale**:
- **Directory**: Simple, good for self-hosted setups
- **S3**: Scalable, widely available, cost-effective
- **Rclone**: Maximum flexibility for diverse environments
- **Two modes**: Balance between frequent metadata updates and less frequent full backups
- **Constitution alignment**: Principle XI (Resource Efficiency) - avoid unnecessary downloads/uploads

**Implementation pattern**:
```python
# annextube/services/git_annex.py

def init_special_remote(self, remote_name, remote_type, **config):
    """Initialize a git-annex special remote."""
    # Use datasalad to run: git annex initremote ...
    pass

def enable_special_remote(self, remote_name):
    """Enable an existing special remote (for CI)."""
    # Use datasalad to run: git annex enableremote ...
    pass

def copy_to_remote(self, files, remote_name):
    """Copy git-annex files to a special remote."""
    # Use datasalad to run: git annex copy --to=remote_name files
    pass
```

---

## Summary of Decisions

| Unknown | Decision | Rationale |
|---------|----------|-----------|
| Frontend framework | **Svelte** | Smallest bundle (15-20KB), compiles to vanilla JS, excellent file:// protocol support, aligns with resource efficiency |
| Frontend testing | **Vitest + @testing-library/svelte + Playwright** | Fast (Vitest), industry best practice (Testing Library), multi-browser + file:// support (Playwright) |
| datasalad usage | **Primary interface for git/git-annex** | DRY principle, leverages DataLad ecosystem, efficient command execution |
| yt-dlp integration | **Python API with lazy download + archive file** | Better control, efficient incremental updates, aligns with FR-004 |
| Hugo documentation | **Hugo extended + Congo theme + Diataxis** | Spec requirement, clear documentation organization, GitHub Pages compatible |
| Git-annex remotes | **Support directory, S3, rclone with two-mode CI** | Flexibility, scalability, resource efficiency (index-only vs full backup) |

## Action Items for Phase 1

1. ✅ Update Technical Context in plan.md with frontend framework decision
2. Create data-model.md with entity definitions (Video, Channel, Playlist, Comment, Caption, SyncState, FilterConfig)
3. Generate API contracts in contracts/ (OpenAPI/JSON schema)
4. Create quickstart.md (tutorial-style quick start guide)
5. Update .claude/CLAUDE.md with technology stack context (Svelte, Vitest, Playwright, datasalad, yt-dlp)
6. Initialize Hugo documentation structure (deferred to implementation phase)
7. Add LICENSE file to repository (FOSS compliance)

## References

- datasalad: https://hub.datalad.org/datalad/datasalad
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- Svelte: https://svelte.dev/
- Vitest: https://vitest.dev/
- Playwright: https://playwright.dev/
- Hugo Congo theme: https://github.com/jpanther/congo
- Diataxis framework: https://diataxis.fr/
- Git-annex special remotes: https://git-annex.branchable.com/special_remotes/
