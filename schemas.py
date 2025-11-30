from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class VoicePreset(str, Enum):
    af_heart = "af_heart"
    af_bella = "af_bella"
    af_nicole = "af_nicole"


class SubtitlePosition(str, Enum):
    top = "top"
    center = "center"
    bottom = "bottom"


class VideoStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    email: EmailStr
    avatar_url: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(min_length=3, max_length=30)


class User(UserBase):
    pass


class UserUpdate(BaseModel):
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=3, max_length=30)


class UserPasswordConfirm(BaseModel):
    password: str


class VideoCreateRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=500)
    voice: VoicePreset
    subtitle_style_id: int = Field(ge=1, le=10)
    subtitle_position: SubtitlePosition


class VideoResponse(BaseModel):
    id: str
    author_username: str
    text: str
    status: VideoStatus
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: datetime


class VideoUpdateStatus(BaseModel):
    status: VideoStatus
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
