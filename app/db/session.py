from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(str(settings.DATABASE_URL))
AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
