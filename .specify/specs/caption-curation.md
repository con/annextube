# Caption Curation Feature Plan

## Context

YouTube auto-generated captions systematically mangle domain-specific vocabulary ("DataLad" becomes "data lad", "fMRI" becomes "f mri", etc.). A proven 8-stage curation pipeline already exists as standalone scripts in the ReproTube project (`parse_youtube_vtt.py`, `curate_captions.py`, `glossary.yaml`). This plan integrates that pipeline into annextube as a first-class feature, with per-archive and user-wide glossary support, automatic curation during backup, LLM-assisted correction generation, and optional audio forced-alignment.

### Source Material

The working prototype lives at:
```
/home/yoh/proj/repronim/ReproTube/ReproNim/videos/2026/02/
  2026-02-06_YODA-Structure-your-studies-observable-and-reproducible-they-become/
    CURATE_CAPTIONS.md          # Detailed design document
    glossary.yaml               # ~450 terms, 11 categories
    tmp/parse_youtube_vtt.py    # Stage 1: VTT → word-level JSON
    tmp/curate_captions.py      # Stages 2-8: main pipeline
    tmp/llm_corrections.json    # Per-video context corrections
```

Results on a 1-hour talk: ~200 domain term errors fixed, 191 fillers removed, 37 commands quoted, 916 readable cues (max 12 words each), 8,257 word-level `<c>` tags restored. Execution: 7.5s for stages 1-7 (CPU, no deps beyond stdlib).

## Architecture Overview

```
[Backup] ──caption download──> video.en.vtt ──auto-curate──> video.en-curated.vtt
                                                    │
                    ┌───────────────────────────────┘
                    v
           CaptionCurator.curate()
           ├── Stage 1: Glossary regex (YAML glossary → compiled patterns)
           ├── Stage 2: LLM corrections (per-video llm_corrections.json)
           ├── Stage 3: Fuzzy matching (difflib, threshold 0.82)
           ├── Stage 4: Filler removal (uh, um, etc.)
           ├── Stage 5: ASR artifact fixes (truncated "g" → "git")
           ├── Stage 6: Sentence segmentation (rule-based)
           ├── Stage 7: Cue chunking (max 12 words, balanced split)
           └── Stage 8: Word-level timestamp restoration (proportional or audio-aligned)
```

## Files to Create

| File | Purpose |
|------|---------|
| `annextube/models/curation.py` | Data models: `WordTimestamp`, `GlossaryTerm`, `Glossary`, `CurationResult` |
| `annextube/services/caption_curator.py` | Core 8-stage curation engine (ported from standalone scripts) |
| `annextube/services/llm_corrector.py` | LLM provider abstraction + correction generation |
| `annextube/cli/curate_captions.py` | `annextube curate-captions` CLI command |
| `tests/unit/test_caption_curator.py` | Unit tests for all 8 stages |
| `tests/unit/test_curation_config.py` | Config parsing tests |
| `tests/fixtures/sample_karaoke.vtt` | YouTube-style VTT test fixture |
| `tests/fixtures/sample_glossary.yaml` | Small test glossary |

## Files to Modify

| File | Changes |
|------|---------|
| `annextube/lib/config.py` | Add `CurationConfig` dataclass, wire into `Config`, add `glossary_path` to `UserConfig`, add `curation` override to `SourceConfig` |
| `annextube/services/archiver.py` | Add `_curate_captions()` method, call it after caption download |
| `annextube/cli/__main__.py` | Register `curate-captions` command |
| `pyproject.toml` | Add `pyyaml` dep, add `[audio-align]` optional dep group |

## Phase 1: Data Models and Configuration

### 1a. `annextube/models/curation.py` -- Data types

