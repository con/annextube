---
description: Diagnose the latest annextube-cron failure from duct logs, identify root cause, check if already fixed, and propose solutions.
---

## Troubleshoot annextube-cron

Analyze the latest con-duct log from the annextube-cron runner, identify why
the cron job failed, and recommend next steps.

### Step 1: Locate the latest duct log

Find the most recent run in `$ANNEXTUBE-cron/.duct/logs/` (where $ANNEXTUBE is the current
codebase top directory) by sorting the `_info.json` files by name (they
are timestamped).

```
CRON_DIR=$ANNEXTUBE-cron
LOG_DIR=$CRON_DIR/.duct/logs
```

Pick the latest `*_info.json` and derive the prefix for `_stderr`, `_stdout`,
`_usage.jsonl`.

### Step 2: Ensure log content is accessible

The log files may be git-annex symlinks with content only on smaug. Check if
the `_stderr` and `_stdout` files are readable:

1. If they are broken symlinks → run `git -C $CRON_DIR annex get <file>` to
   fetch them. If that fails (e.g., read-only filesystem, no SSH access),
   report clearly: "Log content is only available on smaug. Run
   `git annex get .duct/logs/<prefix>_stderr .duct/logs/<prefix>_stdout`
   on a machine that can reach smaug, then retry."
2. If they are readable → proceed.

### Step 3: Read the info.json

Extract and report:
- **Exit code**
- **Wall clock time**
- **Command** that was run
- **Hostname** and **start/end times**

If exit code is 0, report "Latest cron run succeeded" and stop.

### Step 4: Read stderr and stdout

Read both files. The stderr typically contains the `set -x` trace (PS4='> ')
showing each command executed, plus annextube log output. The stdout contains
annextube's normal output (summary lines, datalad run/save/push output).

**Important**: These files can be large (50-100KB). Read them fully. Look for:

1. **The failure point**: Where did the script stop? Look for:
   - `run(impossible):` — datalad run refused (dirty dataset)
   - `run(error):` — command failed inside datalad run
   - Python tracebacks
   - `ERROR:` lines from yt-dlp or annextube
   - Shell errors from `set -eu` (command not found, permission denied, etc.)

2. **The annextube version**: Find the version string, typically in a line like:
   ```
   annextube, version 0.X.Y.postN+gHASH
   ```
   or in the backup output:
   ```
   annextube 0.X.Y.postN+gHASH with yt-dlp YYYY.MM.DD
   ```

3. **Which collection/channel failed**: The script loops over multiple top-level
   directories (ReproTube, src-youtube, dandi, bbqs, scrap/yoh) and within each
   loops over `*/.annextube` subdirectories. Identify which specific channel
   dataset caused the failure.

4. **What succeeded before the failure**: Count how many channels completed
   successfully before the failure point.

### Step 5: Extract the annextube version and check if issue is already fixed

From the version string found in step 4:

1. Extract the git commit hash (the `gHASH` part after `+`)
2. Compare against the current HEAD in `$ANNEXTUBE`:
   ```
   git -C $ANNEXTUBE log --oneline <HASH>..HEAD
   ```
3. Check if any commits since that version address the identified issue.
   Look at commit messages for relevant keywords (the error type, the
   channel name, the specific failure mode).
4. Also compare the installed version tag against the latest tag:
   ```
   git -C "$ANNEXTUBE" tag --list 'v*' --sort=-v:refname | head -1
   ```

Report:
- "Cron was running version X, current HEAD is Y (N commits ahead)"
- "Latest release tag is vZ.Z.Z"
- Whether any of the intervening commits appear to fix the issue

### Step 6: Diagnose root cause

Based on the failure output, classify the root cause into one of these
categories and provide specific diagnosis:

| Category | Indicators | Typical cause |
|----------|-----------|---------------|
| **Dirty dataset** | `run(impossible): ... clean dataset required` | Previous failed run left uncommitted changes |
| **yt-dlp error** | `ERROR: [youtube]` lines | Bot detection, rate limiting, unavailable videos, cookies expired |
| **Pagefind stall** | Timeout or hang after "Building search index" | IPC deadlock (check if fixed in newer commits) |
| **Git/annex error** | `git-annex:` error, `fatal:` git error | Disk full, permission denied, lock contention |
| **Network error** | Connection refused, timeout, DNS | Transient network issue |
| **Python exception** | Traceback | Bug in annextube code |
| **Config error** | Missing config, bad TOML | Misconfigured channel |
| **Shell error** | Command not found, permission denied | Environment issue (conda not activated, missing dep) |

### Step 7: Propose mitigation

Based on the diagnosis, recommend:

1. **Immediate fix** — what to do right now to unblock the cron job
   (e.g., "run `datalad save -d /path/to/dirty-dataset` on smaug")

2. **Preventive fix** — if this is a recurring pattern, propose a code change
   in annextube that would prevent it. Reference the collection management
   spec at `.specify/specs/multi-channel-collections.md` Phase 2 if the fix
   aligns with `collection backup` resilience goals (continue-on-failure,
   dirty dataset handling).

3. **Version upgrade** — if the issue is already fixed in a newer commit,
   recommend upgrading: "Upgrade annextube on smaug to latest (pip install -e .)
   or to release vX.Y.Z"

### Output format

Structure your response as:

```
## Cron Failure Diagnosis

**Run**: <timestamp> on <hostname>
**Exit code**: <N> after <duration>
**Annextube version**: <version> (current: <current>, latest tag: <tag>)

### What happened

<1-3 sentence summary of what the script was doing when it failed>

### Root cause

<Category>: <specific explanation>

### Failed at

<Which collection / channel / command failed>
<N channels succeeded before failure>

### Already fixed?

<Yes/No — with commit references if yes>

### Recommended actions

1. **Immediate**: <what to do now>
2. **Preventive**: <code change or config change>
3. **Version**: <upgrade recommendation if applicable>
```
