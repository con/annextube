# Annextube Frontend

Client-side web interface for browsing YouTube archives offline.

## Technology Stack

- **Framework**: Svelte 4 + TypeScript
- **Build Tool**: Vite
- **Testing**: Vitest (components) + Jest (utilities) + Playwright (E2E)
- **Search**: Fuse.js (client-side full-text search)

## Architecture

This frontend follows a **hybrid approach** combining:
- **MyKrok patterns**: Lightweight TSV parser, on-demand loading, hash-based URL state
- **Svelte components**: Modern UI with type safety and reactivity

See: `../specs/001-youtube-backup/FRONTEND_ARCHITECTURE_COMPARISON.md`

## Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev
# → Opens http://localhost:5173

# Build for production
npm run build
# → Outputs to ../web/

# Run tests
npm test              # Vitest (component tests)
npm run test:utils    # Jest (utility tests)
npm run test:e2e      # Playwright (E2E tests)

# Type checking
npm run type-check
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Svelte components
│   │   ├── VideoCard.svelte
│   │   ├── VideoList.svelte
│   │   ├── VideoPlayer.svelte
│   │   ├── FilterPanel.svelte
│   │   └── CommentView.svelte
│   ├── pages/               # Page components
│   │   ├── Index.svelte
│   │   └── VideoDetail.svelte
│   ├── services/            # Data loading, search
│   │   ├── data-loader.ts
│   │   ├── search.ts
│   │   └── caption-service.ts
│   ├── utils/               # Pure utilities (adopted from mykrok)
│   │   ├── tsv-parser.ts    # Lightweight TSV parser (mykrok pattern)
│   │   ├── url-state.ts     # URL state manager (mykrok pattern)
│   │   └── date-format.ts
│   ├── types/               # TypeScript types
│   │   └── models.ts        # Generated from JSON Schema
│   ├── lib/                 # Shared libraries
│   │   └── routing.ts       # Hash-based router
│   ├── App.svelte           # Root component
│   └── main.ts              # Entry point
├── tests/
│   ├── unit/                # Jest tests for utilities
│   │   └── tsv-parser.test.ts
│   ├── integration/         # Vitest tests for components
│   └── e2e/                 # Playwright E2E tests
└── package.json
```

## Data Loading Strategy (MyKrok Pattern)

**Fast initial load**:
1. Load `videos/videos.tsv` (~1-2 MB) - Parse with lightweight TSV parser
2. Display video list immediately

**On-demand details**:
3. When user clicks video → Load `videos/{video_id}/metadata.json`
4. When user views comments → Load `videos/{video_id}/comments.json`
5. Video files are git-annex symlinks (not loaded to browser)

## URL State Management (MyKrok Pattern)

Full application state is encoded in URL hash for shareable links:

```
#/videos?q=react&from=2024-01-01&to=2024-12-31
#/video/abc123?t=120               # Video at 2:00 timestamp
#/playlist/PL456?video=3           # Playlist at video 3
```

See: `src/utils/url-state.ts`

## Building for Production

```bash
# Build frontend
npm run build

# Output structure:
../web/
├── index.html
└── assets/
    ├── index-[hash].js     # Compiled Svelte → vanilla JS
    ├── index-[hash].css
    └── *.js                # Code-split chunks

# Users open: file:///path/to/archive/web/index.html
```

## File:// Protocol Support

The frontend works with `file://` protocol (no web server required):

1. **Relative paths**: `base: './'` in vite.config.ts
2. **Hash routing**: `#/video/abc` instead of `/video/abc`
3. **Same-origin fetch**: All data files in same directory tree

## Testing Strategy

### Utility Tests (Jest + jsdom)
```bash
npm run test:utils
```
- Fast, no browser overhead
- Test pure functions: TSV parser, date formatting, URL state

### Component Tests (Vitest + @testing-library/svelte)
```bash
npm test
```
- Test Svelte components in isolation
- Verify rendering, user interactions, state changes

### E2E Tests (Playwright)
```bash
npm run test:e2e
```
- Test complete user workflows in real browser
- Video playback, caption switching, search, filtering

## Development

### Adding a New Component

1. Create `src/components/MyComponent.svelte`
2. Write component tests: `tests/integration/MyComponent.test.ts`
3. Import and use in pages

### Adding a New Utility

1. Create `src/utils/my-util.ts` (pure TypeScript, no Svelte)
2. Write Jest tests: `tests/unit/my-util.test.ts`
3. Import in components or services

## Type Generation

TypeScript types are generated from backend JSON Schema:

```bash
npm run generate-types
# → Reads ../annextube/schema/models.json
# → Generates src/types/models.ts
```

## Contributing

See: `../specs/001-youtube-backup/FRONTEND_TODO.md` for task list.
