"""Database engine and migration helpers.

Uses Alembic for versioned migrations. Falls back to create_all for
zero-downtime MVP bootstraps where Alembic cannot reach the database.
"""

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
    """Run all pending Alembic migrations, falling back to create_all."""
    try:
        await migrate_to_head(engine)
    except Exception:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def migrate_to_head(engine: AsyncEngine) -> None:
    """Apply pending Alembic migrations (synchronous executor bridge)."""
    from alembic import command as alembic_command
    from alembic.config import Config

    import asyncio

    loop = asyncio.get_event_loop()

    def _run() -> None:
        url = str(engine.url).replace("***", engine.url.password or "")
        cfg = Config()
        cfg.set_main_option("script_location", "alembic")
        cfg.set_main_option("sqlalchemy.url", url)
        cfg.attributes["connection"] = None
        alembic_command.upgrade(cfg, "head")

    await loop.run_in_executor(None, _run)


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
