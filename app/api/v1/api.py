from fastapi import APIRouter
from app.api.v1.endpoints import auth, wallet, circles, notifications

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
api_router.include_router(circles.router, prefix="/circles", tags=["circles"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
