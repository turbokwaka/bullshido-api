import os
import sys
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

from fastapi import HTTPException

from config import settings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import User, Video
from schemas import (
    VideoCreateRequest,
    VoicePreset,
    SubtitlePosition,
    VideoStatus,
    VideoUpdateStatus,
)
from services.videos_service import (
    create_video_generation_task_service,
    update_video_status_service,
)


# tests for create_video_generation_task_service
@pytest.mark.asyncio
async def test_create_video_task_success(monkeypatch):
    mock_session = MagicMock()

    async def fake_refresh(obj):
        obj.id = 42
        try:
            obj.voice = VoicePreset(obj.voice)
        except Exception:
            obj.voice = SimpleNamespace(value=obj.voice)
        try:
            obj.subtitle_position = SubtitlePosition(obj.subtitle_position)
        except Exception:
            obj.subtitle_position = SimpleNamespace(value=obj.subtitle_position)

    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=fake_refresh)
    mock_session.add = MagicMock()

    mock_redis = AsyncMock()

    async def mock_get_redis():
        return mock_redis

    monkeypatch.setattr("services.videos_service.get_redis", mock_get_redis)

    user = User(id=1, username="test_user", email="t@t.com", hashed_password="pw")
    request_data = VideoCreateRequest(
        text="Test video generation",
        voice=VoicePreset.af_heart,
        subtitle_style_id=1,
        subtitle_position=SubtitlePosition.top,
    )

    result = await create_video_generation_task_service(
        request_data, user, mock_session
    )

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()

    added_video = mock_session.add.call_args[0][0]
    assert isinstance(added_video, Video)
    assert added_video.user_id == user.id
    assert added_video.voice == "af_heart"

    mock_redis.enqueue_job.assert_awaited_once_with(
        "generate_video",
        video_id=42,
        text="Test video generation",
        voice="af_heart",
        subtitle_style_id=1,
        subtitle_position="top",
    )

    assert result.id == "42"
    assert result.status == VideoStatus.queued


# test if update status works correctly
@pytest.mark.asyncio
async def test_update_video_status_success(monkeypatch):
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = MagicMock()

    video_obj = Video(
        id=10,
        status=VideoStatus.queued,
        user_id=5,
        text="original text",
        created_at=datetime.now(timezone.utc),
    )
    user_obj = User(id=5, username="test_user", email="t@t.com", hashed_password="x")

    res_video = MagicMock()
    res_video.first.return_value = video_obj

    res_user = MagicMock()
    res_user.first.return_value = user_obj

    mock_session.exec = AsyncMock(side_effect=[res_video, res_user])

    update_payload = VideoUpdateStatus(
        status=VideoStatus.completed,
        video_url="http://minio/vid.mp4",
    )

    monkeypatch.setattr(
        "config.settings.WORKER_SECRET_TOKEN", settings.WORKER_SECRET_TOKEN
    )

    result = await update_video_status_service(
        video_id="10",
        update_data=update_payload,
        x_worker_token=settings.WORKER_SECRET_TOKEN,
        session=mock_session,
    )

    assert result.status == VideoStatus.completed
    assert result.video_url == "http://minio/vid.mp4"
    assert result.author_username == "test_user"

    mock_session.add.assert_called_once_with(video_obj)
    mock_session.commit.assert_awaited_once()


# test if invalid token raises exception
@pytest.mark.asyncio
async def test_update_video_status_invalid_token(monkeypatch):
    mock_session = AsyncMock()

    monkeypatch.setattr("config.settings.WORKER_SECRET_TOKEN", "real_token")

    update_payload = VideoUpdateStatus(status=VideoStatus.failed)

    with pytest.raises(HTTPException) as exc_info:
        await update_video_status_service(
            video_id="10",
            update_data=update_payload,
            x_worker_token="WRONG_TOKEN",
            session=mock_session,
        )

    assert exc_info.value.status_code == 403
    assert "Not authorized worker" in exc_info.value.detail

    mock_session.commit.assert_not_awaited()


# test if video not found raises exception
@pytest.mark.asyncio
async def test_update_video_status_not_found(monkeypatch):
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.exec = AsyncMock(return_value=mock_result)

    valid_token = "secret_token_for_worker_communication"
    monkeypatch.setattr("config.settings.WORKER_SECRET_TOKEN", valid_token)

    update_payload = VideoUpdateStatus(status=VideoStatus.failed)

    with pytest.raises(HTTPException) as exc_info:
        await update_video_status_service(
            video_id="999",
            update_data=update_payload,
            x_worker_token=valid_token,
            session=mock_session,
        )

    assert exc_info.value.status_code == 404
    assert "Video not found" in exc_info.value.detail

    mock_session.commit.assert_not_awaited()
