from typing import Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

from config import settings

# postgreSQL
engine = create_async_engine(settings.database_url, echo=True, future=True)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


# Redis
_redis_pool: Optional[ArqRedis] = None


async def get_redis() -> ArqRedis:
    global _redis_pool

    if _redis_pool is not None:
        return _redis_pool

    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        database=0,
    )

    _redis_pool = await create_pool(redis_settings)
    return _redis_pool
