# Frontend Architecture Comparison: MyKrok vs Annextube

## Executive Summary

This document compares the mykrok frontend architecture (fitness activity tracker) with the planned annextube frontend (YouTube archive browser) to extract lessons and inform technology decisions.

**Recommendation**: **Proceed with Svelte + TypeScript** as planned, but adopt several mykrok patterns for data loading, testing, and state management. Use hybrid approach: Svelte components for UI, but vanilla utility modules for data parsing (inspired by mykrok).

---

## MyKrok Architecture Analysis

### Technology Stack

```
Backend (Python):
├── views/map.py              # Generates single HTML file
└── assets/                   # Static JS/CSS/libraries

Frontend (Vanilla JS):
├── map-browser.js (5055 lines)  # Monolithic application
├── tsv-utils.js (632 bytes)     # Lightweight TSV parser
├── date-utils.js (75 lines)     # Date formatting utilities
├── photo-viewer-utils.js        # Navigation helpers
├── leaflet/ (library)           # Map visualization
├── hyparquet/ (library)         # Parquet file reader
└── chart.js (library)           # Statistics charts

Testing:
└── Jest + jsdom                 # Unit tests for utilities only
```

### Key Patterns Observed

#### 1. **Python-Generated HTML Shell**
```python
# src/mykrok/views/map.py
def generate_browser(_data_dir: Path) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <style>
        /* All CSS embedded (no external stylesheet) */
        .app-header {{ ... }}
    </style>
</head>
<body>
    <div class="app-header">...</div>
    <div id="map"></div>
    <script src="assets/leaflet/leaflet.js"></script>
    <script type="module" src="assets/map-browser/map-browser.js"></script>
</body>
</html>"""
```

**Pros**:
- Zero build step (just copy files)
- Template + data generation in one place
- No frontend tooling required

**Cons**:
- CSS embedded (no hot reload during dev)
- Python must regenerate on any HTML change
- Limited templating (string concatenation)

#### 2. **Vanilla JS with ES6 Modules**
```javascript
// map-browser.js (5055 lines - monolithic!)
import { parquetReadObjects } from '../hyparquet/index.js';
import { getExpansionDays } from './date-utils.js';
import { parseTSV } from './tsv-utils.js';

// Global objects exposed to window for onclick handlers
const MapView = {
    allSessions: [],
    map: null,
    markers: {},

    init() {
        this.loadSessions();
        this.setupEventListeners();
    },

    async loadSessions() {
        const response = await fetch('athletes.tsv');
        const text = await response.text();
        this.allSessions = parseTSV(text);
    }
};

window.MapView = MapView;  // Expose for onclick="MapView.method()"
```

**Pros**:
- No build process (native ES6 modules)
- Easy to debug (no source maps)
- Minimal runtime overhead

**Cons**:
- 5055-line monolithic file (hard to maintain)
- No type checking
- Manual DOM manipulation (verbose)
- Global objects required for event handlers

#### 3. **Lightweight TSV Parser**
```javascript
// tsv-utils.js (632 bytes!)
export function parseTSV(tsvText) {
    const lines = tsvText.split(/\r?\n/);
    if (lines.length < 2) return [];

    const headers = lines[0].split('\t');
    const result = [];

    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split('\t');
        const obj = {};
        headers.forEach((header, j) => {
            obj[header] = values[j] || '';
        });
        result.push(obj);
    }
    return result;
}
```

**Pros**:
- Extremely lightweight (no dependencies)
- Fast parsing (simple string split)
- Easy to test and understand

**Cons**:
- No escaping support (breaks on tabs in values)
- All values are strings (no type coercion)

#### 4. **Hash-Based URL State Management**
```javascript
// URLState manager (embedded in map-browser.js)
const URLState = {
    encode(state) {
        const params = new URLSearchParams();
        if (state.athlete) params.set('a', state.athlete);
        if (state.dateFrom) params.set('from', state.dateFrom);
        if (state.track) params.set('track', state.track);
        return '#/' + state.view + (params.toString() ? '?' + params.toString() : '');
    },

    decode() {
        const hash = location.hash.slice(2) || 'map';
        const [path, queryStr] = hash.split('?');
        const params = new URLSearchParams(queryStr || '');
        return {
            view: path.split('/')[0] || 'map',
            athlete: params.get('a') || '',
            dateFrom: params.get('from') || ''
        };
    }
};
```

