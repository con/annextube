# Test Scripts for Cookie Implementation

## Issue with Bash Tool

Every bash command returns `exit code 1` with no output or error message, including simple commands like `echo "test"`. This prevents direct execution of git commands or test scripts through the tool interface.

## Workaround: Manual Execution Scripts

Created scripts for you to run manually:

### Quick Start

```bash
cd /home/yoh/proj/annextube/test-archives
chmod +x *.sh
./RUN-ALL.sh
```

This will:
1. Remove test-archives files from git (they're .gitignored)
2. Commit the git-annex cookie path fix (removed quotes)
3. Run complete test with miniconda + deno setup

### Individual Scripts

#### 1. `cleanup-git.sh`
Removes test-archives files from git history (since they're .gitignored)

```bash
./cleanup-git.sh
```

#### 2. `commit-fix.sh`
Commits the git-annex.py fix that removes quotes from cookie paths

```bash
./commit-fix.sh
```

#### 3. `complete-test.sh`
Complete end-to-end test:
- Installs miniconda3 under `test-archives/miniconda3/`
- Creates deno conda environment
- Installs yt-dlp and annextube in that environment
- Sets HOME to `test-archives/fake-home-demo/`
- Creates user config with cookies + EJS solver
- Initializes archive
- Runs backup
- Tests git-annex addurl directly
- Generates web interface
- Reports results

```bash
./complete-test.sh
```

#### 4. `RUN-ALL.sh`
Runs all three scripts in order with pauses between steps

## What Gets Created

```
test-archives/
├── miniconda3/                    ← Conda installation
│   └── envs/deno/                 ← Deno environment
├── fake-home-demo/                ← Fake HOME directory
│   ├── .config/annextube/         ← User config
│   └── archive/                   ← Git-annex repository
│       ├── .git/
│       ├── videos/
│       └── web/
├── commit-fix.sh                  ← Git commit script
├── cleanup-git.sh                 ← Remove from git
├── complete-test.sh               ← Main test
└── RUN-ALL.sh                     ← Run everything

All installed under test-archives/ (not in system directories)
Everything uses the same Python/deno environment
HOME is set to fake-home-demo for complete isolation
```

## The Fix

**In `annextube/services/git_annex.py`:**

```python
# Before (with quotes):
options.append(f'--cookies "{cookie_path}"')
options.append(f'--proxy "{proxy}"')

# After (no quotes):
options.append(f'--cookies {cookie_path}')
options.append(f'--proxy {proxy}')
```

This generates cleaner git config:
```
# Before:
annex.youtube-dl-options = --cookies "/path/to/cookies.txt" ...

# After:
annex.youtube-dl-options = --cookies /path/to/cookies.txt ...
```

## Expected Results

**If cookies + deno work properly:**
- ✅ Metadata downloaded with authentication
- ✅ Captions downloaded
- ✅ Comments downloaded
- ✅ Thumbnails downloaded
- ✅ Video URLs tracked in git-annex (if addurl works)

**If git-annex addurl still fails:**
- ✅ All metadata/captions/comments work
- ❌ Video URL tracking fails (needs investigation)

## Testing git-annex Directly

The complete-test.sh script includes a direct test:

```bash
cd fake-home-demo/archive
git annex addurl 'https://www.youtube.com/watch?v=VIDEO_ID' \
    --file test-video.mkv --relaxed --fast --no-raw
```

This will show if the issue is:
- Cookie path format (fixed by removing quotes)
- git-annex YouTube support
- yt-dlp configuration
- Something else

## Cleanup

To remove everything:
```bash
chmod -R u+w test-archives/fake-home-demo test-archives/miniconda3
rm -rf test-archives/fake-home-demo test-archives/miniconda3
```

## Next Steps

1. Run `./RUN-ALL.sh` to execute all tests
2. Check `test-output.log` for results
3. If video downloads work → commit success
4. If video downloads fail → investigate git-annex addurl error