```python
@dataclass
class WordTimestamp:
    word: str
    start: float  # seconds
    end: float

@dataclass
class GlossaryTerm:
    canonical: str           # e.g., "DataLad"
    patterns: list[str]      # e.g., ["data lad", "data glad", "datal"]
    category: str = ""

@dataclass
class Glossary:
    terms: list[GlossaryTerm]

    def merge(self, other: "Glossary") -> "Glossary":
        """Merge: other's terms override self's (by canonical form)."""

    @classmethod
    def from_yaml(cls, path: Path) -> "Glossary": ...

    @classmethod
    def load_merged(cls, user_path: Path | None, archive_path: Path | None) -> "Glossary": ...

@dataclass
class CurationResult:
    original_word_count: int
    curated_text: str
    segments: list[dict]     # [{text, start, end, words: [{word, start, end}]}]
    stage_results: list[dict]  # per-stage change counts
    curated_at: str          # ISO 8601
```

### 1b. `CurationConfig` in `annextube/lib/config.py`

```python
@dataclass
class CurationConfig:
    enabled: bool = True               # Auto-curate during backup
    curated_suffix: str = "curated"    # video.en-curated.vtt
    max_words_per_cue: int = 12
    min_orphan_words: int = 3
    filler_removal: bool = True
    command_quoting: bool = True
    fuzzy_enabled: bool = True
    fuzzy_threshold: float = 0.82
    # LLM settings
    llm_provider: str | None = None    # "ollama", "openai", "anthropic"
    llm_model: str | None = None
    llm_base_url: str | None = None    # For Ollama
    # Audio alignment (optional)
    audio_align_method: str | None = None  # "stable-ts" or "ctc"
    audio_align_model: str | None = None   # Whisper model name
```

Add to `UserConfig`:
```python
glossary_path: str | None = None  # ~/.config/annextube/glossary.yaml
```

Add to `SourceConfig`:
```python
curation: bool | None = None  # Per-source curation override
```

Wire into `Config.from_dict()` to parse `[curation]` TOML section.

### Config TOML example

```toml
# .annextube/config.toml
[curation]
enabled = true
curated_suffix = "curated"
max_words_per_cue = 12
fuzzy_threshold = 0.82
# llm_provider = "ollama"
# llm_model = "llama3"
```

## Phase 2: Core Curation Engine

### `annextube/services/caption_curator.py`

Port the existing pipeline logic from the standalone scripts into a `CaptionCurator` class.

**Key design decisions:**
- Stages 1-5 operate on a flat text string (join words → apply corrections → split back). This is faithful to the working prototype.
- Stages 6-7 handle segmentation and chunking on the corrected text.
- Stage 8 uses proportional timestamp mapping (floating-point index) to map curated words back to original timestamps.

**Reuse directly from source scripts:**
- `parse_youtube_vtt()` -- extract words from karaoke VTT
- `load_glossary()` -- YAML parsing (adapt to use `pyyaml` instead of regex parsing)
- `apply_glossary()` -- regex replacement with SKIP_PATTERNS
- `fuzzy_glossary_correct()` -- difflib matching with `_FUZZY_SKIP`, morphological variants, prefix tiebreaker
- `remove_fillers()` -- filler word regex
- `fix_truncated_commands()` -- ASR artifact fixes ("g submodule" → "git submodule")
- `quote_commands()` -- CLI command quoting
- `segment_into_sentences()` -- rule-based sentence splitting
- `chunk_sentences()` -- balanced word chunking
- `map_sentences_to_timestamps()` -- proportional timestamp mapping
- `add_word_timing_proportional()` -- character-proportional word timing
- `write_vtt()` -- VTT output with optional `<c>` tags

**SKIP_PATTERNS** (common English words that collide with glossary terms):
```python
SKIP_PATTERNS = {
    "do", "discover", "describe", "conduct", "connects",
    "ants", "nifty", "docker", "galaxy", "gentle",
    "gin", "slurm", "elixir", "enigma", "grab",
    "hub", "globus",
}
```

