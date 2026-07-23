"""Хелперы асинхронного движка и сессий БД"""

from collections.abc import AsyncGenerator
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings | None = None) -> None:
    """Инициализирует асинхронный engine и фабрику сессий при наличии DATABASE_URL"""
    global _engine, _session_factory

    settings = settings or get_settings()
    if not settings.database_url:
        return

    _engine = create_async_engine(
        settings.database_url,
        echo=settings.app_debug,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Предоставляет асинхронную сессию БД для зависимостей FastAPI"""
    session_factory = cast(async_sessionmaker[AsyncSession], _session_factory)
    if _session_factory is None:
        raise RuntimeError("Database is not configured.")
    async with session_factory() as session:
        yield session


def get_engine():
    """Возвращает текущий async engine или None"""
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """Возвращает фабрику сессий после init_db или None"""
    return _session_factory
