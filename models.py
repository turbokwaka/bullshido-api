from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import sqlalchemy as sa

from schemas import VoicePreset, SubtitlePosition, VideoStatus


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    avatar_url: Optional[str] = Field(default="https://ibb.co/s9DkGLf5")

    videos: List["Video"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Video(SQLModel, table=True):
    __tablename__ = "videos"

    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="users.id", index=True)

    text: str = Field(max_length=500)
    voice: VoicePreset
    subtitle_style_id: int
    subtitle_position: SubtitlePosition

    status: VideoStatus = Field(default=VideoStatus.queued, index=True)
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    created_at: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )

    user: Optional["User"] = Relationship(back_populates="videos")