**_FUZZY_SKIP** (~40 common English words preventing fuzzy match false positives):
```python
_FUZZY_SKIP = {
    'conduct', 'conducted', 'conducting',
    'connect', 'connected', 'connecting', 'connections',
    'describe', 'described', 'describes', 'describing',
    'discover', 'discovered', 'discovers', 'discovering',
    'install', 'installed', 'installer', 'installing',
    'process', 'processed', 'processing',
    'principle', 'principles', 'principal',
    'reproduce', 'reproduced', 'reproducing', 'reproducible',
    'repository', 'repositories',
    'toolkit', 'toolkits',
    'version', 'versioned', 'versioning',
    'execute', 'executed', 'executing', 'executable',
    'repro',  # commonly used abbreviation
}
```

**Class interface:**

```python
class CaptionCurator:
    def __init__(self, config: CurationConfig): ...

    @staticmethod
    def parse_youtube_vtt(vtt_path: Path) -> list[WordTimestamp]: ...

    @staticmethod
    def load_glossary(user_path: Path | None, archive_path: Path | None) -> Glossary: ...

    def curate(self, words: list[WordTimestamp], glossary: Glossary,
               corrections: dict[str, str] | None = None) -> CurationResult: ...

    @staticmethod
    def write_curated_vtt(result: CurationResult, output_path: Path,
                          word_timing: bool = True) -> None: ...

    def curate_vtt_file(self, vtt_path: Path, output_path: Path,
                        glossary: Glossary, corrections: dict[str, str] | None = None,
                        word_timing: bool = True) -> CurationResult: ...

    # Optional audio alignment (requires annextube[audio-align])
    def align_with_audio(self, text: str, audio_path: Path) -> list[dict]: ...
```

### Key algorithm: Proportional timestamp mapping

```python
ratio = total_original_words / total_corrected_words
float_idx = 0.0
for chunk in chunks:
    n = len(chunk.split())
    start_idx = int(float_idx)
    end_idx = int(float_idx + n * ratio)
    segment = {start: words[start_idx].start, end: words[end_idx].end}
    float_idx += n * ratio
```

This prevents timestamp collapse when word counts change due to corrections.

## Phase 3: LLM Correction Generation

### `annextube/services/llm_corrector.py`

```python
class LLMCorrectionGenerator:
    """Generate correction proposals via LLM (Ollama/OpenAI/Anthropic)."""

    def __init__(self, provider: str, model: str,
                 base_url: str | None = None, api_key: str | None = None): ...

    def generate_corrections(self, text: str, glossary_terms: list[str]) -> dict[str, str]:
        """Send glossary-corrected text to LLM, get {old: new} proposals."""

    def save_corrections(self, corrections: dict[str, str], path: Path) -> None:
        """Save to per-video llm_corrections.json for human review."""

def load_corrections(path: Path) -> dict[str, str]:
    """Load approved corrections from llm_corrections.json."""
```

**LLM prompt strategy:** Send the glossary-corrected transcript with domain term list, ask the LLM to identify remaining ASR errors and propose `{old_context: new_text}` corrections. Context strings prevent false positives (e.g., "g is about" rather than standalone "g"). Save as JSON for human review.

**Provider implementations:** Use `httpx` for HTTP calls. Keep it simple.

## Phase 4: CLI Command

### `annextube/cli/curate_captions.py`

```
annextube curate-captions [OPTIONS]

Options:
  -o, --output-dir PATH        Archive directory (default: cwd)
  --video-id TEXT               Specific video ID(s) to curate (repeatable)
  -l, --language TEXT           Caption language to curate (default: all auto-generated)
  --all                         Curate all videos in archive
  --glossary PATH               Additional glossary to merge
  --corrections PATH            Path to corrections JSON
  --generate-corrections        Generate LLM correction proposals
  --audio PATH                  Audio file for forced alignment
  --align-method [stable-ts|ctc]
  --align-model TEXT            Whisper model name
  --no-word-timing              Plain text output (no <c> tags)
  --dry-run                     Show changes without writing
```

Register in `annextube/cli/__main__.py` via `cli.add_command(curate_captions)`.

## Phase 5: Backup Integration

### Modify `annextube/services/archiver.py`

Add `_curate_captions(video_dir, captions_metadata) -> list[dict]` method:

