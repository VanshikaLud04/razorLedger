import os
from dotenv import load_dotenv
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

Base = declarative_base()

# Engine and session factory are only created when DATABASE_URL is configured.
# This allows tests that don't need a DB to import app modules safely.
if DATABASE_URL:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def get_db():
        async with AsyncSessionLocal() as session:
            yield session
else:
    engine = None
    AsyncSessionLocal = None

    async def get_db():  # type: ignore[misc]
        raise RuntimeError(
            "DATABASE_URL is not configured. Copy .env.example to .env and set it."
        )
