from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.schemas.token import Token
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead, LoginRequest, GoogleLoginRequest, AppleLoginRequest

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
async def login_access_token(session: Annotated[AsyncSession, Depends(deps.get_db)], form_data: LoginRequest) -> Any:
    result = await session.execute(select(User).where(User.email == form_data.email))
    user = result.scalars().first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return Token(access_token=security.create_access_token(user.id), token_type="bearer")

async def get_or_create_social_user(session: AsyncSession, email: str, provider: str, social_id: str, first_name: str, last_name: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        # Create new user
        import uuid
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            hashed_password=security.get_password_hash(str(uuid.uuid4())), # Random password
            referral_code=str(uuid.uuid4())[:8],
            social_provider=provider,
            social_id=social_id,
            is_active=True,
            is_verified=True # Social accounts are usually verified
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Update social info if missing
        if not user.social_provider:
             user.social_provider = provider
             user.social_id = social_id
             session.add(user)
             await session.commit()
    return user

@router.post("/social/google", response_model=Token)
async def google_login(session: Annotated[AsyncSession, Depends(deps.get_db)], login_in: GoogleLoginRequest) -> Any:
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        id_info = id_token.verify_oauth2_token(login_in.token, google_requests.Request(), audience=settings.GOOGLE_CLIENT_ID)
        email = id_info['email']
        social_id = id_info['sub']
        first_name = id_info.get('given_name', "")
        last_name = id_info.get('family_name', "")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    user = await get_or_create_social_user(session, email, "google", social_id, first_name, last_name)
    return Token(access_token=security.create_access_token(user.id), token_type="bearer")

@router.post("/social/apple", response_model=Token)
async def apple_login(session: Annotated[AsyncSession, Depends(deps.get_db)], login_in: AppleLoginRequest) -> Any:
    try:
        import jwt
        import requests
        from jwt.algorithms import RSAAlgorithm
        import json
        
        # Fetch Apple's public keys
        apple_keys_url = "https://appleid.apple.com/auth/keys"
        keys = requests.get(apple_keys_url).json()['keys']
        
        # Get kid from token header
        header = jwt.get_unverified_header(login_in.token)
        kid = header['kid']
        
        # Find matching key
        key = next(k for k in keys if k['kid'] == kid)
        public_key = RSAAlgorithm.from_jwk(json.dumps(key))
        
        # Verify token
        payload = jwt.decode(login_in.token, public_key, algorithms=['RS256'], audience=settings.APPLE_CLIENT_ID) 
        email = payload.get('email')
        social_id = payload['sub']
        
        if not email:
            raise HTTPException(status_code=400, detail="Could not retrieve email from provider")
            
    except Exception as e:
        print(f"Apple login error: {e}")
        raise HTTPException(status_code=400, detail="Invalid Apple token")

    user = await get_or_create_social_user(session, email, "apple", social_id, login_in.first_name or "", login_in.last_name or "")
    return Token(access_token=security.create_access_token(user.id), token_type="bearer")
