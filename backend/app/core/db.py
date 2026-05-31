from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_recycle=600,  # 10 min — shorter window mitigates stale connections after MySQL restart
)

# Note: pool_pre_ping is incompatible with aiomysql's async ping() signature.
# pool_recycle=600 provides a practical compromise for stale-connection recovery.


async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
