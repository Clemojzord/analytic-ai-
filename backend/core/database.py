"""
Analytic AI — Async Database Setup (SQLAlchemy + aiosqlite)
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

# Async engine
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Session factory
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def init_db():
    """Create all tables defined by Base subclasses."""
    # Import models so they register with Base.metadata
    import models.user  # noqa: F401
    import models.dataset  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
