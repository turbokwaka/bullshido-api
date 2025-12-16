import pytest
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker


from models import User
from schemas import (
    VideoCreateRequest,
    VoicePreset,
    SubtitlePosition,
    VideoUpdateStatus,
    VideoStatus,
)
from services.videos_service import (
    create_video_generation_task_service,
    update_video_status_service,
)

pytest.importorskip("aiosqlite")


class DummyRedis:
    def __init__(self):
        self.enqueued = []

    async def enqueue_job(self, name, **kwargs):
        self.enqueued.append((name, kwargs))
        return "job-id"


@pytest.mark.asyncio
async def test_integration_create_and_update_video(monkeypatch, tmp_path):
    db_file = tmp_path / "test_integration.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    dummy_redis = DummyRedis()

    async def fake_get_redis():
        return dummy_redis

    monkeypatch.setattr("services.videos_service.get_redis", fake_get_redis)

    async with async_session() as session:
        user = User(username="int_user", email="i@t.com", hashed_password="pw")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        req = VideoCreateRequest(
            text="This is an integration test video text",
            voice=VoicePreset.af_bella,
            subtitle_style_id=2,
            subtitle_position=SubtitlePosition.bottom,
        )

        resp = await create_video_generation_task_service(req, user, session)

        assert resp.author_username == user.username
        assert resp.text == req.text
        assert resp.status == VideoStatus.queued

        assert len(dummy_redis.enqueued) == 1
        name, kwargs = dummy_redis.enqueued[0]
        assert name == "generate_video"
        assert kwargs["text"] == req.text
        assert kwargs["voice"] == VoicePreset.af_bella.value
        assert kwargs["subtitle_position"] == SubtitlePosition.bottom.value

        monkeypatch.setattr("config.settings.WORKER_SECRET_TOKEN", "worker-token")

        update_payload = VideoUpdateStatus(
            status=VideoStatus.completed,
            video_url="http://minio/test.mp4",
        )

        updated = await update_video_status_service(
            video_id=str(resp.id),
            update_data=update_payload,
            x_worker_token="worker-token",
            session=session,
        )

        assert updated.status == VideoStatus.completed
        assert updated.video_url == "http://minio/test.mp4"
        assert updated.author_username == user.username
