<!--
Sync Impact Report - Constitution v1.3.0
════════════════════════════════════════
Version Change: 1.2.0 → 1.3.0
Rationale: MINOR - Added FOSS principles and resource efficiency requirements
           Inspired by mykrok constitution review
           Enhanced CLI requirements with idempotency and exit codes

Modified Principles:
  - II. Multi-Interface Exposure → Added CLI idempotency, exit codes, progress indication
  - Added X. FOSS Principles (new principle) - licensing, privacy, transparency, offline capability
  - Added XI. Resource Efficiency (new principle) - network, disk, memory, CPU, energy efficiency

Added Sections:
  - None (new principles added)

Previous Changes:
  v1.2.0:
    - VIII. DRY Principle - No Code Duplication
    - Code Review Standards → Enhanced with duplication detection
  v1.1.0:
    - II. Multi-Interface Exposure → Frontend MVC architecture
    - IV. Integration Testing → Frontend component testing
    - IX. Shared Data Schema
    - Frontend Architecture subsection

Templates Requiring Updates:
  ⚠ .specify/templates/plan-template.md - pending validation (FOSS compliance, resource limits)
  ⚠ .specify/templates/spec-template.md - pending validation (privacy requirements, offline scenarios)
  ⚠ .specify/templates/tasks-template.md - pending validation (license checks, performance tasks)

Follow-up TODOs:
  - Add LICENSE file to repository
  - Configure license compatibility checking in CI
  - Add resource profiling to performance tests
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
- **Meaningful exit codes**: 0 for success, non-zero for errors (follow conventions)
- **Idempotency**: Same command with same inputs produces same result (safe to retry)
- **Machine-parseable output**: JSON mode for automation integration
- **Progress indication**: Show progress for long-running operations (when TTY detected)

**Frontend UI Architecture (MVC Pattern)**:
- **Model**: Data structures defined by shared schema (consumed from library output)
- **View**: UI components rendering data (React, Vue, Svelte, or similar)
- **Controller**: Frontend logic handling user interactions and state management
- Frontend MUST operate standalone without backend dependency (client-side rendering)
- Frontend consumes library output via CLI or direct API calls
- Separation of concerns: UI components, business logic, and data layer clearly delineated

**Rationale**: Multiple interfaces serve different user needs (automation, integration, human interaction). Clean MVC separation ensures maintainability and testability of frontend components. Frontend independence enables flexible deployment (static hosting, CDN, offline use).

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
- **Frontend components**:
  - Component integration tests (parent-child component interactions)
  - State management integration (store/context updates reflecting in UI)
  - Data schema consumption (frontend correctly parsing library output)
  - User interaction flows (multi-step workflows through UI)
  - Browser compatibility testing (if supporting multiple browsers)

**Rationale**: Integration tests ensure components work together correctly in real-world scenarios, catching issues unit tests miss. Frontend integration tests verify UI components interact correctly with data models and handle user workflows end-to-end.

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

### VIII. DRY Principle - No Code Duplication

**Duplication is evil.** Code MUST NOT contain duplicated logic or functionality:

**Before writing new code**:
- Introspect existing codebase for similar functionality
- Search for patterns that solve the same or related problems
- Identify opportunities to extract common functionality
- Prefer reusing existing functions over creating new ones

**When duplication is detected**:
- Extract common functionality into reusable functions/modules
- Refactor immediately (do not defer "for later")
- Create utility functions for repeated patterns
- Use composition and higher-order functions for variations
- Document extracted functions with clear purpose and examples

**Code review MUST**:
- Actively check for code duplication (copy-paste, similar logic)
- Identify opportunities to refactor into reusable components
- Reject PRs with obvious duplication without justification
- Suggest existing functions/modules that solve the same problem
- Require refactoring before approval if duplication detected

**Allowed exceptions** (duplication is acceptable):
- **Automated generation**: Generated code (summaries, documentation, type definitions from schema)
- **Build artifacts**: Compiled output, bundled assets, generated types
- **Test fixtures**: Similar test setup where abstraction reduces readability
- **Configuration**: Environment-specific configs with overlapping values
- **Explicit performance**: Inlining for performance (must be justified and measured)

All exceptions MUST be documented with rationale.

**Tools and enforcement**:
- Use linters to detect code duplication (e.g., `jscpd`, `pylint --duplicate-code`)
- Enforce maximum duplication threshold in CI (e.g., <3% duplicated code)
- Regular refactoring sprints to address accumulated duplication

**Rationale**: Code duplication multiplies maintenance burden, bugs, and inconsistencies. Every duplicated line is a potential source of divergence and technical debt. Extracting common functionality makes codebases smaller, more maintainable, and easier for new contributors to understand.

### IX. Shared Data Schema

Data structures MUST be defined in a common schema shared between library and frontend:
- **Single source of truth**: Schema definition file(s) maintained in library
- **Format**: JSON Schema, TypeScript interfaces, Protocol Buffers, or language-agnostic format
- **Validation**: Both library output and frontend input MUST validate against schema
- **Versioning**: Schema changes follow semantic versioning independently
- **Documentation**: Auto-generated docs from schema (types, constraints, examples)
- **Type safety**: Frontend generates types from schema (no manual duplication)

Schema changes REQUIRE:
- Compatibility testing between library and frontend
- Migration path if breaking schema changes
- Clear documentation of added/removed/modified fields

