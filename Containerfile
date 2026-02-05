# Minimal annextube container with all dependencies
# Compatible with podman, docker, and singularity/apptainer
#
# Build:
#   podman build -t annextube:latest -f Containerfile .
#
# Run:
#   podman run -it --rm -v $PWD:/archive annextube:latest annextube --help
#
# For singularity/apptainer:
#   apptainer build annextube.sif docker-daemon://annextube:latest

FROM debian:bookworm-slim

LABEL org.opencontainers.image.title="annextube"
LABEL org.opencontainers.image.description="YouTube archival system using git-annex"
LABEL org.opencontainers.image.url="https://github.com/con/annextube"
LABEL org.opencontainers.image.licenses="MIT"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core requirements
    git \
    git-annex \
    python3 \
    python3-pip \
    python3-venv \
    ca-certificates \
    curl \
    # Optional but recommended
    ffmpeg \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Install deno (minimal JavaScript runtime for YouTube n-challenge solver)
# More lightweight than Node.js
RUN curl -fsSL https://deno.land/install.sh | sh \
    && mv /root/.deno/bin/deno /usr/local/bin/ \
    && rm -rf /root/.deno

# Install uv (fast Python package installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.cargo/bin/uv /usr/local/bin/ \
    && rm -rf /root/.cargo

# Install yt-dlp system-wide (required in PATH for git-annex --no-raw)
RUN pip3 install --no-cache-dir --break-system-packages yt-dlp

# Create app directory
WORKDIR /app

# Copy annextube source
COPY pyproject.toml README.md LICENSE ./
COPY annextube/ ./annextube/

# Install annextube using uv
RUN uv pip install --system --no-cache . \
    && uv cache clean

# Verify installations
RUN git --version \
    && git-annex version \
    && python3 --version \
    && yt-dlp --version \
    && deno --version \
    && annextube --version

# Set working directory to /archive for user data
WORKDIR /archive

# Default command shows help
ENTRYPOINT ["annextube"]
CMD ["--help"]

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV YOUTUBE_API_KEY=""

# Labels for runtime
LABEL org.opencontainers.image.version="0.1.0"