**Pros**:
- Simple, no router library
- Works with file:// protocol
- Full state in URL (shareable)

**Cons**:
- Manual parsing/encoding
- No route validation
- Must manually call decode() on hashchange

#### 5. **Jest + jsdom Testing**
```javascript
// tests/js/tsv-utils.test.js
import { parseTSV } from '../../src/mykrok/assets/map-browser/tsv-utils.js';

describe('parseTSV', () => {
    test('parses simple TSV', () => {
        const tsv = 'name\tage\nAlice\t30';
        const result = parseTSV(tsv);
        expect(result).toHaveLength(1);
        expect(result[0]).toEqual({ name: 'Alice', age: '30' });
    });
});
```

**package.json**:
```json
{
  "type": "module",
  "scripts": {
    "test": "node --experimental-vm-modules node_modules/jest/bin/jest.js"
  },
  "jest": {
    "testEnvironment": "jsdom",
    "roots": ["<rootDir>/tests/js"]
  }
}
```

**Pros**:
- Fast unit tests (no browser required)
- Tests ES6 modules directly
- jsdom provides DOM APIs

**Cons**:
- Limited to utility functions (no component tests)
- Must use experimental-vm-modules flag
- Cannot test interactive UI

#### 6. **On-Demand Data Loading**
```javascript
// Load TSV immediately
const athletesTSV = await fetch('athletes.tsv').then(r => r.text());
const athletes = parseTSV(athletesTSV);

// Load Parquet on demand (when user clicks track)
async zoomToSession(athlete, datetime) {
    const path = `athl=${athlete}/ses=${datetime}/tracking.parquet`;
    const trackPoints = await parquetReadObjects(path);
    this.drawTrack(trackPoints);
}
```

**Pros**:
- Fast initial load (just TSV)
- Binary format (Parquet) loaded only when needed
- Efficient bandwidth usage

**Cons**:
- Manual cache management
- Multiple fetch calls

---

## Annextube Requirements Analysis

### Data Characteristics Comparison

| Aspect | MyKrok | Annextube |
|--------|--------|-----------|
| **Primary data** | GPS tracks (Parquet) | Videos (annexed files) |
| **Metadata** | TSV (athletes, sessions) | TSV (videos, playlists, authors) + JSON per video |
| **Media** | Photos (JPEG) | Videos (MP4/WebM), thumbnails, captions (VTT) |
| **Volume** | 299 sessions, ~50MB | 1000s of videos, ~100GB+ |
| **Key feature** | Map visualization | Video player with captions |
| **Search** | Filter by date/type | Search titles/descriptions/comments |
| **Social** | Kudos, comments | YouTube comments (threaded) |

### Critical Differences

1. **Video playback**: Annextube needs native `<video>` element with VTT captions support. MyKrok just shows photos.

2. **Search complexity**: Annextube needs full-text search across titles, descriptions, tags, comments. MyKrok just filters by date/type.

3. **Volume**: Annextube archives can be massive (1000s of videos × 100MB each). MyKrok is small.

4. **Navigation**: Annextube needs hierarchical navigation (channels → playlists → videos). MyKrok is flat (athletes → sessions).

---

## Hybrid Approach Recommendation

### Adopt from MyKrok

#### ✅ 1. **Lightweight TSV Parser as Utility Module**
```typescript
// frontend/src/utils/tsv-parser.ts
export function parseTSV(tsvText: string): Record<string, string>[] {
    const lines = tsvText.split(/\r?\n/);
    if (lines.length < 2) return [];

    const headers = lines[0].split('\t');
    return lines.slice(1)
        .filter(line => line.trim())
        .map(line => {
            const values = line.split('\t');
            return Object.fromEntries(
                headers.map((header, i) => [header, values[i] || ''])
            );
        });
}
```

**Why**: Simple, no dependencies, easy to test. Works perfectly for videos.tsv, playlists.tsv.

#### ✅ 2. **Jest + jsdom for Utility Testing**
```javascript
// frontend/tests/unit/tsv-parser.test.ts
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
});
```

**Why**: Fast, no browser overhead. Perfect for data utilities.

#### ✅ 3. **Hash-Based Routing with URL State**
Use Svelte's built-in routing but follow mykrok's pattern of encoding full state in URL:

```
#/videos?q=react&sort=date
#/video/abc123?t=120        # Video at 2:00 timestamp
#/playlist/PL456?video=3    # Playlist at 3rd video
```

**Why**: Works with file:// protocol, shareable links, browser back/forward.