**Rationale**: Shared schema eliminates data contract drift between library and frontend. Automated type generation prevents manual synchronization errors and ensures frontend always consumes valid data structures.

### X. FOSS Principles

The project MUST remain Free and Open Source Software:

**Licensing**:
- All code licensed under OSI-approved open source license
- Dependencies MUST use compatible licenses (no proprietary, GPL-compatible)
- License compatibility MUST be verified in CI
- Clear LICENSE file in repository root
- License headers in source files (where applicable)

**Privacy & User Control**:
- No telemetry or tracking without explicit user consent
- No data sent to third parties without user knowledge
- User data stays local unless explicitly configured otherwise
- Opt-in (not opt-out) for any external communication
- Clear privacy policy if any data collection occurs

**Transparency & Auditability**:
- All functionality auditable from source code
- No obfuscation or hidden behavior
- Security practices documented openly
- Dependency supply chain transparent (lock files, SBOMs)

**Offline Capability**:
- Core functionality MUST work offline (no mandatory cloud dependencies)
- Graceful degradation when network unavailable
- Local configuration files (no mandatory remote config)
- Documentation available offline

**Community Ownership**:
- Governance documented and transparent
- Contributor License Agreement (CLA) avoided unless legally necessary
- Project accepts community contributions
- Roadmap publicly visible

**Rationale**: FOSS principles ensure user autonomy, trust, and long-term sustainability. Open source projects handling user data or workflows must be fully auditable and respect user freedom.

### XI. Resource Efficiency

All components MUST minimize resource consumption:

**Network Efficiency**:
- Incremental operations (avoid re-fetching unchanged data)
- Compression for data transfer
- API rate limiting and backoff strategies
- Batch requests where possible
- Connection reuse and keep-alive

**Disk Efficiency**:
- Avoid unnecessary file writes
- Use streaming for large files (no full in-memory loads)
- Clean up temporary files promptly
- Efficient storage formats (avoid bloat)
- Configurable cache size limits

**Memory Efficiency**:
- Bounded memory usage via streaming and pagination
- Avoid loading entire datasets into memory
- Release resources promptly (close file handles, connections)
- Memory profiling for large-scale operations
- Configurable memory limits

**CPU Efficiency**:
- Avoid unnecessary computation
- Use efficient algorithms (O(n) vs O(n²) matters)
- Lazy evaluation where appropriate
- Parallel processing for independent tasks (where beneficial)
- Profiling for performance-critical paths

**Energy Awareness**:
- Minimize polling (use event-driven patterns)
- Avoid busy-waiting loops
- Efficient data structures
- Consider environmental impact of compute-intensive operations

**Rationale**: Efficient resource usage enables deployment on resource-constrained environments (edge devices, CI runners, shared hosting), reduces costs, and minimizes environmental impact. Responsible computing practices make the project accessible to more users.

## Quality Standards

### Testing Coverage

**Backend/Library Testing**:
- Unit tests: MUST cover all public APIs and error paths
- Integration tests: MUST cover component interactions
- Regression tests: MUST be added for every bug fix
- Performance tests: SHOULD be added for performance-critical paths

**Frontend Testing**:
- Component unit tests: MUST cover individual UI components in isolation
- Integration tests: MUST cover component interactions and state management
- User workflow tests: MUST cover end-to-end user scenarios (E2E testing)
- Visual regression tests: SHOULD be added for UI components
- Accessibility tests: MUST verify WCAG 2.1 AA compliance
- Schema validation tests: MUST verify frontend correctly consumes library output

**Testing Frameworks**:
- Backend: pytest, Jest, cargo test, or language-appropriate framework
- Frontend: Vitest/Jest (unit), Testing Library (integration), Playwright/Cypress (E2E)

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

**Duplication Detection (Principle VIII enforcement)**:

Reviewers MUST actively check for:
1. **Copy-paste code**: Identical or near-identical code blocks
2. **Similar logic**: Different implementations solving the same problem
3. **Missed opportunities**: New code duplicating existing functionality
4. **Refactoring needs**: Existing functions that could be reused

Review checklist:
- [ ] Search codebase for similar functionality before approving new code
- [ ] Verify no existing function/module provides the same capability
- [ ] Check for repeated patterns that could be abstracted
- [ ] Suggest specific existing code to reuse if found
- [ ] Require refactoring if duplication detected (no "TODO: refactor later")

**Automated duplication checks**:
- CI MUST run duplication detection tools
- CI MUST fail if duplication threshold exceeded (>3% recommended)
- Reports MUST highlight specific duplicated blocks with line numbers

### Frontend Architecture

**Component Structure**:
- **Presentational components**: Pure UI rendering (no business logic)
- **Container components**: Connect presentational components to data/state
- **Custom hooks**: Reusable logic extraction (React) or composables (Vue)
- **Services layer**: API calls and data transformation separated from components

**State Management**:
- Local state for component-specific UI state
- Shared state for cross-component data (Context, Redux, Vuex, etc.)
- Derived state computed from source data (no duplication)
- State updates MUST be predictable and debuggable

**Data Flow**:
```
Library Output (JSON/CLI) → Schema Validation → Data Models → State Management → UI Components
```

**Frontend Independence**:
- No backend API dependency (operates on library output)
- Static build deployable to CDN/static hosting
- Offline-capable where feasible
- Progressive enhancement (works without JavaScript for core content)

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

**Version**: 1.3.0 | **Ratified**: 2026-01-24 | **Last Amended**: 2026-01-24
