from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exception_handlers import http_exception_handler, validation_exception_handler
from app.schemas.response import ValidationErrorResponse, HTTPErrorResponse

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    from sqlmodel import SQLModel
    from app.db.session import engine
    from app.models import User, Wallet, BankAccount, Card, Circle, CircleMember, Contribution, Notification
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        
    print("Application running at http://localhost:8000")
    print("Swagger UI: http://localhost:8000/docs")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    responses={
        400: {"model": ValidationErrorResponse, "description": "Validation Error"},
        401: {"model": HTTPErrorResponse, "description": "Unauthorized"},
        403: {"model": HTTPErrorResponse, "description": "Forbidden"},
        404: {"model": HTTPErrorResponse, "description": "Not Found"},
    }
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
