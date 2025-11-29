from datetime import datetime, timezone
from typing import List

from arq.connections import ArqRedis
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import desc

from config import settings
from db import get_redis
from models import Video, User
from schemas import VideoResponse, VideoCreateRequest, VideoStatus, VideoUpdateStatus


async def create_video_generation_task_service(
    video_request: VideoCreateRequest,
    current_user: User,
    session: AsyncSession,
) -> VideoResponse:
    new_video = Video(
        user_id=current_user.id,
        text=video_request.text,
        voice=video_request.voice.value,
        subtitle_style_id=video_request.subtitle_style_id,
        subtitle_position=video_request.subtitle_position.value,
        status=VideoStatus.queued,
        created_at=datetime.now(timezone.utc),
    )
    session.add(new_video)
    await session.commit()
    await session.refresh(new_video)

    redis: ArqRedis = await get_redis()
    await redis.enqueue_job(
        "generate_video",
        video_id=new_video.id,
        text=new_video.text,
        voice=new_video.voice.value,
        subtitle_style_id=new_video.subtitle_style_id,
        subtitle_position=new_video.subtitle_position.value,
    )

    return VideoResponse(
        id=str(new_video.id),
        author_username=current_user.username,
        text=new_video.text,
        status=new_video.status,
        video_url=new_video.video_url,
        thumbnail_url=new_video.thumbnail_url,
        created_at=new_video.created_at,
    )


async def get_video_gallery_service(
    session: AsyncSession, skip: int = 0, limit: int = 10
) -> List[VideoResponse]:
    statement = (
        select(Video, User)
        .join(User)
        .where(col(Video.status) == VideoStatus.completed)
        .order_by(desc(col(Video.created_at)))
        .offset(skip)
        .limit(limit)
    )

    result = await session.exec(statement)
    rows = result.all()

    videos: List[VideoResponse] = []
    for video_obj, user_obj in rows:
        videos.append(
            VideoResponse(
                id=str(video_obj.id),
                author_username=user_obj.username,
                text=video_obj.text,
                status=video_obj.status,
                video_url=video_obj.video_url,
                thumbnail_url=video_obj.thumbnail_url,
                created_at=video_obj.created_at,
            )
        )

    return videos


async def get_my_videos_history_service(
    current_user: User, session: AsyncSession, skip: int = 0, limit: int = 10
) -> List[VideoResponse]:
    statement = (
        select(Video, User)
        .join(User)
        .where(col(Video.user_id) == current_user.id)
        .order_by(desc(col(Video.created_at)))
        .offset(skip)
        .limit(limit)
    )

    result = await session.exec(statement)
    rows = result.all()

    videos: List[VideoResponse] = []
    for video_obj, user_obj in rows:
        videos.append(
            VideoResponse(
                id=str(video_obj.id),
                author_username=user_obj.username,
                text=video_obj.text,
                status=video_obj.status,
                video_url=video_obj.video_url,
                thumbnail_url=video_obj.thumbnail_url,
                created_at=video_obj.created_at,
            )
        )

    return videos


async def get_video_status_service(
    video_id: str, current_user: User, session: AsyncSession
) -> VideoResponse:
    if not video_id.isdigit():
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Video not found")

    statement = select(Video, User).join(User).where(col(Video.id) == int(video_id))

    result = await session.exec(statement)
    row = result.first()

    if not row:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Video not found")

    video_obj, user_obj = row

    return VideoResponse(
        id=str(video_obj.id),
        author_username=user_obj.username,
        text=video_obj.text,
        status=video_obj.status,
        video_url=video_obj.video_url,
        thumbnail_url=video_obj.thumbnail_url,
        created_at=video_obj.created_at,
    )


async def update_video_status_service(
    video_id: str,
    update_data: VideoUpdateStatus,
    x_worker_token: str,
    session: AsyncSession,
) -> VideoResponse:
    from fastapi import HTTPException, status
    from sqlmodel import select, col

    if x_worker_token != settings.WORKER_SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized worker"
        )

    if not video_id.isdigit():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Video not found")

    statement = select(Video).where(col(Video.id) == int(video_id))
    result = await session.exec(statement)
    video_obj = result.first()

    if not video_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    video_obj.status = update_data.status

    if update_data.video_url:
        video_obj.video_url = update_data.video_url
    if update_data.thumbnail_url:
        video_obj.thumbnail_url = update_data.thumbnail_url

    session.add(video_obj)
    await session.commit()
    await session.refresh(video_obj)

    author_username = "unknown"
    if video_obj.user_id:
        user_stmt = select(User).where(col(User.id) == video_obj.user_id)
        user_res = await session.exec(user_stmt)
        user = user_res.first()
        if user:
            author_username = user.username

    return VideoResponse(
        id=str(video_obj.id),
        author_username=author_username,
        text=video_obj.text,
        status=video_obj.status,
        video_url=video_obj.video_url,
        thumbnail_url=video_obj.thumbnail_url,
        created_at=video_obj.created_at,
    )
