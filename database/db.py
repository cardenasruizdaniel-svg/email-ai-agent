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
    """Initializes the database schema with automated persistent backup protection."""
    # Ensure automated backup before applying any schema updates
    if "sqlite" in db_url:
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        if db_path != ":memory:" and os.path.exists(db_path) and os.path.getsize(db_path) > 0:
            try:
                import shutil
                backup_dir = os.path.join(os.path.dirname(os.path.abspath(db_path)), "backups")
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, "email_agent_latest.bak")
                shutil.copy2(db_path, backup_path)
            except Exception as e:
                pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency for providing database sessions."""
    async with AsyncSessionLocal() as session:
        yield session
