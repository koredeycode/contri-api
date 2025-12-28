from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User

from app.schemas.user import UserRead, UserUpdate
from app.schemas.response import APIResponse
from app.core.security import get_password_hash

router = APIRouter()

@router.get("/me", response_model=APIResponse[UserRead])
async def read_user_me(current_user: Annotated[User, Depends(deps.get_current_user)]) -> Any:
    """
    Get current user details.
    """
    return APIResponse(message="User details retrieved", data=current_user)

@router.put("/me", response_model=APIResponse[UserRead])
async def update_user_me(
    *,
    session: Annotated[AsyncSession, Depends(deps.get_db)],
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Any:
    """
    Update own user.
    """
    user_data = user_in.model_dump(exclude_unset=True)
    
    if "password" in user_data and user_data["password"]:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        user_data["hashed_password"] = hashed_password
        del user_data["password"]
        
    for field, value in user_data.items():
        setattr(current_user, field, value)

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    
    return APIResponse(message="User profile updated", data=current_user)
