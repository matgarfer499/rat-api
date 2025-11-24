from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Naming convention for PostgreSQL (best practice)
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)
Base = declarative_base(metadata=metadata)

# Database configuration
# Change to your DATABASE_URL
DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # For development with SQLite
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"  # For production with PostgreSQL

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Initialize database (create tables)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
