from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

# 1. Async database engine & sessionmaker (Primary for FastAPI routes & lifespan)
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# 2. Synchronous fallback engine & sessionmaker
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

# 3. Asynchronous database dependency
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# get_db is the primary async dependency used across all routes
get_db = get_async_db

# get_sync_db for any synchronous utilities
def get_sync_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