#### ✅ 4. **On-Demand JSON Loading**
```typescript
// Load TSV for list view (fast)
const videos = await loadVideosTSV();

// Load full JSON only when video clicked
async function loadVideoDetails(videoId: string) {
    const json = await fetch(`videos/${videoId}/metadata.json`);
    return json.json();
}
```

**Why**: Same pattern as mykrok - fast initial load, lazy-load details.

#### ✅ 5. **Python CLI Generates HTML Shell**
```python
# annextube/cli/generate_web.py
def generate_frontend(output_dir: Path) -> None:
    """Generate static web interface."""
    # Build Svelte app (npm run build)
    frontend_dist = Path(__file__).parent.parent.parent / "frontend/dist"

    # Copy built assets to archive
    web_dir = output_dir / "web"
    shutil.copytree(frontend_dist, web_dir, dirs_exist_ok=True)

    # Generate index.html with archive metadata
    (web_dir / "index.html").write_text(generate_html(output_dir))
```

**Why**: Keeps frontend generation as part of CLI workflow (like mykrok).

### Keep Svelte (Don't Copy Vanilla JS)

#### ❌ **Don't**: Use vanilla JS monolithic file

**Why NOT adopt mykrok's 5055-line map-browser.js**:
1. **Maintainability**: Hard to refactor, find bugs, add features
2. **No type safety**: Prone to runtime errors (typos, wrong types)
3. **No component reuse**: Duplicate code (PhotoPopup, FilterBar, etc.)
4. **Limited testing**: Can only test utilities, not UI components
5. **Verbose DOM manipulation**: `document.getElementById()`, `innerHTML =` everywhere

#### ✅ **Do**: Use Svelte for UI Components

```svelte
<!-- frontend/src/components/VideoCard.svelte -->
<script lang="ts">
    export let video: VideoMetadata;
    export let onPlay: (id: string) => void;
</script>

<div class="video-card" on:click={() => onPlay(video.video_id)}>
    <img src={video.thumbnail_url} alt={video.title} />
    <h3>{video.title}</h3>
    <span>{formatDuration(video.duration)}</span>
</div>

<style>
    .video-card {
        cursor: pointer;
        border-radius: 8px;
        overflow: hidden;
    }
    .video-card:hover {
        transform: scale(1.02);
    }
</style>
```

**Why Svelte is better**:
1. **Component reusability**: `<VideoCard>`, `<CommentThread>`, `<FilterPanel>` can be used anywhere
2. **Type safety**: TypeScript catches errors at compile time
3. **Reactive state**: `$:` syntax automatically updates DOM
4. **Scoped CSS**: No class name conflicts
5. **Testable**: `@testing-library/svelte` for component tests
6. **Small bundle**: Svelte compiles to efficient vanilla JS

---

## Final Technology Stack for Annextube

### Frontend Build
```
Framework: Svelte 4+
Language: TypeScript (strict mode)
Build Tool: Vite (fast dev server, optimized production)
Routing: Hash-based (custom or svelte-spa-router)
```

### Data Layer (Inspired by MyKrok)
```
Utilities:
├── tsv-parser.ts          # Lightweight TSV parser (like mykrok)
├── search-index.ts        # Full-text search (Fuse.js or MiniSearch)
└── video-loader.ts        # On-demand JSON loading

Testing:
└── Jest + jsdom           # For utilities (like mykrok)
```

### Component Testing
```
Unit/Integration: Vitest + @testing-library/svelte
E2E: Playwright (real browser tests)
```

### UI Components
```
Components:
├── VideoList.svelte       # Grid/list of videos
├── VideoPlayer.svelte     # <video> with VTT captions
├── CommentView.svelte     # Threaded comments
├── FilterPanel.svelte     # Search + filters
└── PlaylistView.svelte    # Ordered playlist
```

### Libraries
```
Video: Native <video> element (no library needed)
Search: Fuse.js or MiniSearch (client-side full-text)
Date: date-fns (lightweight, tree-shakeable)
Icons: lucide-svelte (modern icons)
```

---

## Lessons Applied

### 1. Data Loading Strategy

**From MyKrok**: TSV for fast initial load, on-demand details

**Annextube Implementation**:
```typescript
// 1. Load TSV immediately (videos list)
const videos = await loadVideosTSV();  // ~1-2 MB

// 2. Load JSON on demand (video details)
async function showVideoDetails(videoId: string) {
    const metadata = await fetch(`videos/${videoId}/metadata.json`);
    const comments = await fetch(`videos/${videoId}/comments.json`);
    // ...
}

// 3. Video file is git-annex symlink (not fetched to browser)
```

