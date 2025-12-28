from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Global Rate Limiter instance using remote address as key and Redis as storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.CELERY_BROKER_URL # Reusing Redis URL
)
