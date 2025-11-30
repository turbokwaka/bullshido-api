from typing import Annotated, List

from fastapi import APIRouter, Depends, status, Query, Header
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from models import User
from schemas import (
    VideoResponse,
    VideoCreateRequest,
    VideoUpdateStatus,
)
from security import get_current_user
from services.videos_service import (
    create_video_generation_task_service,
    get_video_gallery_service,
    get_my_videos_history_service,
    get_video_status_service,
    update_video_status_service,
)

videos_router = APIRouter(prefix="/videos", tags=["Videos"])


@videos_router.post(
    "/generate", response_model=VideoResponse, status_code=status.HTTP_201_CREATED
)
async def create_video_generation_task(
    video_request: VideoCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await create_video_generation_task_service(
        video_request, current_user, session
    )


@videos_router.get(
    "/gallery",
    response_model=List[VideoResponse],
    dependencies=[Depends(get_current_user)],
)
async def get_video_gallery(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return await get_video_gallery_service(session, skip, limit)


@videos_router.get("/history", response_model=List[VideoResponse])
async def get_my_videos_history(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return await get_my_videos_history_service(current_user, session, skip, limit)


@videos_router.get("/{video_id}", response_model=VideoResponse)
async def get_video_status(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await get_video_status_service(video_id, current_user, session)


@videos_router.patch("/{video_id}/status", response_model=VideoResponse)
async def update_video_status(
    video_id: str,
    update_data: VideoUpdateStatus,
    x_worker_token: Annotated[str, Header()],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await update_video_status_service(
        video_id, update_data, x_worker_token, session
    )
