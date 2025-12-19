import os
import sys
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

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
    get_video_gallery_service,
    get_my_videos_history_service,
    get_video_status_service,
)


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


@pytest.mark.asyncio
async def test_get_video_gallery_success():
    mock_session = MagicMock()

    video1 = Video(
        id=1,
        user_id=1,
        text="Video 1",
        status=VideoStatus.completed,
        video_url="http://example.com/1.mp4",
        created_at=datetime.now(timezone.utc),
    )
    user1 = User(id=1, username="user1", email="u1@test.com", hashed_password="hash")

    video2 = Video(
        id=2,
        user_id=2,
        text="Video 2",
        status=VideoStatus.completed,
        video_url="http://example.com/2.mp4",
        created_at=datetime.now(timezone.utc),
    )
    user2 = User(id=2, username="user2", email="u2@test.com", hashed_password="hash")

    mock_result = MagicMock()
    mock_result.all.return_value = [(video1, user1), (video2, user2)]
    mock_session.exec = AsyncMock(return_value=mock_result)

    result = await get_video_gallery_service(mock_session, skip=0, limit=10)

    assert len(result) == 2
    assert result[0].id == "1"
    assert result[0].author_username == "user1"
    assert result[1].id == "2"
    assert result[1].author_username == "user2"


@pytest.mark.asyncio
async def test_get_video_gallery_empty():
    mock_session = MagicMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.exec = AsyncMock(return_value=mock_result)

    result = await get_video_gallery_service(mock_session, skip=0, limit=10)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_video_gallery_pagination():
    mock_session = MagicMock()

    video1 = Video(
        id=1,
        user_id=1,
        text="Video 1",
        status=VideoStatus.completed,
        created_at=datetime.now(timezone.utc),
    )
    user1 = User(id=1, username="user1", email="u1@test.com", hashed_password="hash")

    mock_result = MagicMock()
    mock_result.all.return_value = [(video1, user1)]
    mock_session.exec = AsyncMock(return_value=mock_result)

    result = await get_video_gallery_service(mock_session, skip=10, limit=5)

    mock_session.exec.assert_awaited_once()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_my_videos_history_success():
    mock_session = MagicMock()

    current_user = User(
        id=1, username="testuser", email="t@test.com", hashed_password="hash"
    )

    video1 = Video(
        id=1,
        user_id=1,
        text="My Video 1",
        status=VideoStatus.completed,
        created_at=datetime.now(timezone.utc),
    )

    video2 = Video(
        id=2,
        user_id=1,
        text="My Video 2",
        status=VideoStatus.processing,
        created_at=datetime.now(timezone.utc),
    )

    mock_result = MagicMock()
    mock_result.all.return_value = [(video1, current_user), (video2, current_user)]
    mock_session.exec = AsyncMock(return_value=mock_result)

    result = await get_my_videos_history_service(
        current_user, mock_session, skip=0, limit=10
    )

    assert len(result) == 2
    assert result[0].author_username == "testuser"
    assert result[1].author_username == "testuser"


@pytest.mark.asyncio
async def test_get_my_videos_history_empty():
    mock_session = MagicMock()

    current_user = User(
        id=1, username="testuser", email="t@test.com", hashed_password="hash"
    )

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.exec = AsyncMock(return_value=mock_result)

    result = await get_my_videos_history_service(
        current_user, mock_session, skip=0, limit=10
    )

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_video_status_success():
    mock_session = MagicMock()

    current_user = User(
        id=1, username="testuser", email="t@test.com", hashed_password="hash"
    )

    video = Video(
        id=42,
        user_id=1,
        text="Test Video",
        status=VideoStatus.processing,
        created_at=datetime.now(timezone.utc),
    )

    mock_result = MagicMock()
    mock_result.first.return_value = (video, current_user)
    mock_session.exec = AsyncMock(return_value=mock_result)

    result = await get_video_status_service("42", current_user, mock_session)

    assert result.id == "42"
    assert result.status == VideoStatus.processing
    assert result.author_username == "testuser"


@pytest.mark.asyncio
async def test_get_video_status_not_found():
    mock_session = MagicMock()

    current_user = User(
        id=1, username="testuser", email="t@test.com", hashed_password="hash"
    )

    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.exec = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await get_video_status_service("999", current_user, mock_session)

    assert exc_info.value.status_code == 404
    assert "Video not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_video_status_invalid_id():
    mock_session = MagicMock()

    current_user = User(
        id=1, username="testuser", email="t@test.com", hashed_password="hash"
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_video_status_service("invalid_id", current_user, mock_session)

    assert exc_info.value.status_code == 404
    assert "Video not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_video_status_with_thumbnail():
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = MagicMock()

    video_obj = Video(
        id=10,
        status=VideoStatus.processing,
        user_id=5,
        text="video text",
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
        thumbnail_url="http://minio/thumb.jpg",
    )

    result = await update_video_status_service(
        video_id="10",
        update_data=update_payload,
        x_worker_token=settings.WORKER_SECRET_TOKEN,
        session=mock_session,
    )

    assert result.status == VideoStatus.completed
    assert result.video_url == "http://minio/vid.mp4"
    assert result.thumbnail_url == "http://minio/thumb.jpg"


@pytest.mark.asyncio
async def test_update_video_status_invalid_id():
    mock_session = MagicMock()

    update_payload = VideoUpdateStatus(status=VideoStatus.failed)

    with pytest.raises(HTTPException) as exc_info:
        await update_video_status_service(
            video_id="invalid_id",
            update_data=update_payload,
            x_worker_token=settings.WORKER_SECRET_TOKEN,
            session=mock_session,
        )

    assert exc_info.value.status_code == 404
    assert "Video not found" in exc_info.value.detail
