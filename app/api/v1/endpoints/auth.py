from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.core import security
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter()

@router.post("/signup", response_model=UserRead)
async def create_user(*, session: Annotated[AsyncSession, Depends(deps.get_db)], user_in: UserCreate) -> Any:
    result = await session.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # Generate referral code if missing
    import uuid
    ref_code = user_in.referral_code or str(uuid.uuid4())[:8]
    
    user_data = user_in.model_dump(exclude={"referral_code"})
    user = User(**user_data, referral_code=ref_code)
    user.hashed_password = security.get_password_hash(user_in.password)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login_access_token(session: Annotated[AsyncSession, Depends(deps.get_db)], form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Any:
    result = await session.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return Token(access_token=security.create_access_token(user.id), token_type="bearer")
