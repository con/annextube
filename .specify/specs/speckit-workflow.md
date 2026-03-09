# Spec-Kit Development Workflow for annextube

## Glossary

| Term             | Meaning                                                                                         |
|------------------|-----------------------------------------------------------------------------------------------------|
| **FR**           | Functional Requirement — a numbered spec entry (e.g., FR-042) describing one thing the system must do |
| **NFR**          | Non-Functional Requirement — quality attribute (performance, security, accessibility)               |
| **SC**           | Success Criterion — a measurable validation target (e.g., "loads in < 3s")                         |
| **TDD**          | Test-Driven Development — write a failing test first, then implement to make it pass               |
| **Constitution** | Project governance doc (`.specify/memory/constitution.md`) — immutable principles all features must respect |
| **Spec**         | Feature specification (`spec.md`) — the "what and why", no implementation details                  |
| **Plan**         | Implementation plan (`plan.md`) — the "how": tech stack, architecture, file structure              |
| **Tasks**        | Ordered checklist (`tasks.md`) — dependency-aware, parallelization-marked work items (T001, T002...) |
| **`[P]`**        | Parallelizable task marker — safe to run concurrently with other `[P]` tasks in the same phase     |
| **`[US1]`**      | User Story link — ties a task to a specific user story in the spec                                 |

## Problem

Development has been "vibe-coded" — features implemented ad-hoc without
going through the spec-kit pipeline. This caused massive drift: ~45 tasks
marked pending but already done, 14 features implemented without FRs, 6
terminology mismatches, and obsolete entities still in the spec. The
harmonization commit (e35d823) patched the worst gaps, but the process
needs to change to prevent recurrence.

## The Core Principle

**Spec is the source of truth. Code is its expression.**

Every change to the codebase — new feature, planned work, or bugfix —
should have a traceable path through the spec artifacts. The depth of
that path scales with the change's complexity.

---

## Workflow by Change Type

### 1. New Feature (not in spec)

Full pipeline. This is what spec-kit was designed for.

```
/speckit.specify "Add playlist auto-discovery from channel tabs"
    ↓
/speckit.clarify          # if spec has [NEEDS CLARIFICATION]
    ↓
/speckit.plan             # produces research.md, plan.md, data-model.md
    ↓
/speckit.tasks            # produces tasks.md with T001, T002...
    ↓
/speckit.analyze          # read-only consistency check (RECOMMENDED)
    ↓
/speckit.implement        # TDD, phase-by-phase, marks [X] in tasks.md
```

**Key discipline**: Do NOT start coding until `/speckit.tasks` has
produced `tasks.md`. The temptation to "just start building" is exactly
what caused the drift. The 15 minutes spent on specify+plan saves hours
of harmonization later.

**When to skip steps**: `/speckit.clarify` can be skipped for
well-understood features. `/speckit.analyze` can be skipped for small
features (< 5 tasks). Never skip `/speckit.specify` and `/speckit.plan`.

### 2. Planned Work (already in spec)

The spec and plan already exist in `specs/001-youtube-backup/`. The work
is implementing pending tasks or TODO items from `plan.md`.

```
1. Read the relevant section of tasks.md — find pending tasks
2. Read the corresponding plan.md section for implementation guidance
3. Implement with TDD, following the plan
4. Mark tasks [X] in tasks.md as you complete them
5. If the plan is wrong or outdated, UPDATE plan.md FIRST, then implement
```

**No new spec directory needed** — this work lives in the existing
`specs/001-youtube-backup/` feature. Just pick up where the spec left off.

**If scope grows**: If implementing a planned task reveals it needs
significant new design (new entities, new CLI commands, new services),
STOP and use `/speckit.specify` (for a new feature branch) or
`/speckit.clarify` (to refine the existing spec) before continuing.
The rule: if you're about to write code that no FR describes, add the
FR first — via the speckit pipeline, not manual edits.

### 3. Bugfix / Troubleshooting

Bugfixes don't need the full pipeline, but they DO need spec awareness.

**Small fix** (typo, off-by-one, missing null check):
```
1. Fix the bug
2. Add a regression test (TDD: write failing test first if practical)
3. No spec changes needed
```

**Behavioral fix** (changes observable behavior, affects an FR):
```
1. Identify which FR(s) the bug relates to
2. If the FR is wrong/incomplete → /speckit.clarify to refine it
3. Write a failing test that demonstrates the bug
4. Fix the bug
5. If the fix changes the implementation approach → /speckit.plan to update
```

