"""Database engine and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


class DatabaseSessionManager:
    """Manage the async database engine and session factory."""

    def __init__(self) -> None:
        """Initialize the engine and session factory from settings."""
        settings = get_settings()
        self._engine: AsyncEngine = create_async_engine(
            settings.database.url,
            future=True,
            echo=settings.database.echo or settings.app.debug,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        """Expose the configured async engine."""
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Expose the configured session factory."""
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a managed session with rollback protection."""
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def dispose(self) -> None:
        """Dispose the async engine cleanly."""
        await self._engine.dispose()


database_manager = DatabaseSessionManager()
engine = database_manager.engine
SessionLocal = database_manager.session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for request-scoped work."""
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def get_transaction_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a managed transactional session for service-level operations."""
    async with database_manager.session() as session:
        yield session
