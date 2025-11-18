import uuid
from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status, Header

from config import settings
from db import VIDEOS_DB
from schemas import (
    VideoResponse,
    VideoCreateRequest,
    VideoStatus,
)
from security import (
    get_current_user,
)

videos_router = APIRouter(prefix="/videos", tags=["Videos"])


@videos_router.post(
    "/generate", response_model=VideoResponse, status_code=status.HTTP_201_CREATED
)
async def create_video_generation_task(
    video_request: VideoCreateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    video_id = str(uuid.uuid4())

    new_video = {
        "id": video_id,
        "author_username": current_user["username"],
        "text": video_request.text,
        "voice": video_request.voice,
        "subtitle_style_id": video_request.subtitle_style_id,
        "subtitle_position": video_request.subtitle_position,
        "status": VideoStatus.queued,
        "video_url": None,
        "created_at": datetime.now(timezone.utc),
    }

    VIDEOS_DB[video_id] = new_video
    return new_video


@videos_router.get("/gallery", response_model=List[VideoResponse])
async def get_video_gallery(
    current_user: Annotated[dict, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 10,
):
    completed_videos = [
        v for v in VIDEOS_DB.values() if v["status"] == VideoStatus.completed
    ]
    return completed_videos[skip : skip + limit]


@videos_router.get("/history", response_model=List[VideoResponse])
async def get_my_videos_history(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    username = current_user["username"]

    my_videos = [v for v in VIDEOS_DB.values() if v["author_username"] == username]

    my_videos.sort(key=lambda x: x["created_at"], reverse=True)

    return my_videos


@videos_router.get("/{video_id}", response_model=VideoResponse)
async def get_video_status(
    video_id: str, current_user: Annotated[dict, Depends(get_current_user)]
):
    video = VIDEOS_DB.get(video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Video not found")

    return video


@videos_router.patch("/{video_id}/complete_simulation")
async def worker_complete_task(
    video_id: str,
    video_url: str,
    thumbnail_url: str,
    x_worker_token: Annotated[str, Header()],
):
    if x_worker_token != settings.WORKER_SECRET_TOKEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized worker")

    video = VIDEOS_DB.get(video_id)
    if not video:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task not found")

    video["status"] = VideoStatus.completed
    video["video_url"] = video_url
    video["thumbnail_url"] = thumbnail_url
    return {"message": "Доббі хоче бути вільним.", "video": video}
