from typing import Annotated, Any
from fastapi import APIRouter, Depends
from app.api import deps
from app.models.user import User

from app.schemas.user import UserRead
from app.schemas.response import APIResponse

router = APIRouter()

@router.get("/me", response_model=APIResponse[UserRead])
async def read_user_me(current_user: Annotated[User, Depends(deps.get_current_user)]) -> Any:
    """
    Get current user details.
    """
    return APIResponse(message="User details retrieved", data=current_user)
