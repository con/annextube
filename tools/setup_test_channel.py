#!/usr/bin/env python3
"""Setup YouTube test channel for annextube testing.

This script creates a controlled test environment with:
- Videos under different licenses (standard YouTube and Creative Commons)
- Multiple playlists
- Videos with captions, locations, comments
- Very short videos (1-5 seconds) for fast testing

Requirements:
    pip install google-api-python-client google-auth-oauthlib

Setup:
    1. Create Google Cloud project and enable YouTube Data API v3
    2. Create OAuth 2.0 credentials (Desktop app)
    3. Download client_secrets.json to this directory
    4. Run: python setup_test_channel.py

Usage:
    # Generate test videos only
    python setup_test_channel.py --generate-videos

    # Upload everything (videos + playlists + metadata)
    python setup_test_channel.py --upload-all

    # Just create playlists (videos must already be uploaded)
    python setup_test_channel.py --create-playlists

    # Add comments to existing videos
    python setup_test_channel.py --add-comments

Quota Usage:
    - Upload video: 1600 units each
    - Update metadata: 50 units each
    - Create playlist: 50 units each
    - Add to playlist: 50 units each
    - Total for 12 videos + 5 playlists: ~21,000 units (~$21 or 2 days free tier)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("ERROR: Required libraries not installed")
    print("Install with: pip install google-api-python-client google-auth-oauthlib")
    sys.exit(1)

# YouTube API scopes
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # For playlists and comments
]

# Test video definitions
TEST_VIDEOS = [
    # Standard License Videos
    {
        "filename": "test-video-standard-01.mp4",
        "title": "Test Video - Standard License 1",
        "description": "Test video with standard YouTube license. 1 second, solid red.",
        "tags": ["annextube", "test", "standard-license", "short"],
        "duration": 1,
        "color": "red",
        "license": "youtube",  # Standard license
        "privacy": "public",
    },
    {
        "filename": "test-video-standard-02.mp4",
        "title": "Test Video - Standard License 2",
        "description": "Test video with standard YouTube license. 2 seconds, solid green.",
        "tags": ["annextube", "test", "standard-license", "short"],
        "duration": 2,
        "color": "green",
        "license": "youtube",
        "privacy": "public",
    },
    {
        "filename": "test-video-standard-03.mp4",
        "title": "Test Video - Standard License 3",
        "description": "Test video with standard YouTube license. 3 seconds, solid blue.",
        "tags": ["annextube", "test", "standard-license", "short"],
        "duration": 3,
        "color": "blue",
        "license": "youtube",
        "privacy": "public",
    },
    # Creative Commons Videos
    {
        "filename": "test-video-cc-01.mp4",
        "title": "Test Video - Creative Commons 1",
        "description": "Test video with Creative Commons license. 1 second, solid yellow.\n\nLicense: CC BY 3.0",
        "tags": ["annextube", "test", "creative-commons", "cc-by", "short"],
        "duration": 1,
        "color": "yellow",
        "license": "creativeCommon",  # CC license
        "privacy": "public",
    },
    {
        "filename": "test-video-cc-02.mp4",
        "title": "Test Video - Creative Commons 2",
        "description": "Test video with Creative Commons license. 2 seconds, solid magenta.\n\nLicense: CC BY 3.0",
        "tags": ["annextube", "test", "creative-commons", "cc-by", "short"],
        "duration": 2,
        "color": "magenta",
        "license": "creativeCommon",
        "privacy": "public",
    },
    {
        "filename": "test-video-cc-03.mp4",
        "title": "Test Video - Creative Commons 3",
        "description": "Test video with Creative Commons license. 3 seconds, solid cyan.\n\nLicense: CC BY 3.0",
        "tags": ["annextube", "test", "creative-commons", "cc-by", "short"],
        "duration": 3,
        "color": "cyan",
        "license": "creativeCommon",
        "privacy": "public",
    },
    # Videos with Captions
    {
        "filename": "test-video-captions-en.mp4",
        "title": "Test Video - With English Captions",
        "description": "Test video with English captions. 5 seconds, white background with text.",
        "tags": ["annextube", "test", "captions", "subtitles"],
        "duration": 5,
        "color": "white",
        "text_overlay": "Test Video\\nWith Captions",
        "license": "youtube",
        "privacy": "public",
        "captions": ["en"],  # Will upload English captions
    },
    {
        "filename": "test-video-captions-multi.mp4",
        "title": "Test Video - Multi-language Captions",
        "description": "Test video with captions in multiple languages (EN, ES, DE). 5 seconds.",
        "tags": ["annextube", "test", "captions", "multilingual"],
        "duration": 5,
        "color": "gray",
        "text_overlay": "Multilingual\\nCaptions",
        "license": "creativeCommon",
        "privacy": "public",
        "captions": ["en", "es", "de"],
    },
    # Videos with Location Metadata
    {
        "filename": "test-video-location-nyc.mp4",
        "title": "Test Video - Recorded in New York City",
        "description": "Test video with GPS location metadata. Recorded in NYC.\n\nLocation: New York City, USA",
        "tags": ["annextube", "test", "location", "gps", "nyc"],
        "duration": 3,
        "color": "navy",
        "license": "youtube",
        "privacy": "public",
        "location": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "description": "New York City, USA",
        },
    },
    {
        "filename": "test-video-location-london.mp4",
        "title": "Test Video - Recorded in London",
        "description": "Test video with GPS location metadata. Recorded in London.\n\nLocation: London, UK",
        "tags": ["annextube", "test", "location", "gps", "london"],
        "duration": 3,
        "color": "maroon",
        "license": "creativeCommon",
        "privacy": "public",
        "location": {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "description": "London, UK",
        },
    },
    # Videos for Comment Testing
    {
        "filename": "test-video-with-comments-01.mp4",
        "title": "Test Video - With Comments 1",
        "description": "Test video for comment fetching. Will have multiple comments.",
        "tags": ["annextube", "test", "comments"],
        "duration": 2,
        "color": "purple",
        "license": "youtube",
        "privacy": "public",
        "add_comments": True,
    },
    {
        "filename": "test-video-with-comments-02.mp4",
        "title": "Test Video - With Comments 2",
        "description": "Test video for comment threading. Will have comments with replies.",
        "tags": ["annextube", "test", "comments", "replies"],
        "duration": 2,
        "color": "teal",
        "license": "creativeCommon",
        "privacy": "public",
        "add_comments": True,
    },
]

# Playlist definitions
TEST_PLAYLISTS = [
    {
        "title": "All Standard License Videos",
        "description": "All test videos with standard YouTube license",
        "privacy": "public",
        "video_filter": lambda v: v["license"] == "youtube",
    },
    {
        "title": "All Creative Commons Videos",
        "description": "All test videos with Creative Commons license (CC BY 3.0)",
        "privacy": "public",
        "video_filter": lambda v: v["license"] == "creativeCommon",
    },
    {
        "title": "Mixed License Videos",
        "description": "Test videos with both standard and CC licenses",
        "privacy": "public",
        "video_filter": lambda v: True,  # All videos
    },
    {
        "title": "Videos with Captions",
        "description": "Test videos that include captions/subtitles",
        "privacy": "public",
        "video_filter": lambda v: "captions" in v,
    },
    {
        "title": "Videos with Location Metadata",
        "description": "Test videos with GPS recording location data",
        "privacy": "public",
        "video_filter": lambda v: "location" in v,
    },
]

# Test comments to add
TEST_COMMENTS = [
    "Great test video! Very helpful for testing.",
    "This is a test comment for annextube testing.",
    "Testing comment fetching functionality.",
    "Another test comment with some emoji 🎥📹",
    "This comment has a reply",  # Will add reply to this one
]


class TestChannelSetup:
    """Setup YouTube test channel for annextube."""

    def __init__(self, output_dir: Path = Path("test_videos")):
        """Initialize test channel setup.

        Args:
            output_dir: Directory to store generated videos and metadata
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

        self.youtube = None
        self.uploaded_videos = {}  # filename -> video_id mapping
        self.created_playlists = {}  # title -> playlist_id mapping

    def authenticate(self) -> None:
        """Authenticate with YouTube API using OAuth 2.0."""
        creds = None
        token_file = Path("token.json")
        client_secrets = Path("client_secrets.json")

        if not client_secrets.exists():
            print("ERROR: client_secrets.json not found")
            print("Download OAuth 2.0 credentials from Google Cloud Console")
            print("See: https://developers.google.com/youtube/v3/guides/auth/installed-apps")
            sys.exit(1)

        # Load existing credentials
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                print("Starting OAuth authentication flow...")
                print()
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(client_secrets), SCOPES
                )
                # Use out-of-band (OOB) redirect URI for CLI apps
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                # Generate authorization URL
                auth_url, _ = flow.authorization_url(prompt='consent')
                print("Please visit this URL to authorize:")
                print(auth_url)
                print()
                print("After authorizing, Google will display an authorization code.")
                print("Copy the code and paste it below.")
                print()
                code = input("Enter the authorization code: ").strip()
                flow.fetch_token(code=code)
                creds = flow.credentials

            # Save credentials
            token_file.write_text(creds.to_json())
            print("Credentials saved to token.json")

        # Build YouTube API client
        self.youtube = build("youtube", "v3", credentials=creds)
        print("✓ Authenticated with YouTube API")

    def generate_video(self, video_def: dict) -> Path:
        """Generate test video using ffmpeg.

        Args:
            video_def: Video definition dictionary

        Returns:
            Path to generated video file
        """
        output_path = self.output_dir / video_def["filename"]

        if output_path.exists():
            print(f"  Video already exists: {output_path}")
            return output_path

        # Base ffmpeg command for solid color
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"color=c={video_def['color']}:s=1280x720:d={video_def['duration']}",
        ]

        # Add text overlay if specified
        if "text_overlay" in video_def:
            text = video_def["text_overlay"].replace("\\n", "\n")
            cmd.extend([
                "-vf",
                f"drawtext=text='{text}':fontsize=48:fontcolor=black:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=white@0.5:boxborderw=10"
            ])

        # Output settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-y",  # Overwrite output
            str(output_path),
        ])

        print(f"  Generating {video_def['filename']} ({video_def['duration']}s, {video_def['color']})...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"ERROR: ffmpeg failed: {result.stderr}")
            sys.exit(1)

        print(f"  ✓ Generated {output_path} ({output_path.stat().st_size // 1024} KB)")
        return output_path

    def generate_caption_file(self, video_def: dict, language: str) -> Path:
        """Generate VTT caption file.

        Args:
            video_def: Video definition
            language: Language code (en, es, de, etc.)

        Returns:
            Path to caption file
        """
        caption_path = self.output_dir / f"{video_def['filename']}.{language}.vtt"

        if caption_path.exists():
            return caption_path

        # Caption text by language
        captions = {
            "en": [
                "This is a test video",
                "For annextube testing",
                "With English captions",
            ],
            "es": [
                "Este es un video de prueba",
                "Para pruebas de annextube",
                "Con subtítulos en español",
            ],
            "de": [
                "Dies ist ein Testvideo",
                "Für annextube-Tests",
                "Mit deutschen Untertiteln",
            ],
        }

        lines = captions.get(language, captions["en"])

        # Generate VTT content
        vtt_content = "WEBVTT\n\n"
        time_per_line = video_def["duration"] / len(lines)

        for i, line in enumerate(lines):
            start = i * time_per_line
            end = (i + 1) * time_per_line
            vtt_content += f"{format_time(start)} --> {format_time(end)}\n{line}\n\n"

        caption_path.write_text(vtt_content)
        print(f"  ✓ Generated caption: {caption_path.name}")
        return caption_path

    def upload_video(self, video_def: dict) -> str:
        """Upload video to YouTube.

        Args:
            video_def: Video definition

        Returns:
            Video ID
        """
        video_path = self.output_dir / video_def["filename"]

        if not video_path.exists():
            print(f"ERROR: Video not found: {video_path}")
            sys.exit(1)

        print(f"  Uploading {video_def['filename']}...")

        # Prepare video metadata
        body = {
            "snippet": {
                "title": video_def["title"],
                "description": video_def["description"],
                "tags": video_def["tags"],
                "categoryId": "28",  # Science & Technology
            },
            "status": {
                "privacyStatus": video_def["privacy"],
                "license": video_def["license"],
                "embeddable": True,
                "publicStatsViewable": True,
            },
        }

        # Add recording details if location specified
        if "location" in video_def:
            body["recordingDetails"] = {
                "location": {
                    "latitude": video_def["location"]["latitude"],
                    "longitude": video_def["location"]["longitude"],
                },
                "locationDescription": video_def["location"]["description"],
            }

        # Upload video
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)

        try:
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
            )

            response = request.execute()
            video_id = response["id"]

            print(f"  ✓ Uploaded: {video_id} (License: {video_def['license']})")
            self.uploaded_videos[video_def["filename"]] = video_id

            # Upload captions if specified
            if "captions" in video_def:
                for lang in video_def["captions"]:
                    self.upload_caption(video_id, video_def, lang)

            return video_id

        except HttpError as e:
            print(f"ERROR: Upload failed: {e}")
            sys.exit(1)

    def upload_caption(self, video_id: str, video_def: dict, language: str) -> None:
        """Upload caption file to video.

        Args:
            video_id: YouTube video ID
            video_def: Video definition
            language: Language code
        """
        caption_path = self.output_dir / f"{video_def['filename']}.{language}.vtt"

        if not caption_path.exists():
            self.generate_caption_file(video_def, language)

        print(f"    Uploading {language} captions...")

        body = {
            "snippet": {
                "videoId": video_id,
                "language": language,
                "name": f"{language.upper()} captions",
            },
        }

        media = MediaFileUpload(str(caption_path), mimetype="text/vtt")

        try:
            self.youtube.captions().insert(
                part="snippet",
                body=body,
                media_body=media,
            ).execute()

            print(f"    ✓ Caption uploaded: {language}")

        except HttpError as e:
            print(f"    WARNING: Caption upload failed: {e}")

    def create_playlist(self, playlist_def: dict) -> str:
        """Create playlist on YouTube.

        Args:
            playlist_def: Playlist definition

        Returns:
            Playlist ID
        """
        print(f"  Creating playlist: {playlist_def['title']}...")

        body = {
            "snippet": {
                "title": playlist_def["title"],
                "description": playlist_def["description"],
            },
            "status": {
                "privacyStatus": playlist_def["privacy"],
            },
        }

        try:
            response = self.youtube.playlists().insert(
                part="snippet,status",
                body=body,
            ).execute()

            playlist_id = response["id"]
            print(f"  ✓ Created playlist: {playlist_id}")
            self.created_playlists[playlist_def["title"]] = playlist_id

            return playlist_id

        except HttpError as e:
            print(f"ERROR: Playlist creation failed: {e}")
            sys.exit(1)

    def add_to_playlist(self, playlist_id: str, video_id: str) -> None:
        """Add video to playlist.

        Args:
            playlist_id: YouTube playlist ID
            video_id: YouTube video ID
        """
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            },
        }

        try:
            self.youtube.playlistItems().insert(
                part="snippet",
                body=body,
            ).execute()

        except HttpError as e:
            print(f"    WARNING: Failed to add video to playlist: {e}")

    def add_comment(self, video_id: str, text: str, parent_id: str | None = None) -> str:
        """Add comment to video.

        Args:
            video_id: YouTube video ID
            text: Comment text
            parent_id: Parent comment ID for replies

        Returns:
            Comment ID
        """
        if parent_id:
            # Reply to existing comment
            body = {
                "snippet": {
                    "parentId": parent_id,
                    "textOriginal": text,
                },
            }
            response = self.youtube.comments().insert(
                part="snippet",
                body=body,
            ).execute()
        else:
            # Top-level comment
            body = {
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": text,
                        },
                    },
                },
            }
            response = self.youtube.commentThreads().insert(
                part="snippet",
                body=body,
            ).execute()

        return response["id"]

    def save_metadata(self) -> None:
        """Save uploaded video IDs and playlist IDs to JSON file."""
        metadata = {
            "videos": self.uploaded_videos,
            "playlists": self.created_playlists,
        }

        metadata_path = self.output_dir / "test_channel_metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        print(f"\n✓ Metadata saved to {metadata_path}")
        print("\nAdd this to tests/conftest.py:")
        print("```python")
        print(f"TEST_CHANNEL_VIDEOS = {json.dumps(self.uploaded_videos, indent=4)}")
        print(f"\nTEST_CHANNEL_PLAYLISTS = {json.dumps(self.created_playlists, indent=4)}")
        print("```")


