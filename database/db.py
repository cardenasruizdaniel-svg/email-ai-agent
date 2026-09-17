import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config.settings import settings
from database.models import Base

db_url = settings.DATABASE_URL

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not ("+asyncpg" in db_url or "+psycopg" in db_url):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Ensure directory exists for SQLite database file if applicable
if "sqlite" in db_url:
    db_path = db_url.replace("sqlite+aiosqlite:///", "")
    if db_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

engine = create_async_engine(
    db_url,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initializes the database schema."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency for providing database sessions."""
    async with AsyncSessionLocal() as session:
        yield session