**Architectural fix** (refactoring, dependency changes like DataLad):
```
1. /speckit.plan    — update the approach (deps, architecture, structure)
2. /speckit.specify — update FRs if requirements change (new deps, removed entities)
3. /speckit.tasks   — regenerate or update task list (marks obsolete, adds new)
4. /speckit.implement — execute the tasks
5. /speckit.analyze — verify consistency across all artifacts
```

The DataLad-as-core-dependency change was this type — it should have
started with `/speckit.plan` to update the dependency section, then
`/speckit.specify` to add FR-097–100 and mark SyncState obsolete,
BEFORE writing the code.

---

## Gatekeeping: Preventing Drift

### Gate 1: Pre-implementation Check (manual, per-session)

Before starting any coding session, ask yourself:

> "Is there a spec artifact (FR, task, plan section) that describes
> what I'm about to build?"

- **Yes** → proceed, reference the FR/task ID in your commit message
- **No, but it's trivial** → proceed (bugfix, typo, config tweak)
- **No, and it's non-trivial** → STOP. Run `/speckit.specify` or update
  the existing spec first.

### Gate 2: Commit Message Convention

Include spec references in commit messages when applicable:

```
Add playlist auto-discovery (FR-002a, FR-002b)

- Implement _discover_playlists() in archiver.py
- Add include_playlists config field
- Tasks: T045, T046, T047

Co-Authored-By: ...
```

This creates a traceable link from git history to spec artifacts.

### Gate 3: Periodic `/speckit.analyze` (weekly or per-milestone)

Run `/speckit.analyze` periodically to catch drift early. This is the
read-only consistency check that produces a severity-ranked findings
table. Treat CRITICAL findings as blockers.

Suggested cadence:
- After completing a batch of related tasks
- Before tagging a release
- When onboarding a new contributor
- After any "vibe coding" session (be honest with yourself)

### Gate 4: Pre-release Spec Sync

Part of the existing pre-release process (`specs/001-youtube-backup/pre-release-checks.md`).
Run all checks with a single command:

```bash
uv run tox -e sdist-check,spec-check
```

The `spec-check` tox environment (see `tox.ini`) automates:
- No unresolved `[NEEDS CLARIFICATION]` in specs
- Task completion summary (done / total)
- Every CLI command has a corresponding FR in spec.md

See also: `/speckit.analyze` for deeper cross-artifact consistency
checking before a release.

---

## Quick Reference Card

| Situation | Minimum spec work required |
|-----------|---------------------------|
| New feature (> 1 day of work) | Full pipeline: specify → plan → tasks → implement |
| New feature (< 1 day) | specify → plan → implement (skip tasks if < 5 steps) |
| Planned task from tasks.md | Read plan, `/speckit.implement`, mark [X] |
| Bug that changes behavior | `/speckit.clarify` if FR needs update, write test, fix |
| Bug that doesn't change behavior | Write test, fix |
| Refactoring / dependency change | `/speckit.plan` → `/speckit.specify` → `/speckit.tasks` → implement |
| "I already built it without spec" | `/speckit.analyze` → fix artifacts via speckit commands |

## What NOT to Do

- **Don't let specs rot.** A spec that doesn't match the code is worse
  than no spec — it actively misleads. If you vibe-coded something,
  update the spec immediately after, not "later."

- **Don't over-specify trivially.** A one-line config change doesn't need
  `/speckit.specify`. Use judgment — the pipeline exists to prevent
  drift on non-trivial work, not to bureaucratize every keystroke.

- **Don't treat analyze as optional after vibe-coding.** If you skipped
  the pipeline, `/speckit.analyze` is your safety net. Run it.

- **Don't amend specs to match bad code.** If the code is wrong, fix the
  code. Specs describe intended behavior, not accidental behavior.
  Exception: if the spec was wrong and the code is actually better,
  update the spec with a note explaining why.

---

## Recovering from Drift (when it happens anyway)

It will happen. When it does:

1. `/speckit.analyze` — quantify the damage (read-only, severity-ranked)
2. `/speckit.plan` — fix terminology, architecture, project structure
3. `/speckit.specify` — add missing FRs for implemented features
4. `/speckit.tasks` — regenerate task list (checks off done, marks obsolete)
5. Commit the harmonization as a dedicated commit (like e35d823)
6. Resume the pipeline from wherever it makes sense

The harmonization we just did is the template for this recovery process.
The goal is to make it rare, not to pretend it won't happen.
