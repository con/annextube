"""Video entity model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Video:
    """Represents a YouTube video with all associated metadata."""

    # === Required fields (no defaults) ===

    # Core identification
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_name: str
    published_at: datetime
    source_url: str
    fetched_at: datetime

    # Media details
    duration: int  # seconds
    thumbnail_url: str

    # Engagement metrics
    view_count: int
    like_count: int
    comment_count: int

    # Status and availability
    privacy_status: str  # 'public', 'unlisted', 'private'
    availability: str  # 'public', 'private', 'deleted', 'unavailable'
    download_status: str  # 'not_downloaded', 'tracked', 'downloaded', 'failed'

    # Content classification
    tags: list[str]
    categories: list[str]
    captions_available: list[str]
    has_auto_captions: bool

    # License (required but may have legacy 'standard' value)
    license: str  # 'youtube', 'creativeCommon', or 'standard' (legacy)

    # === Optional fields (with defaults) ===

    # Media details (optional)
    language: str | None = None
    file_path: str | None = None
    file_size: int | None = None

    # License and usage rights (YouTube API enhanced)
    licensed_content: bool | None = None  # contentDetails.licensedContent
    embeddable: bool | None = None  # status.embeddable
    made_for_kids: bool | None = None  # status.madeForKids

    # Recording metadata (YouTube API enhanced)
    recording_date: datetime | None = None  # when actually recorded
    recording_location: dict | None = None  # {latitude, longitude, altitude}
    location_description: str | None = None  # human-readable location

    # Technical details (YouTube API enhanced)
    definition: str | None = None  # 'hd' or 'sd'
    dimension: str | None = None  # '2d' or '3d'
    projection: str | None = None  # 'rectangular' or '360'

    # Geographic restrictions (YouTube API enhanced)
    region_restriction: dict | None = None  # {allowed: [...], blocked: [...]}
    content_rating: dict | None = None  # age ratings (mpaa, tvpg, bbfc, etc.)

    # Topic classification (YouTube API enhanced)
    topic_categories: list[str] | None = None  # Wikipedia topic URLs

    # Related resources (from extra_metadata.json, merged at export)
    related_resources: list[dict] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = {
            # Core identification
            "video_id": self.video_id,
            "title": self.title,
            "description": self.description,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "published_at": self.published_at.isoformat(),
            "source_url": self.source_url,
            "fetched_at": self.fetched_at.isoformat(),
            # Media details
            "duration": self.duration,
            "thumbnail_url": self.thumbnail_url,
            "language": self.language,
            # Engagement metrics
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            # Status and availability
            "privacy_status": self.privacy_status,
            "availability": self.availability,
            "download_status": self.download_status,
            "file_path": self.file_path,
            "file_size": self.file_size,
            # Content classification
            "tags": self.tags,
            "categories": self.categories,
            "captions_available": self.captions_available,
            "has_auto_captions": self.has_auto_captions,
            # License and usage rights
            "license": self.license,
            "licensed_content": self.licensed_content,
            "embeddable": self.embeddable,
            "made_for_kids": self.made_for_kids,
            # Recording metadata
            "recording_date": (
                self.recording_date.isoformat() if self.recording_date else None
            ),
            "recording_location": self.recording_location,
            "location_description": self.location_description,
            # Technical details
            "definition": self.definition,
            "dimension": self.dimension,
            "projection": self.projection,
            # Geographic restrictions
            "region_restriction": self.region_restriction,
            "content_rating": self.content_rating,
            # Topic classification
            "topic_categories": self.topic_categories,
            # Related resources
            "related_resources": self.related_resources,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Video":
        """Create from dictionary (loaded from JSON).

        Uses .get() for optional fields to ensure backward compatibility
        with existing metadata.json files.
        """
        # Parse recording_date if present
        recording_date = None
        if data.get("recording_date"):
            recording_date = datetime.fromisoformat(data["recording_date"])

        return cls(
            # Core identification
            video_id=data["video_id"],
            title=data["title"],
            description=data["description"],
            channel_id=data["channel_id"],
            channel_name=data["channel_name"],
            published_at=datetime.fromisoformat(data["published_at"]),
            source_url=data["source_url"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            # Media details
            duration=data["duration"],
            thumbnail_url=data["thumbnail_url"],
            language=data.get("language"),
            # Engagement metrics
            view_count=data["view_count"],
            like_count=data["like_count"],
            comment_count=data["comment_count"],
            # Status and availability
            privacy_status=data["privacy_status"],
            availability=data["availability"],
            download_status=data["download_status"],
            file_path=data.get("file_path"),
            file_size=data.get("file_size"),
            # Content classification
            tags=data["tags"],
            categories=data["categories"],
            captions_available=data["captions_available"],
            has_auto_captions=data["has_auto_captions"],
            # License and usage rights
            license=data["license"],
            licensed_content=data.get("licensed_content"),
            embeddable=data.get("embeddable"),
            made_for_kids=data.get("made_for_kids"),
            # Recording metadata
            recording_date=recording_date,
            recording_location=data.get("recording_location"),
            location_description=data.get("location_description"),
            # Technical details
            definition=data.get("definition"),
            dimension=data.get("dimension"),
            projection=data.get("projection"),
            # Geographic restrictions
            region_restriction=data.get("region_restriction"),
            content_rating=data.get("content_rating"),
            # Topic classification
            topic_categories=data.get("topic_categories"),
            # Related resources
            related_resources=data.get("related_resources"),
        )
