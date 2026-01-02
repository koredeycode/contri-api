
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import get_db
from app.core.rate_limit import limiter

# Disable rate limiting globally for tests
limiter.enabled = False

# Use NullPool to ensure connections are closed and not shared across event loops
engine = create_async_engine(str(settings.DATABASE_URL), poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

@pytest.fixture
async def session():
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(session):
    # Create a fresh app for each test to avoid middleware/loop issues
    new_app = FastAPI()
    new_app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Override dependency directly on the new app (or global overrides if it copies?)
    # Dependency overrides work on the app instance.
    
    async def override_get_db():
        yield session

    new_app.dependency_overrides[get_db] = override_get_db
    
    # We need to run startup/shutdown?
    # Our lifespan in main.py creates tables. tests might rely on tables existing.
    # Since we use a persistent DB (Postgres in docker probably), tables might exist.
    # But usually creating them once is good.
    # Let's assume tables exist or run creation manually if needed.
    # For now, let's just accept the router.
    
    async with AsyncClient(transport=ASGITransport(app=new_app), base_url="http://test") as c:
        yield c

@pytest.fixture(autouse=True)
def mock_celery_task(monkeypatch):
    """
    Mock Celery task to avoid sending emails during tests.
    """
    from unittest.mock import MagicMock
    # Create a mock that has a .delay method
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    
    # Patch the task in the worker module (source)
    monkeypatch.setattr("app.worker.send_email_task", mock_task)
    
    # Patch where it is imported and used
    # If modules use 'from app.worker import send_email_task', we must patch the name in that module
    modules_to_patch = [
        "app.api.v1.endpoints.auth.send_email_task",
        "app.api.v1.endpoints.circles.send_email_task",
        "app.api.v1.endpoints.paystack.send_email_task",
        # "app.api.v1.endpoints.email_test.send_email_task", # Might not be loaded in all tests
    ]
    
    import sys
    for module_path in modules_to_patch:
        # Only patch if the module is already loaded, otherwise patching app.worker (source) might be enough 
        # IF the module imports it AFTER this fixture runs (unlikely with pytest collection).
        # But force patching common endpoints.
        try:
             monkeypatch.setattr(module_path, mock_task)
        except AttributeError:
            # Module might not be imported yet or name doesn't exist
            pass
            
    return mock_task
