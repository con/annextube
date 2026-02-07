---
title: "Troubleshooting"
description: "Common issues and solutions for annextube"
weight: 100
---

# Troubleshooting

This guide covers common issues you might encounter when using annextube and how to resolve them.

## yt-dlp Challenge Solver Version Errors

### Symptom

When running `annextube backup`, you see errors like:

```
yt_dlp: [youtube] [jsc:deno] Challenge solver lib script version 0.3.2 is not supported
(source: python package, variant: ScriptVariant.MINIFIED, supported version: 0.4.0)
```

### Cause

This error occurs when yt-dlp's JavaScript challenge solver dependencies are outdated. The challenge solver is used to bypass YouTube's bot detection mechanisms.

### Solution

Upgrade yt-dlp with all its default dependencies:

```bash
python3 -m pip install -U "yt-dlp[default]"
```

Or if using uv:

```bash
uv pip install -U "yt-dlp[default]"
```

**Note:** The `[default]` extra is important - it includes dependencies like the Deno JavaScript runtime needed for the challenge solver.

### Prevention

If you're installing annextube in a fresh environment, ensure you're using a recent version:

```bash
pip install -U "annextube[devel]"  # Includes recent yt-dlp>=2026.2.0
```

The project's `pyproject.toml` specifies `yt-dlp>=2026.2.0`, which includes the required challenge solver version, but existing installations may have outdated dependencies that need manual updating.

---

## More Troubleshooting Topics

(To be added as issues are encountered and documented)
