from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alphaforge.core.config import Settings
from alphaforge.models.orm import Base


def create_engine(settings: Settings) -> AsyncEngine:
    """Create the async SQLAlchemy engine."""
    return create_async_engine(
        settings.database_url,
        echo=settings.app_debug and settings.app_env == "development",
        pool_pre_ping=True,
    )


def create_engine_from_url(url: str, *, echo: bool = False) -> AsyncEngine:
    """Create an engine from a raw database URL."""
    return create_async_engine(url, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine) -> None:
    """Create tables if they do not exist (MVP; Alembic later)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
