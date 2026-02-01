#!/bin/bash
set -e

echo "==> Complete Cookie Test with Fixed Configuration"
echo

# Base directory
TEST_DIR="/home/yoh/proj/annextube/test-archives"
FAKE_HOME="$TEST_DIR/fake-home-demo"
MINICONDA_DIR="$TEST_DIR/miniconda3"
ARCHIVE_DIR="$FAKE_HOME/archive"

echo "Test directory: $TEST_DIR"
echo "Fake HOME: $FAKE_HOME"
echo "Miniconda: $MINICONDA_DIR"
echo "Archive: $ARCHIVE_DIR"
echo

# Step 1: Install miniconda if not exists
if [ ! -d "$MINICONDA_DIR" ]; then
    echo "==> Step 1: Installing Miniconda"
    cd "$TEST_DIR"
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda-installer.sh
    bash miniconda-installer.sh -b -p "$MINICONDA_DIR"
    rm miniconda-installer.sh
    echo "✓ Miniconda installed"
else
    echo "==> Step 1: Miniconda already installed"
fi
echo

# Step 2: Create deno environment
echo "==> Step 2: Setting up deno environment"
source "$MINICONDA_DIR/bin/activate"
if ! conda env list | grep -q "^deno "; then
    conda create -n deno -y --override-channels -c conda-forge deno python=3.11
    echo "✓ Created deno environment"
else
    echo "✓ Deno environment exists"
fi

conda activate deno
pip install -q yt-dlp
cd /home/yoh/proj/annextube
pip install -q -e .
echo "✓ Installed yt-dlp and annextube in deno environment"
echo

# Verify tools
echo "==> Verifying tools"
echo "Python: $(which python)"
echo "yt-dlp: $(which yt-dlp) version $(yt-dlp --version)"
echo "deno: $(which deno) version $(deno --version | head -n1)"
echo "annextube: $(which annextube)"
echo

# Step 3: Clean and setup fake HOME
echo "==> Step 3: Setting up fake HOME"
if [ -d "$FAKE_HOME" ]; then
    chmod -R u+w "$FAKE_HOME" 2>/dev/null || true
    rm -rf "$FAKE_HOME"
fi
mkdir -p "$FAKE_HOME"
echo "✓ Fake HOME created"
echo

# Export HOME for all subsequent commands
export HOME="$FAKE_HOME"
echo "HOME set to: $HOME"
echo

# Step 4: Create user config
echo "==> Step 4: Creating user config with cookies + EJS"
annextube init-user-config

cat >> "$FAKE_HOME/.config/annextube/config.toml" << 'EOF'

# Cookies for authenticated content
cookies_file = "/home/yoh/proj/annextube/.git/yt-cookies.txt"

# Enable EJS challenge solver (requires deno)
ytdlp_extra_opts = ["--remote-components", "ejs:github"]
EOF

echo "✓ User config created:"
echo "  - Cookies: /home/yoh/proj/annextube/.git/yt-cookies.txt"
echo "  - EJS solver enabled"
echo

# Step 5: Initialize archive
echo "==> Step 5: Initializing archive"
annextube init "$ARCHIVE_DIR" "https://www.youtube.com/@apopyk" --videos --limit 2
echo "✓ Archive initialized"
echo

# Step 6: Check git config
echo "==> Step 6: Checking git-annex configuration"
cd "$ARCHIVE_DIR"
echo "Git config annex.youtube-dl-options:"
git config annex.youtube-dl-options
echo

# Step 7: Run backup
echo "==> Step 7: Running backup"
cd "$ARCHIVE_DIR"
annextube backup --output-dir "$ARCHIVE_DIR"
echo

# Step 8: Test git-annex directly
echo "==> Step 8: Testing git-annex addurl directly"
cd "$ARCHIVE_DIR"
echo "Attempting to add YouTube video URL..."
git annex addurl 'https://www.youtube.com/watch?v=hBROP344w-0' \
    --file test-video-direct.mkv \
    --relaxed --fast --no-raw || {
    echo "✗ git annex addurl failed with exit code $?"
    echo "This is expected if YouTube requires special handling"
}
echo

# Step 9: Check results
echo "==> Step 9: Checking results"
cd "$ARCHIVE_DIR"

echo "Videos in videos.tsv:"
if [ -f videos/videos.tsv ]; then
    tail -n +2 videos/videos.tsv | cut -f2,3
else
    echo "  No videos.tsv found"
fi
echo

echo "Actual video files:"
find videos -name "*.mkv" -o -name "*.mp4" -o -name "*.webm" 2>/dev/null || echo "  (none)"
echo

echo "Caption files:"
find videos -name "*.vtt" 2>/dev/null | head -3 || echo "  (none)"
echo

echo "Comments files:"
find videos -name "comments.json" 2>/dev/null | head -3 || echo "  (none)"
echo

# Step 10: Generate web interface
echo "==> Step 10: Generating web interface"
annextube generate-web --output-dir "$ARCHIVE_DIR"
echo

echo "==> Test Complete!"
echo "Archive location: $ARCHIVE_DIR"
echo "To browse: cd $ARCHIVE_DIR/web && python3 -m http.server 8765"
