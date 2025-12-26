import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.core.config import settings
from app.db.session import get_db

# Use the same DB or a test one if configured
# For now, we use the main DB. In production, this should be a separate DB.
engine = create_async_engine(str(settings.DATABASE_URL))
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

@pytest.fixture
async def session():
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(session):
    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    
    # Using AsyncClient for ASGI app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    
    app.dependency_overrides.clear()
