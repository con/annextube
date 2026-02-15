# Pre-release Checks

Checklist to run before tagging a release to ensure the sdist is clean and
the built frontend is included.

## 0. Run the automated sdist check

```bash
uv run tox -e sdist-check
```

This builds the sdist, installs it in a clean venv, deletes the local
`web/` directory, and verifies that the installed package contains the
built frontend and that `generate-web` works.  **This single command
covers steps 1-6 below automatically.**  If it passes, the manual checks
are optional but still useful for eyeballing the tarball contents.

## 1. Build the sdist

```bash
uv run python -m build --sdist --outdir /tmp/annextube-sdist
```

The build hook must print:

```
Building web frontend...
Compiling Svelte frontend...
Frontend build complete! Output: /home/yoh/proj/annextube/web
```

If it prints "Warning: npm not found", install npm first.

## 2. Verify the tarball size

```bash
du -sh /tmp/annextube-sdist/annextube-*.tar.gz
```

Expected: under 500KB.  If it's in the megabytes, something is wrong (large
test fixtures, frontend node_modules, or dev tool caches leaking in).

## 3. Verify built frontend is included

```bash
tar -tf /tmp/annextube-sdist/annextube-*.tar.gz | grep 'web/'
```

Must show at least:

```
.../web/index.html
.../web/assets/index.js
.../web/assets/index.css
```

## 4. Verify no junk is included

```bash
tar -tf /tmp/annextube-sdist/annextube-*.tar.gz | grep -E '(frontend/|node_modules|playwright|specs/|tools/|\.claude/|\.specify/|\.mp4|package-lock|caption\.png)'
```

This must produce **no output**.  If it does, update the `exclude` list in
`[tool.hatch.build.targets.sdist]` in `pyproject.toml`.

## 5. Verify the largest files are reasonable

```bash
tar -tzvf /tmp/annextube-sdist/annextube-*.tar.gz | sort -n -k 3 | tail -10
```

The largest file should be `web/assets/index.js` (the compiled Svelte
bundle, ~120KB).  Nothing should be over 200KB.

## 6. Test install from sdist

```bash
uv pip install /tmp/annextube-sdist/annextube-*.tar.gz --force-reinstall
annextube --help
```

Should install cleanly and the CLI should be functional.