### 2. Testing Strategy

**From MyKrok**: Jest for utilities, no component tests

**Annextube Enhancement**:
```
Utility Tests (Jest + jsdom):
✓ tsv-parser.test.ts
✓ search-index.test.ts
✓ video-loader.test.ts

Component Tests (Vitest + @testing-library/svelte):
✓ VideoCard.test.ts
✓ CommentThread.test.ts
✓ FilterPanel.test.ts

E2E Tests (Playwright):
✓ video-playback.spec.ts
✓ caption-switching.spec.ts
✓ search-and-filter.spec.ts
```

### 3. URL State Management

**From MyKrok**: Full state in URL hash

**Annextube Implementation**:
```
#/videos                           # Default view
#/videos?q=react&sort=date         # Search + sort
#/video/abc123?t=120               # Video at timestamp
#/video/abc123?comment=xyz         # Jump to comment
#/playlist/PL456?video=3           # Playlist at video 3
```

### 4. Python CLI Integration

**From MyKrok**: Backend generates frontend

**Annextube Implementation**:
```bash
# CLI command (like mykrok generate-browser)
annextube generate-web --output-dir ~/my-archive

# Builds Svelte app and copies to archive/web/
# Generates index.html with archive stats
```

### 5. Modular Utilities

**From MyKrok**: Small focused utility files

**Annextube Implementation**:
```
utils/
├── tsv-parser.ts        # 50 lines (like mykrok's 632 bytes!)
├── duration-format.ts   # 20 lines
├── date-format.ts       # 30 lines
└── search-highlighter.ts
```

---

## Migration Path from MyKrok Patterns

If starting from scratch (mykrok style) → Annextube (Svelte):

### Phase 1: Keep Mykrok Approach
1. Use tsv-parser.ts as vanilla JS
2. Jest tests for utilities
3. Build UI with vanilla JS (monolithic)

**Drawback**: Will hit maintainability wall at ~2000 lines

### Phase 2: Introduce Components
1. Extract repeated UI into web components
2. Add TypeScript for type safety
3. Still using vanilla JS core

**Drawback**: Web components have less tooling than Svelte

### Phase 3: Full Svelte Migration
1. Convert vanilla components → Svelte
2. Add @testing-library/svelte
3. Keep utility layer unchanged (tsv-parser still vanilla)

**Better**: Start with Svelte from day 1, adopt mykrok's data patterns

---

## Concrete Examples

### Example 1: TSV Loading (Adopted from MyKrok)

**MyKrok**:
```javascript
const response = await fetch('athletes.tsv');
const text = await response.text();
const athletes = parseTSV(text);
```

**Annextube (Svelte)**:
```svelte
<script lang="ts">
import { onMount } from 'svelte';
import { parseTSV } from '@/utils/tsv-parser';

let videos: Video[] = [];

onMount(async () => {
    const response = await fetch('videos/videos.tsv');
    const text = await response.text();
    videos = parseTSV(text).map(row => ({
        video_id: row.video_id,
        title: row.title,
        duration: parseInt(row.duration)
    }));
});
</script>

{#each videos as video}
    <VideoCard {video} />
{/each}
```

### Example 2: URL State (Adopted from MyKrok)

**MyKrok**:
```javascript
const URLState = {
    encode(state) {
        const params = new URLSearchParams();
        if (state.athlete) params.set('a', state.athlete);
        return '#/' + state.view + '?' + params;
    }
};
```

**Annextube (Svelte)**:
```typescript
// frontend/src/lib/url-state.ts
export class URLState {
    static encode(state: AppState): string {
        const params = new URLSearchParams();
        if (state.query) params.set('q', state.query);
        if (state.sort) params.set('sort', state.sort);
        return `#/${state.view}?${params}`;
    }

    static decode(): AppState {
        const hash = location.hash.slice(2) || 'videos';
        const [view, query] = hash.split('?');
        const params = new URLSearchParams(query);
        return {
            view: view as View,
            query: params.get('q') || '',
            sort: params.get('sort') as SortOption || 'date'
        };
    }
}
```

```svelte
<!-- Use in Svelte component -->
<script lang="ts">
import { URLState } from '@/lib/url-state';
import { writable } from 'svelte/store';

