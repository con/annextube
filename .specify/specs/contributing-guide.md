# Design: CONTRIBUTING.md for Humans and Agentic Systems

**Task**: T139
**Date**: 2026-04-15
**Status**: Design complete, ready for implementation

## Problem

The project lacks a CONTRIBUTING.md (required by constitution governance) and contribution
guidelines are scattered across CLAUDE.md (agent-specific) with no canonical human-readable
guide. This creates duplication risk and makes onboarding harder for both humans and AI agents.

## Design: Single Source of Truth Pattern

```
CONTRIBUTING.md (canonical, human-focused, complete)
    ↑ referenced by
CLAUDE.md, AGENTS.md, .cursorrules, etc. (agent-focused, lean)
```

### Key Principle

CONTRIBUTING.md is the authoritative source for:
- Development setup
- Commit message conventions
- Testing requirements
- Code style
- PR process
- Review timeline

Agent instruction files (CLAUDE.md) should **reference** CONTRIBUTING.md for these topics,
not duplicate them. CLAUDE.md keeps only agent-specific guidance (e.g., "check troubleshooting.md
FIRST", "use @AnnexTubeTesting", tox commands vs pytest).

## Recommended CONTRIBUTING.md Structure

### Sections

1. **Welcome** - Brief project intro, who can contribute
2. **Quick Start** - Fork -> Clone -> Branch -> Test -> PR (5-line summary)
3. **Development Setup** - Python 3.10+, `uv pip install -e ".[devel]"`, git-annex
4. **Commit Message Conventions** - Conventional Commits format
   - Types: feat, fix, docs, style, refactor, perf, test, chore, ci
   - Format: `<type>[scope]: <description>`
   - Examples with annextube-specific scopes (youtube, cli, frontend, annex)
5. **Testing Requirements** - tox environments, coverage expectations, test markers
6. **Code Style** - Python (PEP 8, type hints), Frontend (TypeScript, Svelte)
7. **Pull Request Process** - Branch naming, required checks, PR template
8. **Review Timeline** - Response expectations
9. **Getting Help** - Issues, discussions
10. **License** - Contribution licensing terms

### Why Conventional Commits (not DataLad-style prefixes)

DataLad uses custom prefixes (NF, BF, RF, DOC, etc.). For annextube, Conventional Commits
is recommended because:
- Widely understood by LLMs (extensive training data)
- Tooling ecosystem (commitlint, semantic-release, changelogs)
- Lower learning curve for new contributors
- Still machine-parseable for automation

### Agent-Friendly Properties

The structure is designed so AI agents can:
- Extract commit format from structured Markdown headers
- Follow concrete examples consistently
- Parse explicit requirements (coverage %, test commands)
- Reference authoritative sections without ambiguity

## CLAUDE.md Refactoring

After creating CONTRIBUTING.md, refactor CLAUDE.md to replace duplicated sections with:

```markdown
## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the canonical guide on:
- Development setup and dependencies
- Commit message conventions (Conventional Commits)
- Testing requirements and tox environments
- Code style standards (Python + Frontend)
- Pull request process and review expectations
```

Keep agent-specific sections that don't belong in CONTRIBUTING.md:
- Troubleshooting.md mandatory check
- @AnnexTubeTesting test channel
- Git hygiene before new work
- .git-meta/ commit workflow
- tox.ini shell script patterns

## References

- DataLad CONTRIBUTING.md: https://github.com/datalad/datalad/blob/master/CONTRIBUTING.md
- Conventional Commits: https://www.conventionalcommits.org/en/v1.0.0/
- AGENTS.md spec: https://agents.md/
- Mozilla Science contributing guide: https://mozillascience.github.io/working-open-workshop/contributing/
