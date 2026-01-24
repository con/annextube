# annextube Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-24

## Active Technologies

**Backend/Library**:
- Python 3.10+ (001-youtube-backup)
- datasalad (git/git-annex operations)
- yt-dlp (YouTube downloads and metadata extraction)
- pytest (testing)

**Frontend**:
- Svelte (client-side web interface)
- Vitest + @testing-library/svelte (unit/integration tests)
- Playwright (E2E tests)

**Documentation**:
- Hugo static site generator with Congo theme
- Diataxis framework (Tutorial, How-to, Reference, Explanation)

**Storage**:
- File-based (NO database dependencies)
- git-annex repository (URL backend for video URLs)
- TSV files for summary metadata (videos.tsv, playlists.tsv)
- JSON for per-video metadata
- VTT for captions

## Project Structure

```text
annextube/                    # Python package (library + CLI)
├── models/                   # Data entities (Channel, Video, Playlist, etc.)
├── services/                 # Core logic (git_annex, youtube, archiver, updater)
├── cli/                      # CLI commands
├── lib/                      # Common utilities
└── schema/                   # JSON Schema for data models

frontend/                     # Svelte web interface
├── src/
│   ├── components/           # UI components
│   ├── pages/                # Page components
│   ├── services/             # Data loading, search
│   └── types/                # Generated TypeScript types
└── tests/                    # Frontend tests

tests/                        # Backend tests
├── contract/                 # API contract tests
├── integration/              # Integration tests
└── unit/                     # Unit tests

docs/                         # Hugo documentation
└── content/
    ├── tutorial/             # Getting started
    ├── how-to/               # Task guides
    ├── reference/            # API/CLI reference
    └── explanation/          # Concepts

specs/001-youtube-backup/     # Feature specification and planning
├── spec.md                   # Requirements
├── plan.md                   # Implementation plan
├── research.md               # Phase 0 research
├── data-model.md             # Phase 1 data model
├── quickstart.md             # Phase 1 quickstart guide
└── contracts/                # Phase 1 API contracts
```

## Commands

**Development**:
```bash
# Install dependencies
uv pip install -e ".[devel]"

# Run tests
pytest tests/

# Lint
ruff check annextube/ tests/

# Type check
mypy annextube/

# Frontend tests
cd frontend && npm test
cd frontend && npm run test:e2e
```

**CLI Usage**:
```bash
# Create archive
annextube create-dataset ~/my-archive

# Backup channel
annextube backup --output-dir ~/my-archive https://www.youtube.com/@Channel

# Update archive
annextube update --output-dir ~/my-archive

# Export metadata
annextube export --output-dir ~/my-archive

# Generate web UI
annextube generate-web --output-dir ~/my-archive
```

## Code Style

**Python**:
- Follow PEP 8
- Use type hints (Python 3.10+ syntax)
- Use datasalad for git/git-annex operations (DRY principle)
- Use yt-dlp Python API (not CLI)
- Prefer file-based storage (NO database dependencies)

**Frontend (Svelte)**:
- TypeScript for type safety
- Generate types from JSON Schema (no manual duplication)
- Client-side only (no backend dependency)
- File:// protocol support (hash-based routing)

**Testing**:
- TDD mandatory (tests before implementation)
- Contract tests for library API
- Integration tests for CLI ↔ library
- E2E tests for user workflows

## Recent Changes

- 001-youtube-backup: Added Python 3.10+

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