def format_time(seconds: float) -> str:
    """Format seconds as VTT timestamp (HH:MM:SS.mmm).

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Setup YouTube test channel for annextube")
    parser.add_argument("--generate-videos", action="store_true", help="Generate test videos only")
    parser.add_argument("--upload-all", action="store_true", help="Upload videos and create playlists")
    parser.add_argument("--create-playlists", action="store_true", help="Create playlists only")
    parser.add_argument("--add-comments", action="store_true", help="Add test comments")
    parser.add_argument("--output-dir", type=Path, default=Path("test_videos"), help="Output directory")

    args = parser.parse_args()

    if not any([args.generate_videos, args.upload_all, args.create_playlists, args.add_comments]):
        parser.print_help()
        sys.exit(1)

    setup = TestChannelSetup(output_dir=args.output_dir)

    # Generate videos
    if args.generate_videos or args.upload_all:
        print("\n=== Generating Test Videos ===\n")

        # Check ffmpeg availability
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("ERROR: ffmpeg not found. Install with: apt install ffmpeg")
            sys.exit(1)

        for video_def in TEST_VIDEOS:
            setup.generate_video(video_def)

            # Generate captions if needed
            if "captions" in video_def:
                for lang in video_def["captions"]:
                    setup.generate_caption_file(video_def, lang)

        print(f"\n✓ Generated {len(TEST_VIDEOS)} test videos")

    # Upload videos
    if args.upload_all:
        print("\n=== Uploading Videos to YouTube ===\n")
        setup.authenticate()

        for video_def in TEST_VIDEOS:
            setup.upload_video(video_def)

        print(f"\n✓ Uploaded {len(setup.uploaded_videos)} videos")

    # Create playlists
    if args.create_playlists or args.upload_all:
        print("\n=== Creating Playlists ===\n")

        if not setup.youtube:
            setup.authenticate()

        # Load uploaded videos if not in memory
        if not setup.uploaded_videos and (args.output_dir / "test_channel_metadata.json").exists():
            metadata = json.loads((args.output_dir / "test_channel_metadata.json").read_text())
            setup.uploaded_videos = metadata["videos"]

        for playlist_def in TEST_PLAYLISTS:
            playlist_id = setup.create_playlist(playlist_def)

            # Add matching videos to playlist
            for video_def in TEST_VIDEOS:
                if playlist_def["video_filter"](video_def):
                    filename = video_def["filename"]
                    if filename in setup.uploaded_videos:
                        video_id = setup.uploaded_videos[filename]
                        setup.add_to_playlist(playlist_id, video_id)
                        print(f"    Added {video_def['title']}")

        print(f"\n✓ Created {len(setup.created_playlists)} playlists")

    # Add comments
    if args.add_comments:
        print("\n=== Adding Test Comments ===\n")

        if not setup.youtube:
            setup.authenticate()

        # Load uploaded videos
        if not setup.uploaded_videos and (args.output_dir / "test_channel_metadata.json").exists():
            metadata = json.loads((args.output_dir / "test_channel_metadata.json").read_text())
            setup.uploaded_videos = metadata["videos"]

        for video_def in TEST_VIDEOS:
            if video_def.get("add_comments"):
                filename = video_def["filename"]
                video_id = setup.uploaded_videos.get(filename)

                if not video_id:
                    print(f"  WARNING: Video not found: {filename}")
                    continue

                print(f"  Adding comments to {video_def['title']}...")

                # Add top-level comments
                parent_id = None
                for i, comment_text in enumerate(TEST_COMMENTS):
                    comment_id = setup.add_comment(video_id, comment_text)
                    print(f"    ✓ Added comment {i+1}")

                    # Add reply to first comment
                    if i == 0:
                        parent_id = comment_id

                # Add reply
                if parent_id:
                    setup.add_comment(video_id, "This is a reply to the first comment", parent_id=parent_id)
                    print("    ✓ Added reply")

    # Save metadata
    if args.upload_all or args.create_playlists:
        setup.save_metadata()

    print("\n✓ Test channel setup complete!")


if __name__ == "__main__":
    main()
