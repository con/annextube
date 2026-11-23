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
npm run test:chromatic  # Playwright (page snapshots, in Chromium; nothing is uploaded)

# Look at the component stories, live
npm run storybook

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

### Visual Snapshots (Chromatic)

Every push is rendered on [Chromatic](https://www.chromatic.com) and compared against the last accepted baseline, twice: once per story, once per page state.
The two feeds answer different questions, which is why there are two Chromatic projects, two build workflows and two badges.

|                          | Storybook stories                                                                     | Playwright snapshots                                                                                              |
| ------------------------ | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| What is captured         | One real Svelte component in one state, mounted with fixed props, outside the app     | The real app, booted in Chromium inside a fixture archive, at desktop, tablet and phone sizes                     |
| Where it lives           | `stories/*.stories.ts`                                                                | `tests/chromatic/*.test.ts`, fixture archives under `tests/chromatic/fixtures/`                                   |
| What a diff points at    | That component, in that state                                                         | The page as a whole: layout between components, overflow at narrow widths, what the real boot path rendered       |
| How it reaches Chromatic | The built Storybook (`npm run build-storybook`)                                       | An archive of the DOM that `@chromatic-com/playwright` records at the end of each test (`npm run test:chromatic`) |
| Workflow and badge       | Chromatic (Storybook)                                                                 | Chromatic (Playwright)                                                                                            |

A story is the place for a component's own states (a video card that is downloaded, tracked, or missing its thumbnail).
A Playwright snapshot is the place for a page state (the video list, a video's page, the channels overview, a load error), since only the running app knows how its pieces fit together.
Neither keeps pixels in this repository: Chromatic renders both in its own browsers, holds the baselines, and a change is accepted or rejected in its review UI.

The snapshot suite does not use the dev server.
`scripts/serve-chromatic-fixtures.sh` builds the web UI and serves it inside each fixture archive, laid out as a deployed archive is (`<archive>/web/` beside `<archive>/videos/`), so the pages read real files and nothing is stubbed.
Everything a snapshot shows is pinned: the fixtures reference no remote URL, and the clock is fixed (in the tests and in `.storybook/preview.ts`), because the UI prints ages relative to now.

**Setup (once per repository)**

1. Create two Chromatic projects for this repository: one for Storybook, then **Add project**, pick the same repository again, and name the second one for Playwright.
2. Add each project's token as a repository secret: `CHROMATIC_STORYBOOK_PROJECT_TOKEN` and `CHROMATIC_PLAYWRIGHT_PROJECT_TOKEN`.
3. Push. `chromatic-storybook.yml` and `chromatic-playwright.yml` under `.github/workflows/` build on every push without a token, and `chromatic-publish.yml` uploads each build from the default branch, which holds the tokens.
   The first upload comes from the merge that adds these files; that first build of each project is its baseline, so look it over in Chromatic once.
   After that, the default branch's builds are accepted on their own, since their changes were reviewed on their pull requests.

**Day to day**

1. `npm run storybook` to look at the stories; `npm run test:chromatic` to run the page captures locally. Nothing is uploaded from a local run.
2. Push a branch, or open a pull request from a fork. Each build workflow captures its feed, `chromatic-publish.yml` uploads it, and Chromatic posts one status check per project once the upload is done.
3. Open the check and review each diff: accept what was intended, otherwise fix and push again. Chromatic diffs a branch against that branch's own last build, so merge `master` in first when the branch is behind, or `master`'s changes show up as yours.
4. A new component state gets a story; a new page state gets a `forEachViewport` test in `tests/chromatic/`, plus fixture files that reach it deterministically.

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
