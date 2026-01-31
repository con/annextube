# YouTube Cookie Support Demo - Complete Guide

## Summary of Cookie Implementation

✅ **Successfully implemented:**
- User-wide configuration system with `platformdirs`
- Cookie support via `cookies_file` and `cookies_from_browser`
- Configuration passed to both yt-dlp Python API and git-annex CLI
- Network settings (proxy, rate limiting)
- Extractor args support for advanced yt-dlp options

## The Challenge: YouTube's n-challenge

When using cookies with YouTube, yt-dlp encounters YouTube's "n-challenge" - a JavaScript obfuscation that requires a JavaScript runtime to solve.

### Two Approaches

#### Approach 1: Cookies + deno (RECOMMENDED for authenticated content)
**Pros:** Works with age-restricted, members-only, liked videos
**Cons:** Requires deno runtime

**Setup:**
```bash
# Install deno (or use your miniconda environment)
curl -fsSL https://deno.land/install.sh | sh

# Create user config
annextube init-user-config

# Edit ~/.config/annextube/config.toml
cookies_file = "/path/to/cookies.txt"

# Run backup (deno must be in PATH)
annextube backup
```

#### Approach 2: Android Client without Cookies (for public content)
**Pros:** No deno required
**Cons:** No authentication, public videos only

**Setup:**
```bash
# Create user config
annextube init-user-config

# Edit ~/.config/annextube/config.toml
# Android client bypasses n-challenge but doesn't support cookies
ytdlp_extra_opts = ["--extractor-args", "youtube:player_client=android"]

# Run backup (works without deno, public videos only)
annextube backup
```

## Why Android Client + Cookies Don't Work Together

From yt-dlp output:
```
WARNING: [youtube] Skipping client "android" since it does not support cookies
```

This is a **yt-dlp limitation**, not an annextube bug. The Android client API endpoint doesn't accept authentication.

## Working Demo Script (Public Content, No Cookies)

See `demo-public-no-auth.sh` for a complete working demo without authentication.

## Working with Cookies + deno

For a demo with full cookie support:

```bash
# In your miniconda environment with deno
source ~/miniconda3.sh
conda activate deno

# Create user config with cookies
annextube init-user-config
cat >> ~/.config/annextube/config.toml << 'EOF'

# Cookies for authenticated content
cookies_file = "/home/yoh/proj/annextube/.git/yt-cookies.txt"
EOF

# Run backup - now with full authentication support
export YOUTUBE_API_KEY="your-key"
annextube init /tmp/demo "@apopyk" --videos --limit 2
annextube backup --output-dir /tmp/demo
```

## Testing

### Test 1: User Config System ✅
```bash
$ annextube init-user-config
✓ Created user config template
```

### Test 2: Config Loading ✅
```python
from annextube.lib.config import load_config
config = load_config(repo_path="/path/to/archive")
print(config.user.cookies_file)  # Shows cookie path
```

### Test 3: git-annex Configuration ✅
```bash
$ cd /path/to/archive
$ git config annex.youtube-dl-options
--cookies "/path/to/cookies.txt"
```

### Test 4: yt-dlp Python API ✅
YouTubeService properly receives:
- `cookiefile` option
- `extractor_args` option
- All network settings

## Implementation Files

- `annextube/lib/config.py` - UserConfig, platformdirs integration
- `annextube/services/youtube.py` - Cookie and extractor args support
- `annextube/services/git_annex.py` - git-annex configuration
- `annextube/services/archiver.py` - Extractor args parsing
- `annextube/cli/init_user_config.py` - CLI command

## Configuration Hierarchy

```
Environment Variables (ANNEXTUBE_COOKIES_FILE, etc.)
    ↓
Archive Config (.annextube/config.toml)
    ↓
User Config (~/.config/annextube/config.toml)
    ↓
Built-in Defaults
```

## User Config Location (Cross-Platform)

- **Linux**: `~/.config/annextube/config.toml`
- **macOS**: `~/Library/Application Support/annextube/config.toml`
- **Windows**: `%APPDATA%\annextube\config.toml`

## Example User Config

```toml
# Authentication
cookies_file = "~/.config/annextube/cookies/youtube.txt"
# OR
cookies_from_browser = "firefox"

# API key (or use YOUTUBE_API_KEY env var)
# api_key = "your-key-here"

# Network
proxy = "socks5://127.0.0.1:9050"
limit_rate = "1M"
sleep_interval = 3
max_sleep_interval = 5

# Advanced (Android client - public videos only, no cookies!)
# ytdlp_extra_opts = ["--extractor-args", "youtube:player_client=android"]
```

## Next Steps

1. **For authenticated content**: Set up deno and use cookies
2. **For public content**: Use without cookies or with Android client
3. **For Containerfile**: Use deno-enabled base image (e.g., miniforge with deno)

## References

- [yt-dlp Cookie Guide](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [yt-dlp Extractors](https://github.com/yt-dlp/yt-dlp/wiki/Extractors)
- [YouTube n-challenge](https://github.com/yt-dlp/yt-dlp/wiki/EJS)
