from fastapi import APIRouter
from app.api.v1.endpoints import auth, wallet, circles, notifications, users, chat, transactions, paystack

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
api_router.include_router(circles.router, prefix="/circles", tags=["circles"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(paystack.router, prefix="/webhooks/paystack", tags=["webhooks"])