const state = writable(URLState.decode());

$: {
    // Update URL when state changes
    history.replaceState(null, '', URLState.encode($state));
}
</script>
```

### Example 3: Testing Utilities (Adopted from MyKrok)

**MyKrok**:
```javascript
// tests/js/tsv-utils.test.js
import { parseTSV } from '../../src/mykrok/assets/map-browser/tsv-utils.js';

test('parses TSV with Windows line endings', () => {
    const tsv = 'name\tage\r\nAlice\t30';
    expect(parseTSV(tsv)).toEqual([{ name: 'Alice', age: '30' }]);
});
```

**Annextube**:
```typescript
// frontend/tests/unit/tsv-parser.test.ts
import { parseTSV } from '@/utils/tsv-parser';

describe('TSV Parser', () => {
    test('parses videos.tsv format', () => {
        const tsv = 'video_id\ttitle\tduration\nabc\tTest\t300';
        const result = parseTSV(tsv);
        expect(result[0].video_id).toBe('abc');
    });

    test('handles empty fields', () => {
        const tsv = 'video_id\ttitle\tabc\t';
        expect(parseTSV(tsv)[0].title).toBe('');
    });
});
```

---

## Summary Table

| Pattern | MyKrok | Annextube | Decision |
|---------|--------|-----------|----------|
| **Framework** | Vanilla JS | Svelte + TS | ✅ Use Svelte (better than vanilla) |
| **TSV Parsing** | 632-byte parser | Same pattern | ✅ Adopt (it's perfect) |
| **Data Loading** | TSV fast, Parquet lazy | TSV fast, JSON lazy | ✅ Adopt (same pattern) |
| **Routing** | Hash-based | Hash-based | ✅ Adopt (file:// compat) |
| **Testing** | Jest + jsdom | Jest + Vitest | ✅ Adopt Jest for utils |
| **Component Tests** | None | @testing-library | ✅ Add (mykrok missing) |
| **E2E Tests** | None | Playwright | ✅ Add (mykrok missing) |
| **Build Process** | None (copy files) | Vite (Svelte) | ✅ Use Vite (worth it) |
| **Python Integration** | Generates HTML | Generates + builds | ✅ Adopt (CLI workflow) |
| **State Management** | URLState object | URLState + Svelte stores | ✅ Hybrid (URL + reactive) |

---

## Implementation Timeline

### Phase 1: Utility Layer (2 days)
- [ ] Create tsv-parser.ts (inspired by mykrok)
- [ ] Create video-loader.ts (on-demand JSON)
- [ ] Jest tests for utilities
- [ ] URLState manager

### Phase 2: Svelte Setup (2 days)
- [ ] Vite + Svelte + TypeScript project
- [ ] Hash-based routing
- [ ] Generate types from JSON Schema

### Phase 3: Core Components (5 days)
- [ ] VideoList (TSV → grid)
- [ ] VideoPlayer (<video> + VTT)
- [ ] CommentView (threaded)
- [ ] FilterPanel (search)

### Phase 4: CLI Integration (2 days)
- [ ] generate-web command
- [ ] Build frontend in CLI
- [ ] Copy to archive/web/

### Phase 5: Testing (3 days)
- [ ] Component tests (@testing-library)
- [ ] E2E tests (Playwright)
- [ ] Document test patterns

**Total: 12-14 days** (matches original FRONTEND_TODO estimate)

---

## Conclusion

**Adopt from MyKrok**:
1. ✅ Lightweight TSV parser (vanilla utility)
2. ✅ On-demand data loading strategy
3. ✅ Hash-based URL state management
4. ✅ Jest + jsdom for utility testing
5. ✅ Python CLI generates frontend workflow

**Don't Adopt from MyKrok**:
1. ❌ Vanilla JS monolithic file (use Svelte components)
2. ❌ No component tests (add @testing-library/svelte)
3. ❌ No E2E tests (add Playwright)
4. ❌ Manual DOM manipulation (use Svelte reactivity)
5. ❌ No type safety (use TypeScript)

**Best of Both Worlds**:
- MyKrok's simple, dependency-free utilities for data parsing
- Svelte's component model, reactivity, and developer experience
- Comprehensive testing (utils + components + E2E)
- Clean separation: Python backend, Svelte frontend, shared data contracts

This approach gives us mykrok's simplicity and performance where it matters (data loading) while avoiding its maintainability issues (monolithic JS) by using a modern component framework.
