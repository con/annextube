# annextube

YouTube archive system using git-annex for efficient storage and incremental updates.

## Features

- **Complete channel archival**: Videos, metadata, comments, and captions
- **Incremental updates**: Efficient detection of new content
- **Offline browsing**: Client-side web interface (no server required)
- **Flexible filtering**: By date, license, playlist, metadata attributes
- **CI/CD automation**: GitHub Actions and Codeberg Actions support
- **Git-annex integration**: Efficient storage with special remotes (S3, WebDAV, etc.)

## Quick Start

```bash
# Install
pip install annextube

# Create archive
mkdir my-archive && cd my-archive
annextube init

# Configure (edit .annextube/config.toml)
# Add YouTube Data API key and channel URLs

# Backup
annextube backup

# Browse offline
annextube generate-web
open web/index.html
```

## Documentation

- **Installation**: See [docs/tutorial/01-installation.md](docs/content/tutorial/01-installation.md)
- **Quick Start**: See [specs/001-youtube-backup/quickstart.md](specs/001-youtube-backup/quickstart.md)
- **API Reference**: See [docs/reference/](docs/content/reference/)

## System Requirements

### Required

- **Python 3.10+**: Runtime for annextube
- **git**: Version control
- **git-annex 8.0+**: Large file management
- **yt-dlp** (command-line): MUST be in PATH for git-annex --no-raw
  ```bash
  sudo pip install yt-dlp
  # Or download binary to /usr/local/bin
  ```

### Strongly Recommended

- **ffmpeg**: Video processing and best quality downloads
  ```bash
  sudo apt-get install ffmpeg  # Debian/Ubuntu
  brew install ffmpeg          # macOS
  ```

### Optional

- **YouTube Data API v3 key**: For API-based metadata (free from Google Cloud Console)
- **deno or node**: JavaScript runtime for modern YouTube features

## Development

```bash
# Clone repository
git clone https://github.com/con/annextube.git
cd annextube

# Install with development dependencies
uv pip install -e ".[devel]"

# Run tests
pytest

# Run linter
ruff check annextube/ tests/

# Run type checker
mypy annextube/
```

## License

MIT License - see [LICENSE](LICENSE) file

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) (TBD)

## Project Status

🚧 **Early Development** - This project is under active development. API may change.

Current phase: Implementing MVP (User Story 1 + 2)
