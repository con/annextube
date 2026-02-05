# Container Deployment Guide

This guide covers deploying annextube using containers (Podman, Docker, or Singularity/Apptainer).

## Quick Start

### Podman (Recommended)

```bash
# Build container
podman build -t annextube:latest -f Containerfile .

# Initialize archive
mkdir my-archive && cd my-archive
podman run -it --rm -v $PWD:/archive annextube:latest init

# Configure (edit .annextube/config.toml)
# Add your YouTube Data API key and channel URLs

# Backup
podman run -it --rm \
  -v $PWD:/archive \
  -e YOUTUBE_API_KEY="your-api-key" \
  annextube:latest backup

# Generate web interface
podman run -it --rm -v $PWD:/archive annextube:latest generate-web
```

### Docker

Same commands as Podman, just replace `podman` with `docker`:

```bash
docker build -t annextube:latest -f Containerfile .
docker run -it --rm -v $PWD:/archive annextube:latest backup
```

### Singularity/Apptainer

```bash
# Build SIF from local container image
podman build -t annextube:latest -f Containerfile .
apptainer build annextube.sif docker-daemon://annextube:latest

# Or build directly from Dockerfile
apptainer build annextube.sif Containerfile

# Run
apptainer run --bind $PWD:/archive annextube.sif backup

# Shell into container
apptainer shell --bind $PWD:/archive annextube.sif
```

## Container Details

### Included Dependencies

The container includes:

- **Python 3.11+**: Runtime
- **git**: Version control
- **git-annex**: Large file management
- **yt-dlp**: YouTube download tool (system-wide in PATH)
- **ffmpeg**: Video processing
- **deno**: Lightweight JavaScript runtime (for YouTube n-challenge solver)
- **uv**: Fast Python package installer
- **annextube**: Installed and ready to use

### Size

- Compressed: ~300 MB
- Uncompressed: ~800 MB

Minimal compared to alternatives (no Node.js, no conda, no unnecessary dev tools).

## Usage Patterns

### Interactive Session

```bash
# Start interactive shell
podman run -it --rm -v $PWD:/archive annextube:latest bash

# Inside container:
annextube init
annextube backup
annextube generate-web
```

### Automated Backup (Cron/Systemd)

Create a script `backup-youtube.sh`:

```bash
#!/bin/bash
set -euo pipefail

ARCHIVE_DIR="/path/to/my-archive"
YOUTUBE_API_KEY="$(cat /path/to/secret/api-key.txt)"

podman run --rm \
  -v "$ARCHIVE_DIR":/archive:Z \
  -e YOUTUBE_API_KEY="$YOUTUBE_API_KEY" \
  annextube:latest backup

# Optional: generate updated web interface
podman run --rm \
  -v "$ARCHIVE_DIR":/archive:Z \
  annextube:latest generate-web
```

Run via cron:
```cron
# Daily backup at 2 AM
0 2 * * * /home/user/backup-youtube.sh >> /var/log/annextube-backup.log 2>&1
```

### With Cookies (Private Playlists)

```bash
podman run -it --rm \
  -v $PWD:/archive \
  -v $HOME/.config/annextube/cookies.txt:/cookies.txt:ro \
  -e YOUTUBE_API_KEY="your-api-key" \
  annextube:latest backup
```

Then reference in your `.annextube/config.toml`:
```toml
cookies_file = "/cookies.txt"
```

### HPC/Cluster Usage (Singularity)

```bash
#!/bin/bash
#SBATCH --job-name=annextube-backup
#SBATCH --time=04:00:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=2

module load singularity

ARCHIVE_DIR="/work/project/youtube-archive"
export YOUTUBE_API_KEY="your-api-key"

singularity run \
  --bind "$ARCHIVE_DIR":/archive \
  --env YOUTUBE_API_KEY \
  /shared/containers/annextube.sif backup
```

## Advanced Configuration

### Building with Custom Base Image

```dockerfile
# Use Alpine for smaller size (advanced users)
FROM alpine:3.19

RUN apk add --no-cache \
    git git-annex python3 py3-pip ffmpeg curl

# ... rest of Containerfile
```

### Multi-Architecture Builds

```bash
# Build for multiple architectures
podman build --platform linux/amd64,linux/arm64 -t annextube:latest .

# Or use buildx with Docker
docker buildx build --platform linux/amd64,linux/arm64 -t annextube:latest .
```

### Rootless Podman

Recommended for security:

```bash
# No sudo needed
podman build -t annextube:latest .
podman run --rm -v $PWD:/archive:Z annextube:latest backup

# SELinux users: note the :Z flag for proper labeling
```

## Troubleshooting

### Permission Issues

**Problem**: Files created by container are owned by root

**Solution**: Use user namespaces

```bash
# Podman (automatic user namespaces)
podman run --rm -v $PWD:/archive:Z annextube:latest backup

# Docker (map to current user)
docker run --rm --user $(id -u):$(id -g) -v $PWD:/archive annextube:latest backup
```

### YouTube Download Failures

**Problem**: "n challenge solving failed"

**Solution**: Container includes deno. Use EJS solver:

In your user config (`$HOME/.config/annextube/config.toml`):
```toml
ytdlp_extra_opts = ["--remote-components", "ejs:github"]
```

Or use Android client workaround:
```toml
ytdlp_extra_opts = ["--extractor-args", "youtube:player_client=android"]
```

### Git-annex Special Remotes

To use special remotes (S3, WebDAV, etc.):

```bash
# Install special remote support
# Add to Containerfile:
RUN pip3 install --no-cache-dir --break-system-packages git-annex-remote-rclone

# Or use git-annex built-in remotes (S3, WebDAV, etc.)
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Backup YouTube Archive

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/con/annextube:latest
    steps:
      - name: Checkout archive
        uses: actions/checkout@v4
        with:
          repository: your-org/your-archive-repo

      - name: Backup
        env:
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
        run: annextube backup

      - name: Generate web
        run: annextube generate-web

      - name: Commit changes
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add .
          git commit -m "Automated backup $(date)" || true
          git push
```

### GitLab CI

```yaml
backup:
  image: annextube:latest
  script:
    - annextube backup
    - annextube generate-web
    - git add .
    - git commit -m "Automated backup" || true
    - git push
  variables:
    YOUTUBE_API_KEY: $YOUTUBE_API_KEY
  only:
    - schedules
```

## Performance Tips

1. **Use bind mounts for archive**: Faster than copying data in/out
2. **Pre-download yt-dlp**: Container includes it system-wide
3. **Enable deno caching**: Mount deno cache directory
4. **Use specific tags**: Don't rely on `:latest` in production

## Security Best Practices

1. **Never embed secrets in container**: Use environment variables or mounted files
2. **Run rootless**: Use Podman or Docker with user namespaces
3. **Read-only mounts**: Mount cookies as `:ro` (read-only)
4. **Scan images**: Use `podman scan` or `trivy` before deployment
5. **Pin versions**: Use specific git-annex and yt-dlp versions for reproducibility

## See Also

- [Installation Guide](../tutorial/01-installation.md)
- [Quick Start](../../specs/001-youtube-backup/quickstart.md)
- [Git-annex Integration](../reference/git-annex-integration.md)
