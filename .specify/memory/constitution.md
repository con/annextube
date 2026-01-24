<!--
Sync Impact Report - Constitution v1.0.0
════════════════════════════════════════
Version Change: Initial → 1.0.0
Rationale: Initial constitution establishing foundational principles for FOSS multi-interface project

Modified Principles:
  - All principles newly defined (initial version)

Added Sections:
  - Core Principles (I-VII)
  - Quality Standards
  - Contribution & Community
  - Governance

Templates Requiring Updates:
  ⚠ .specify/templates/plan-template.md - pending validation
  ⚠ .specify/templates/spec-template.md - pending validation
  ⚠ .specify/templates/tasks-template.md - pending validation

Follow-up TODOs: None
-->

# Annextube Constitution

## Core Principles

### I. Library-First Architecture

Every feature MUST start as a standalone library with:
- Self-contained functionality with minimal dependencies
- Independent testability (unit and integration tests)
- Clear, documented API surface
- No organizational-only libraries (each must solve a concrete problem)

**Rationale**: Library-first design ensures reusability, testability, and enables other projects to integrate components independently. This maximizes the value of open source contributions.

### II. Multi-Interface Exposure

Every library MUST expose functionality through:
- **CLI**: Command-line interface following Unix philosophy (stdin/args → stdout, errors → stderr)
- **API**: Programmatic interface for library consumers
- **Web UI**: User-friendly web interface for interactive use (where applicable)

CLI text I/O protocol requirements:
- Accept input via stdin and/or command-line arguments
- Output primary results to stdout
- Output errors and warnings to stderr
- Support both JSON and human-readable formats

**Rationale**: Multiple interfaces serve different user needs (automation, integration, human interaction) and make the project accessible to diverse audiences.

### III. Test-First Development (NON-NEGOTIABLE)

Test-Driven Development is MANDATORY:
1. Tests MUST be written before implementation
2. Tests MUST be reviewed and approved by user/maintainer
3. Tests MUST fail initially (red phase)
4. Implementation follows to make tests pass (green phase)
5. Refactoring MUST preserve passing tests

**Rationale**: TDD prevents scope creep, ensures requirements are testable, and creates living documentation. This is non-negotiable for robustness.

### IV. Integration Testing

Integration tests are REQUIRED for:
- New library contract tests (API boundaries)
- Contract changes (backward compatibility verification)
- Inter-component communication (CLI ↔ library, library ↔ web UI)
- Shared schemas and data formats
- End-to-end user workflows

**Rationale**: Integration tests ensure components work together correctly in real-world scenarios, catching issues unit tests miss.

### V. Code Efficiency & Conciseness

Codebase MUST prioritize:
- Minimal complexity (avoid over-engineering)
- Clear, readable code over clever solutions
- YAGNI principle (You Aren't Gonna Need It)
- Remove dead code immediately
- Each component has a single, well-defined purpose

**Rationale**: Concise, efficient code is easier to understand, maintain, and debug. This lowers the contribution barrier for new developers.

### VI. Observability & Debuggability

All components MUST provide:
- Structured logging (JSON format for machine parsing)
- Human-readable log output option
- Clear error messages with actionable guidance
- Trace identifiers for request tracking
- Performance metrics at component boundaries

**Rationale**: Text I/O and structured logging ensure issues can be debugged in production. Observability is critical for robust operation.

### VII. Versioning & Breaking Changes

Version numbering MUST follow semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes (incompatible API changes)
- **MINOR**: New features (backward compatible additions)
- **PATCH**: Bug fixes (backward compatible corrections)

Breaking changes REQUIRE:
- Migration guide in release notes
- Deprecation warnings in prior MINOR version (when possible)
- Clear documentation of changed behavior

**Rationale**: Predictable versioning builds trust with users and integrators. Clear migration paths enable safe upgrades.

## Quality Standards

### Testing Coverage

- Unit tests: MUST cover all public APIs and error paths
- Integration tests: MUST cover component interactions
- Regression tests: MUST be added for every bug fix
- Performance tests: SHOULD be added for performance-critical paths

### Documentation Requirements

Every component MUST include:
- README with quickstart examples
- API documentation (auto-generated from code)
- Architecture decision records (ADRs) for significant choices
- Contribution guide (CONTRIBUTING.md)

### Code Review Standards

All changes MUST:
- Pass automated tests (unit, integration, linting)
- Include tests for new functionality
- Update relevant documentation
- Be reviewed by at least one maintainer
- Follow existing code style and patterns

## Contribution & Community

### Welcoming Contributors

The project MUST:
- Provide clear "good first issue" labels for newcomers
- Respond to issues and PRs within 7 days
- Maintain up-to-date contribution guidelines
- Include code of conduct (Contributor Covenant)
- Recognize contributors in release notes

### Supported Use Cases

The project is designed for:
- Individual users (via CLI and Web UI)
- Developers integrating libraries into other projects
- System administrators (automation via CLI)
- Organizations deploying web UI for teams

All design decisions MUST consider impact on these use cases.

## Governance

### Amendment Process

Constitution amendments REQUIRE:
1. Documented proposal with rationale
2. Impact analysis on existing code and practices
3. Community feedback period (minimum 7 days for MAJOR changes)
4. Approval from project maintainers
5. Migration plan for affected code

### Compliance & Enforcement

- All pull requests MUST verify compliance with constitution principles
- Code reviews MUST reject violations (exception requires documented justification)
- Complexity increases MUST be justified against business value
- Security vulnerabilities override other principles (fix immediately)

### Runtime Development Guidance

For agent-specific development instructions, refer to `.claude/CLAUDE.md` (or equivalent guidance files for other AI assistants). These files provide runtime context while the constitution remains tool-agnostic.

**Version**: 1.0.0 | **Ratified**: 2026-01-24 | **Last Amended**: 2026-01-24