1. Check `self.config.curation.enabled` (and per-source override)
2. Load merged glossary (user-wide + archive)
3. Skip if no glossary terms found (graceful: no glossary = no curation, no error)
4. For each auto-generated caption:
   - Parse VTT → curate → write `video.{lang}-curated.vtt`
   - Load per-video `llm_corrections.json` if it exists
5. Append curated entries to captions_metadata
6. Return updated metadata

Call from `_download_captions()` right after caption files are downloaded.

### Update `captions.tsv` schema

Add optional `curated_from` column:
```
language_code	auto_generated	auto_translated	file_path	fetched_at	curated_from
en              true            false           videos/.../video.en.vtt          2026-02-16T...
en-curated      false           false           videos/.../video.en-curated.vtt  2026-02-16T...  en
```

## Phase 6: Dependencies

### `pyproject.toml` changes

```toml
dependencies = [
    # ... existing ...
    "pyyaml>=6.0",  # YAML glossary parsing for caption curation
]

[project.optional-dependencies]
# ... existing ...
audio-align = [
    "stable-ts>=2.15.0",
    "openai-whisper>=20231117",
]
```

## Phase 7: Testing

### Test fixtures

- `tests/fixtures/sample_karaoke.vtt` -- Small YouTube-style VTT with `<c>` tags (~10 cues)
- `tests/fixtures/sample_glossary.yaml` -- 5-10 test terms across 2 categories

### Unit tests (`tests/unit/test_caption_curator.py`)

Test each stage independently:
- VTT parsing (karaoke and standard)
- Glossary loading and merging (user + archive, override semantics)
- Glossary regex with SKIP_PATTERNS
- Fuzzy matching with threshold, morphological variants, prefix tiebreaker
- Filler removal
- ASR artifact fixes ("g submodule" → "git submodule")
- Command quoting
- Sentence segmentation
- Cue chunking (balanced split, orphan merge)
- Proportional timestamp mapping
- Full pipeline end-to-end
- VTT output validity

### Config tests (`tests/unit/test_curation_config.py`)

- Default values
- TOML parsing with `[curation]` section
- Missing section uses defaults

## Implementation Order

1. **Phase 1** -- Models + Config (foundation, no logic)
2. **Phase 7 partial** -- Write test fixtures + initial test stubs (TDD)
3. **Phase 2** -- Core CaptionCurator service (largest piece, port from scripts)
4. **Phase 4** -- CLI command (depends on Phase 2)
5. **Phase 5** -- Backup integration (depends on Phase 2)
6. **Phase 3** -- LLM correction generation (independent, can parallel)
7. **Phase 6** -- Audio alignment optional deps
8. **Phase 7** -- Complete test suite

## Verification

1. `uv run tox -e py3` -- All unit tests pass
2. `uv run tox -e lint` -- No ruff violations
3. Manual test: create archive with glossary, backup a video, verify `video.en-curated.vtt` created
4. Manual test: `annextube curate-captions --all --dry-run` shows expected corrections
5. Verify `captions.tsv` includes curated entries with `curated_from` column

## Glossary File Format

Reuse the existing YAML format from ReproTube (proven with ~450 terms):

```yaml
# Categories are top-level keys
project_names:
  - term: "DataLad"
    patterns: ["data lad", "data glad", "data lard", "data lab"]
  - term: "git-annex"
    patterns: ["git annex", "git anex", "get annex"]
commands:
  - term: "datalad run"
    patterns: ["data lad run", "data glad run"]
acronyms:
  - term: "BIDS"
    expansion: "Brain Imaging Data Structure"
    patterns: ["bids", "beds", "bits"]
```

## Open Questions

- Should command quoting patterns be configurable per-glossary (e.g., a `commands_to_quote` section in YAML), or hardcoded in the engine?
- Should the LLM correction file format be a flat `{old: new}` dict (simple, like the prototype) or a richer format with `approved`, `confidence`, `context` fields?
- For the backup integration, should curation re-run when the glossary changes (detect via file hash)?
