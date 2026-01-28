# Frontend Development TODO

**Feature**: Client-side web interface for browsing YouTube archives
**User Story**: US4 - Browse and Search Archive via Web Interface (Priority: P2)
**Status**: Not Started
**Target**: Phase 6

---

## Architecture Analysis

**📖 See**: [FRONTEND_ARCHITECTURE_COMPARISON.md](./FRONTEND_ARCHITECTURE_COMPARISON.md)

A comprehensive analysis of the mykrok fitness tracker frontend has been completed. Key lessons adopted:

### ✅ Patterns Adopted from MyKrok

1. **Lightweight TSV Parser**: Vanilla utility module (632 bytes in mykrok) for fast data loading
2. **On-Demand Loading**: Load TSV for lists (fast), JSON for details (lazy)
3. **Hash-Based URL State**: Full state in URL for shareable links and file:// compatibility
4. **Jest + jsdom for Utilities**: Fast unit tests without browser overhead
5. **Python CLI Integration**: Backend generates and builds frontend in one command

### ❌ Patterns NOT Adopted

1. **Vanilla JS Monolithic File**: Use Svelte components instead (mykrok's 5055-line file is hard to maintain)
2. **No Component Tests**: Add @testing-library/svelte (mykrok only tests utilities)
3. **Manual DOM Manipulation**: Use Svelte reactivity (cleaner than `document.getElementById()`)

**Result**: Hybrid approach combining mykrok's simple data utilities with Svelte's component model for best of both worlds.

---

## Overview

Build a pure client-side web interface using Svelte that allows users to browse their YouTube archives offline (via file:// protocol), with search, filtering, video playback with captions, and comment viewing.

### Key Requirements

- **Client-side only**: No backend server required
- **file:// protocol support**: Works locally without web server
- **Fast loading**: Load from TSV files for quick initialization (mykrok pattern)
- **Video playback**: HTML5 video with caption selection
- **Comments**: Display with threading support
- **Search & Filter**: Real-time search across titles/descriptions, date range filtering
- **Shareable URLs**: Hash-based routing preserves filter/view state (mykrok pattern)

---

## Technology Stack

### Core Framework
- **Framework**: Svelte 4+ (NOT vanilla JS - see architecture comparison)
- **Language**: TypeScript (strict mode)
- **Build Tool**: Vite (fast dev + optimized production builds)
- **Routing**: Hash-based routing (for file:// protocol compatibility)

### Data Layer (Inspired by MyKrok)
- **TSV Parser**: Lightweight vanilla utility (no dependencies)
- **Data Loading**: TSV for lists, on-demand JSON for details
- **URL State**: Custom URLState manager (encode/decode URL hash)

### Testing Strategy
- **Utility Tests**: Jest + jsdom (for TSV parser, search, etc.)
- **Component Tests**: Vitest + @testing-library/svelte
- **E2E Tests**: Playwright (real browser)

### Libraries
- **Search**: Fuse.js or MiniSearch (client-side full-text)
- **Video**: Native `<video>` element (no library needed)
- **Icons**: lucide-svelte (modern icon set)
- **Date**: date-fns (lightweight)

---

## Phase 6: Tasks Breakdown

### Setup & Infrastructure (2 tasks)

#### T014 [P] Setup frontend project structure
**Status**: ❌ Not Started
**Dependencies**: T001 (Python package structure - ✅ Done)

**Deliverables**:
```
frontend/
├── src/
│   ├── components/          # Svelte components
│   │   ├── VideoList.svelte
│   │   ├── VideoPlayer.svelte
│   │   ├── FilterPanel.svelte
│   │   └── CommentView.svelte
│   ├── pages/               # Page components
│   │   ├── Index.svelte
│   │   └── VideoDetail.svelte
│   ├── services/            # Data loading, search
│   │   ├── data_loader.ts
│   │   ├── search.ts
│   │   └── caption_service.ts
│   ├── types/               # TypeScript types
│   │   └── models.ts        # Generated from JSON Schema
│   ├── lib/                 # Utilities
│   │   └── routing.ts       # Hash-based router
│   ├── App.svelte           # Root component
│   └── main.ts              # Entry point
├── tests/
│   ├── unit/                # Component unit tests
│   ├── integration/         # Integration tests
│   └── e2e/                 # Playwright E2E tests
├── public/                  # Static assets
├── package.json
├── tsconfig.json
├── vite.config.ts
└── playwright.config.ts
```

**Action Items**:
1. Create frontend directory structure
2. Initialize npm project: `npm init -y`
3. Install dependencies:
   ```bash
   npm install svelte vite @sveltejs/vite-plugin-svelte
   npm install -D typescript @tsconfig/svelte vitest @testing-library/svelte playwright
   ```
4. Configure `vite.config.ts` for hash-based routing:
   ```typescript
   export default defineConfig({
     base: './',  // Relative paths for file:// protocol
     build: {
       outDir: '../web',  // Output to archive's web/ directory
       emptyOutDir: true,
     },
   })
   ```
5. Configure `tsconfig.json` with strict mode
6. Set up Vitest config for component testing
7. Set up Playwright for E2E tests

---

#### T015 [P] Configure frontend build tooling
**Status**: ❌ Not Started
**Dependencies**: T014

**Goals**:
- Vite build outputs static assets to `web/` directory
- Hash-based routing for file:// protocol support
- TypeScript compilation with strict type checking
- Source maps for debugging

**Action Items**:
1. Configure Vite build:
   - Output to `web/index.html` and `web/assets/`
   - Inline small assets (base64)
   - Code splitting for better caching
   - Minification + tree shaking
2. Add npm scripts to `package.json`:
   ```json
   {
     "scripts": {
       "dev": "vite",
       "build": "vite build",
       "preview": "vite preview",
       "test": "vitest",
       "test:e2e": "playwright test",
       "type-check": "tsc --noEmit"
     }
   }
   ```
3. Verify file:// protocol works:
   - Test hash routing: `file:///path/to/web/index.html#/video/abc123`
   - Test relative paths load correctly
   - Test CORS doesn't block local file access

---

### Type Generation (1 task)

#### T058 [P] Generate TypeScript types from JSON Schema
**Status**: ❌ Not Started
**Dependencies**: T014, existing `annextube/schema/models.json`

**FR Mapping**: Supports all FRs by ensuring type safety between backend JSON and frontend

**Action Items**:
1. Install json-schema-to-typescript:
   ```bash
   npm install -D json-schema-to-typescript
   ```
2. Create generation script `scripts/generate-types.js`:
   ```javascript
   import { compileFromFile } from 'json-schema-to-typescript'

   compileFromFile('../annextube/schema/models.json')
     .then(ts => writeFileSync('src/types/models.ts', ts))
   ```
3. Add to package.json scripts:
   ```json
   "generate-types": "node scripts/generate-types.js"
   ```
4. Run and verify types are generated for:
   - `Video` interface
   - `Playlist` interface
   - `Channel` interface
   - `Author` interface
   - `Caption` interface
5. Add pre-build hook to regenerate types automatically

**Validation**:
- TypeScript compiles without errors
- All JSON data from backend validates against generated types
- IDE provides autocomplete for all model fields

---

### Utility Layer (1 task) - **Inspired by MyKrok**

#### T070 [P] Create lightweight TSV parser utility
**Status**: ❌ Not Started
**Dependencies**: T014
**Pattern**: Adopted from mykrok (632-byte lightweight parser)

**FR Mapping**: Foundation for FR-039 (fast TSV loading)

**File**: `frontend/src/utils/tsv-parser.ts`

**Goals**:
- Parse TSV files without dependencies (pure TypeScript)
- Handle Unix and Windows line endings
- Support empty fields
- Keep implementation <100 lines

**Implementation** (inspired by mykrok's approach):
```typescript
/**
 * Lightweight TSV parser with no dependencies.
 * Based on mykrok's proven 632-byte implementation.
 */
export function parseTSV(tsvText: string): Record<string, string>[] {
    const lines = tsvText.split(/\r?\n/);
    if (lines.length < 2) return [];

    const headers = lines[0].split('\t');
    return lines.slice(1)
        .filter(line => line.trim())  // Skip empty lines
        .map(line => {
            const values = line.split('\t');
            return Object.fromEntries(
                headers.map((header, i) => [header, values[i] || ''])
            );
        });
}
```

**Action Items**:
1. Create `frontend/src/utils/tsv-parser.ts` with parseTSV function
2. Create `frontend/tests/unit/tsv-parser.test.ts` with Jest:
   ```typescript
   import { parseTSV } from '@/utils/tsv-parser';

   describe('TSV Parser', () => {
       test('parses videos.tsv format', () => {
           const tsv = 'video_id\ttitle\tduration\nabc123\tTest Video\t300';
           const result = parseTSV(tsv);
           expect(result[0]).toEqual({
               video_id: 'abc123',
               title: 'Test Video',
               duration: '300'
           });
       });

       test('handles Windows CRLF line endings', () => {
           const tsv = 'id\tname\r\n1\tAlice\r\n2\tBob';
           expect(parseTSV(tsv)).toHaveLength(2);
       });

       test('handles empty fields', () => {
           const tsv = 'id\tname\t1\t';
           expect(parseTSV(tsv)[0].name).toBe('');
       });
   });
   ```
3. Configure Jest to run with `--experimental-vm-modules` (for ES6 modules)
4. Add npm script: `"test:utils": "node --experimental-vm-modules node_modules/jest/bin/jest.js tests/unit"`

**Validation**:
- All test cases pass
- Parser handles real videos.tsv and playlists.tsv files
- No external dependencies added
- TypeScript strict mode passes

---

### Data Loading & Services (2 tasks)

#### T063 Implement data loader service
**Status**: ❌ Not Started
**Dependencies**: T070 (TSV parser), T058 (types)

**FR Mapping**: FR-039 (load metadata from TSV files)

**File**: `frontend/src/services/data_loader.ts`

**Pattern**: Inspired by mykrok's on-demand loading strategy

**Features**:
- Load `videos/videos.tsv` and parse into Video[] (fast initial load)
- Load `playlists/playlists.tsv` and parse into Playlist[]
- Load individual `videos/{video_id}/metadata.json` **on demand** (lazy loading)
- Load `videos/{video_id}/comments.json` **on demand** (mykrok pattern)
- Load `videos/{video_id}/captions.tsv` to list available captions
- Handle file:// protocol CORS restrictions
- Implement in-memory caching to avoid re-parsing TSV files

**API Design** (uses TSV parser from T070):
```typescript
import { parseTSV } from '@/utils/tsv-parser';

export class DataLoader {
  // Fast: Load summary data from TSV (mykrok pattern)
  async loadVideos(): Promise<Video[]> {
    const response = await fetch('videos/videos.tsv');
    const text = await response.text();
    return parseTSV(text).map(row => ({
      video_id: row.video_id,
      title: row.title,
      duration: parseInt(row.duration),
      // ... map all TSV fields
    }));
  }

  async loadPlaylists(): Promise<Playlist[]>
  async loadVideoMetadata(videoId: string): Promise<Video>
  async loadComments(videoId: string): Promise<Comment[]>
  async loadCaptions(videoId: string): Promise<Caption[]>
}
```

**Action Items**:
1. Implement TSV parser (tab-separated, handle quotes, newlines)
2. Implement JSON loader with fetch() API
3. Add error handling for missing files
4. Add caching layer (Map<string, T>)
5. Write unit tests with mock TSV/JSON data
6. Test with real archive data (test-archives/apopyk/)

**Challenges**:
- file:// protocol may restrict some fetch() operations - test thoroughly
- TSV parsing edge cases (escaped tabs, quotes, newlines in descriptions)
- Large archives (1000+ videos) - consider lazy loading

---

#### T064 Implement client-side search
**Status**: ❌ Not Started
**Dependencies**: T063 (data loader)

**FR Mapping**: FR-042 (text search across titles and descriptions)

**File**: `frontend/src/services/search.ts`

**Features**:
- Full-text search across video titles, descriptions, tags
- Case-insensitive search
- Support multiple search terms (AND logic)
- Search result ranking by relevance
- Fast performance (<100ms for 1000 videos)

**API Design**:
```typescript
export class SearchService {
  constructor(videos: Video[])
  search(query: string): Video[]
  filterByDateRange(videos: Video[], start: Date, end: Date): Video[]
  filterByChannel(videos: Video[], channelId: string): Video[]
  filterByPlaylist(videos: Video[], playlistId: string): Video[]
  filterByTags(videos: Video[], tags: string[]): Video[]
}
```

**Action Items**:
1. Implement tokenizer (split query into terms, handle quotes for phrases)
2. Implement search indexing (pre-process titles/descriptions into searchable index)
3. Implement ranking algorithm (title matches > description matches)
4. Add filter functions for date, channel, playlist, tags
5. Write unit tests with various search queries
6. Performance test with 1000 video dataset

**Performance Considerations**:
- Pre-build search index on data load
- Use efficient string matching (avoid regex if slow)
- Consider using Fuse.js or similar lightweight search library

---

### UI Components (4 tasks)

#### T059 [P] Create VideoList component
**Status**: ❌ Not Started
**Dependencies**: T063 (data loader), T064 (search)

**FR Mapping**: FR-043 (display thumbnails, metadata, allow playback)

**File**: `frontend/src/components/VideoList.svelte`

**Features**:
- Display videos in grid or list view
- Show thumbnail, title, duration, upload date, view count
- Click to navigate to video detail page
- Responsive layout (mobile, tablet, desktop)
- Infinite scroll or pagination for large archives
- Loading states and error handling

**Props**:
```typescript
export let videos: Video[]
export let layout: 'grid' | 'list' = 'grid'
```

**Action Items**:
1. Create basic grid layout with CSS Grid
2. Add video card component (thumbnail + metadata)
3. Add click handler to navigate (hash routing)
4. Add responsive breakpoints
5. Add loading skeleton
6. Write component tests (render, click interaction)
7. Test with real archive (50+ videos)

**UI/UX Considerations**:
- Lazy load thumbnails (IntersectionObserver)
- Placeholder for missing thumbnails
- Date formatting (relative: "2 days ago" or absolute: "2024-01-15")
- Duration formatting (e.g., "1:23:45")

---

#### T060 [P] Create VideoPlayer component
**Status**: ❌ Not Started
**Dependencies**: T063 (data loader)

**FR Mapping**: FR-043, FR-045 (video playback with caption selection)

**File**: `frontend/src/components/VideoPlayer.svelte`

**Features**:
- HTML5 video player with native controls
- Caption/subtitle track selection dropdown
- Load VTT files from `videos/{video_id}/video.{lang}.vtt`
- Support multiple caption languages
- Auto-select default caption (user's browser language or 'en')
- Playback controls: play/pause, seek, volume, fullscreen
- Keyboard shortcuts (space=play/pause, arrow keys=seek)

**Props**:
```typescript
export let videoPath: string  // Relative path to video.mkv
export let captions: Caption[] // Available caption tracks
```

**Action Items**:
1. Create basic video element with src
2. Add caption track elements dynamically
3. Create caption selector UI (dropdown or buttons)
4. Handle caption track switching
5. Add keyboard shortcuts
6. Style player controls (optional, or use native)
7. Write component tests (render, caption switching)
8. Test with real video + multiple captions

**Technical Notes**:
- VTT files should be served from same origin (file://)
- May need to use `<track>` elements with `default` attribute
- Caption paths: `videos/{video_id}/video.{lang}.vtt` (not `{video_id}.{lang}.vtt`)

---

#### T061 [P] Create FilterPanel component
**Status**: ❌ Not Started
**Dependencies**: T064 (search service)

**FR Mapping**: FR-040, FR-041 (filter by date, channel, playlist, tags)

**File**: `frontend/src/components/FilterPanel.svelte`

**Features**:
- Text search input (live search)
- Date range picker (from/to dates)
- Channel dropdown/select
- Playlist dropdown/select (show all playlists from archive)
- Tag multi-select or autocomplete
- "Clear filters" button
- Active filter badges/chips
- Filter state persists in URL hash

**Props**:
```typescript
export let onFilterChange: (filters: FilterState) => void
export let channels: Channel[]
export let playlists: Playlist[]
export let allTags: string[]
```

**Action Items**:
1. Create search input with debounce (300ms)
2. Add date range inputs (HTML date inputs or date picker library)
3. Add channel/playlist dropdowns
4. Add tag multi-select (checkbox list or tag input)
5. Implement filter state management (reactive Svelte store)
6. Add "Clear all" button
7. Show active filters as removable chips
8. Write component tests (filter interactions)

**UI/UX Considerations**:
- Responsive: collapsible on mobile
- Show filter counts (e.g., "5 playlists, 12 tags")
- Persist filter state in URL hash for shareability

---

#### T062 [P] Create CommentView component
**Status**: ❌ Not Started
**Dependencies**: T063 (data loader)

**FR Mapping**: FR-044 (display comments with threading)

**File**: `frontend/src/components/CommentView.svelte`

**Features**:
- Display comment text, author, timestamp, like count
- Show comment threading (replies nested under parent)
- Expandable replies ("Show N replies" button)
- Sort options: top (by likes), newest, oldest
- Load comments from `videos/{video_id}/comments.json`
- Handle long comment text (show more/less)
- Link author names to author filter

**Props**:
```typescript
export let comments: Comment[]  // Flat list with parent_id references
```

**Action Items**:
1. Build comment tree structure from flat list (group by parent_id)
2. Create Comment component (single comment card)
3. Add recursive rendering for replies
4. Add "Show replies" expand/collapse
5. Add sort dropdown (top/newest/oldest)
6. Format timestamps ("2 days ago")
7. Add "show more" for long comment text
8. Write component tests (render, expand replies, sort)

**Data Structure** (from `comments.json`):
```json
{
  "id": "comment_id",
  "text": "Comment text",
  "author": "Author Name",
  "author_id": "UC...",
  "published_at": "2024-01-15T10:30:00Z",
  "like_count": 42,
  "parent_id": null  // or parent comment ID for replies
}
```

---

### Pages (2 tasks)

#### T065 Create Index page
**Status**: ❌ Not Started
**Dependencies**: T059 (VideoList), T061 (FilterPanel), T064 (search)

**FR Mapping**: FR-037, FR-038, FR-040, FR-041, FR-042

**File**: `frontend/src/pages/Index.svelte`

**Features**:
- Main landing page showing all videos
- FilterPanel + VideoList layout
- Archive statistics (total videos, channels, playlists)
- Apply filters and update video list
- URL hash updates on filter changes

**Layout**:
```
┌─────────────────────────────────────┐
│ Header: Archive Title, Stats        │
├─────────────────────────────────────┤
│ FilterPanel (sidebar or top)        │
├─────────────────────────────────────┤
│ VideoList (grid or list)            │
│  ┌───┐ ┌───┐ ┌───┐                │
│  │ V │ │ V │ │ V │                │
│  └───┘ └───┘ └───┘                │
└─────────────────────────────────────┘
```

**Action Items**:
1. Create page layout (2-column: filters + videos)
2. Load videos and playlists on mount
3. Wire FilterPanel to update video list
4. Add archive statistics display
5. Implement URL hash reading/writing
6. Add loading states
7. Write E2E test (Playwright: load page, apply filter, verify results)

---

#### T066 Create VideoDetail page
**Status**: ❌ Not Started
**Dependencies**: T060 (VideoPlayer), T062 (CommentView), T063 (data loader)

**FR Mapping**: FR-043, FR-044, FR-045

**File**: `frontend/src/pages/VideoDetail.svelte`

**Features**:
- Load and display video metadata
- VideoPlayer component with video file
- Video description (full text, expandable)
- Video metadata table (upload date, duration, views, license, etc.)
- CommentView component
- "Back to list" navigation
- Related videos (from same playlist or channel)

**Layout**:
```
┌─────────────────────────────────────┐
│ VideoPlayer                          │
├─────────────────────────────────────┤
│ Title, Channel, Upload Date          │
│ Description (expandable)             │
│ Metadata (tags, license, etc.)      │
├─────────────────────────────────────┤
│ Comments (CommentView)               │
└─────────────────────────────────────┘
```

**Action Items**:
1. Extract video ID from URL hash
2. Load video metadata from JSON
3. Render VideoPlayer with video path and captions
4. Display video description and metadata
5. Load and render comments
6. Add "Back" button
7. Add related videos section
8. Write E2E test (Playwright: navigate to video, play video, view comments)

---

### Routing & State (2 tasks)

#### T067 Configure hash-based routing
**Status**: ❌ Not Started
**Dependencies**: T065, T066 (pages)

**FR Mapping**: FR-038 (file:// protocol support), FR-046 (shareable URLs)

**File**: `frontend/src/lib/routing.ts`

**Features**:
- Hash-based router (file:// protocol compatible)
- Route definitions:
  - `#/` → Index page
  - `#/video/:videoId` → VideoDetail page
  - `#/playlist/:playlistId` → Playlist view (optional)
- Navigation functions (navigate, back)
- Current route store (reactive)

**API Design**:
```typescript
export const routes = {
  index: '/',
  video: (id: string) => `/video/${id}`,
  playlist: (id: string) => `/playlist/${id}`,
}

export function navigate(path: string): void
export const currentRoute: Readable<Route>
```

**Action Items**:
1. Implement hash change listener
2. Create route parser (extract params from hash)
3. Create navigation function (update window.location.hash)
4. Create Svelte store for current route
5. Wire up pages to router
6. Write tests (route parsing, navigation)

**Reference**: See research.md for file:// routing patterns

---

#### T068 Implement shareable URL state **[MyKrok Pattern]**
**Status**: ❌ Not Started
**Dependencies**: T067 (routing)

**FR Mapping**: FR-046 (preserve filter/view state in URL)
**Pattern**: Directly adopted from mykrok's URLState manager

**Features**:
- Encode filter state in URL hash (full state for sharing)
- Decode filter state from URL hash (restore on load)
- Update URL when filters change (debounced)
- Restore filter state on page load

**URL Format** (inspired by mykrok):
```
#/?search=datalad&from=2024-01-01&to=2024-12-31&playlist=UCx1
#/video/abc123?t=120               # Video at timestamp (like mykrok's photo index)
#/video/abc123?comment=xyz         # Jump to comment
#/playlist/PL456?video=3           # Playlist at video 3
```

**Implementation** (mykrok's encode/decode pattern):
```typescript
// frontend/src/lib/url-state.ts
export class URLState {
    // Encode state to URL hash (like mykrok)
    static encode(state: AppState): string {
        const params = new URLSearchParams();
        if (state.query) params.set('q', state.query);
        if (state.dateFrom) params.set('from', state.dateFrom);
        if (state.dateTo) params.set('to', state.dateTo);
        if (state.playlist) params.set('playlist', state.playlist);
        if (state.videoTimestamp) params.set('t', state.videoTimestamp.toString());
        const queryStr = params.toString();
        return '#/' + state.view + (queryStr ? '?' + queryStr : '');
    }

    // Decode state from URL hash (like mykrok)
    static decode(): AppState {
        const hash = location.hash.slice(2) || 'videos';
        const [path, queryStr] = hash.split('?');
        const params = new URLSearchParams(queryStr || '');
        return {
            view: path.split('/')[0] as View,
            query: params.get('q') || '',
            dateFrom: params.get('from') || '',
            dateTo: params.get('to') || '',
            playlist: params.get('playlist') || '',
            videoTimestamp: params.get('t') ? parseInt(params.get('t')) : null
        };
    }

    // Update URL without navigation (like mykrok's URLState.update)
    static update(partialState: Partial<AppState>): void {
        const current = this.decode();
        const newState = { ...current, ...partialState };
        history.replaceState(null, '', this.encode(newState));
    }
}
```

**Action Items**:
1. Create URLState class with encode/decode methods (like mykrok)
2. Integrate with Svelte stores (state → URL, URL → state)
3. Update hash when filters change (debounced 500ms)
4. Read filters from hash on mount
5. Write Jest tests (serialization roundtrip):
   ```typescript
   test('encode/decode roundtrip', () => {
       const state = { view: 'videos', query: 'react', dateFrom: '2024-01-01' };
       const encoded = URLState.encode(state);
       const decoded = URLState.decode(encoded);
       expect(decoded).toEqual(state);
   });
   ```

**Reference**: See mykrok's URLState implementation in map-browser.js:318-399

---

### Build & Generation (3 tasks)

#### T069 [P] Build frontend to static assets
**Status**: ❌ Not Started
**Dependencies**: T015 (build tooling), T065, T066 (pages complete)

**FR Mapping**: FR-037 (generate client-side web interface)

**Goal**: `npm run build` outputs production-ready static files to `web/` directory

**Action Items**:
1. Configure Vite to output to `web/` (relative to project root)
2. Verify output structure:
   ```
   web/
   ├── index.html
   └── assets/
       ├── index-[hash].js
       ├── index-[hash].css
       └── [other-chunks]-[hash].js
   ```
3. Test build output works via file:// protocol
4. Add .gitignore entry for `web/` (generated, not committed)
5. Document build process in README

**Validation**:
- `file:///path/to/archive/web/index.html` loads successfully
- All assets load (no 404s)
- Routing works (hash navigation)
- Videos and captions load from archive

---

#### T056 [P] Implement generate-web command
**Status**: ❌ Not Started
**Dependencies**: T069 (frontend builds)

**FR Mapping**: FR-052 (CLI command to generate web interface)

**File**: `annextube/cli/generate_web.py`

**Command**:
```bash
annextube generate-web --output-dir /path/to/archive
```

**Features**:
- Trigger frontend build (`npm run build` in frontend/)
- Copy built files to `{archive}/web/`
- Verify archive has required files (videos.tsv, playlists.tsv)
- Output success message with path to index.html

**Action Items**:
1. Create `generate_web.py` CLI command
2. Add subprocess call to `npm run build`
3. Copy `frontend/web/` → `{archive}/web/`
4. Add validation checks (TSV files exist)
5. Add progress output
6. Write integration test (generate-web on test archive)

**Error Handling**:
- If npm not installed → error message
- If frontend/ not found → error message
- If build fails → show npm error

---

#### T057 [P] Implement WebGenerator service
**Status**: ❌ Not Started
**Dependencies**: T056 (generate-web command)

**FR Mapping**: Orchestrate frontend build + data validation

**File**: `annextube/services/web_generator.py`

**Features**:
- Validate archive structure (required files exist)
- Run frontend build
- Copy output to archive
- Generate data manifest (list of available videos, playlists)
- Optional: pre-generate search index

**API Design**:
```python
class WebGenerator:
    def __init__(self, archive_path: Path):
        self.archive_path = archive_path

    def validate_archive(self) -> bool:
        """Check archive has required structure."""

    def build_frontend(self) -> None:
        """Run npm build in frontend/."""

    def copy_to_archive(self) -> None:
        """Copy web/ output to archive."""

    def generate_manifest(self) -> None:
        """Generate data manifest for quick loading."""
```

**Action Items**:
1. Implement archive validation
2. Implement frontend build trigger
3. Implement file copying with progress
4. Add optional manifest generation
5. Write unit tests with mock archive

---

### Testing & Validation (integrated throughout)

#### Unit Tests (Vitest)
- Data loader (TSV parsing, JSON loading, caching)
- Search service (query parsing, ranking, filtering)
- Component rendering (VideoList, VideoPlayer, FilterPanel, CommentView)

#### Integration Tests (@testing-library/svelte)
- Filter panel updates video list
- Search updates video list
- Video player loads captions
- Comments display with threading

#### E2E Tests (Playwright)
- **Test 1**: Load index, see video grid
- **Test 2**: Apply filter, verify filtered results
- **Test 3**: Search keyword, verify results
- **Test 4**: Navigate to video, play video, view comments
- **Test 5**: Select caption language, verify captions display
- **Test 6**: Share URL with filters, verify state restores

**Test Data**: Use `test-archives/apopyk/` (53 videos, 7 playlists, captions, comments)

---

## Success Criteria (FR Validation)

From spec.md FR-037 to FR-047:

- ✅ **FR-037**: Client-side web interface generated (single HTML + assets)
- ✅ **FR-038**: Works offline via file:// protocol without server
- ✅ **FR-039**: Loads metadata from TSV files on demand
- ✅ **FR-040**: Filters videos by date range
- ✅ **FR-041**: Filters videos by channel, playlist, tags
- ✅ **FR-042**: Text search across titles and descriptions
- ✅ **FR-043**: Displays thumbnails, metadata, allows playback
- ✅ **FR-044**: Displays comments with threading
- ✅ **FR-045**: Caption selection during playback
- ✅ **FR-046**: Shareable URLs preserve filter/view state
- ✅ **FR-047**: Export captions (deferred to future phase)
- ✅ **FR-052**: CLI command `annextube generate-web` exists

---

## Performance Targets (from spec.md)

- **SC-003**: Web interface loads and displays 1000 videos in under 3 seconds
- **SC-006**: Search finds specific video in under 2 seconds
- **SC-009**: Works identically locally (file://) or via web hosting

---

## Deferred Features (Future Phases)

- **T084**: External service integration for caption editing (LLM integration) - User Story 7
- **T086**: Publish mode with `--base-url` for web hosting - User Story 8
- Mobile-optimized responsive design (works but not optimized)
- Progressive Web App (PWA) features
- Dark mode toggle
- Playlist detail page

---

## Development Workflow

### Phase 6 Execution Order

1. **Setup** (T014, T015) - 1-2 days
2. **Type Generation** (T058) - 0.5 day
3. **Services** (T063, T064) - 2-3 days
4. **Components** (T059, T060, T061, T062 in parallel) - 3-4 days
5. **Pages** (T065, T066) - 2 days
6. **Routing** (T067, T068) - 1 day
7. **Build & CLI** (T069, T056, T057) - 1-2 days
8. **Testing & Polish** - 2-3 days

**Total Estimate**: 12-18 days for full Phase 6

### Quick Start Path (MVP in 5-7 days)

1. Setup (T014, T015)
2. Types (T058)
3. Data loader (T063) - without caching
4. Simple search (T064) - basic filtering only
5. VideoList component (T059) - grid only
6. VideoPlayer component (T060) - basic playback
7. Index page (T065) - minimal layout
8. Hash routing (T067) - basic navigation
9. Build (T069, T056)

**Deferred for later**:
- CommentView (can show "Comments: N" count initially)
- FilterPanel (start with search input only)
- VideoDetail page (can watch inline from grid)
- Shareable URLs (basic routing first)

---

## Testing Against Real Data

Use existing test archives:
- `test-archives/apopyk/` - 53 videos, 7 playlists, 159 captions, 53 comments
- `test-archives/datalad/` - 44 videos, 4 playlists, 132 captions, 44 comments

Run `annextube generate-web` and test:
```bash
# After implementing generate-web:
cd test-archives/apopyk
annextube generate-web

# Open in browser:
open web/index.html  # macOS
xdg-open web/index.html  # Linux
start web/index.html  # Windows

# Or use file:// URL directly
```

---

## References

- **Spec**: `specs/001-youtube-backup/spec.md` (FR-037 to FR-047, User Story 4)
- **Tasks**: `specs/001-youtube-backup/tasks.md` (T056-T069, T084, T086)
- **Research**: `specs/001-youtube-backup/research.md` (file:// routing patterns)
- **Data Model**: `specs/001-youtube-backup/data-model.md` (Video, Playlist, Comment schemas)
- **JSON Schema**: `annextube/schema/models.json` (source for TypeScript types)
- **CLAUDE.md**: Technology stack decisions (Svelte, Vitest, Playwright)

---

## Questions to Resolve

1. **Svelte vs SvelteKit**: Use SvelteKit (overkill?) or plain Svelte + Vite (simpler)?
   - **Recommendation**: Plain Svelte + Vite (no need for server-side features)

2. **Date Picker Library**: Use native `<input type="date">` or library (flatpickr, date-fns)?
   - **Recommendation**: Start with native, add library if UX needs improvement

3. **Search Library**: Build from scratch or use Fuse.js/lunr.js?
   - **Recommendation**: Start custom (TSV is already fast), add library if performance issues

4. **Commit Strategy**: One large "Implement frontend" commit or task-by-task commits?
   - **Recommendation**: Task-by-task commits for better history

5. **CSS Framework**: TailwindCSS, plain CSS, or CSS-in-JS?
   - **Recommendation**: Plain CSS (Svelte scoped styles) for simplicity, no build dependencies

---

## Next Actions

To start Phase 6 frontend development:

1. Review this TODO with user for approval
2. Create feature branch: `git checkout -b 002-web-frontend`
3. Start with T014 (setup frontend structure)
4. Follow task order above
5. Commit after each task completion
6. Test with real archives after each component
7. Merge to master when FR-037 to FR-046 pass

---

**Last Updated**: 2026-01-28
**Status**: Ready for Implementation
