from typing import Annotated, List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.circle import Circle, CircleMember
from app.schemas.circle import CircleCreate, CircleRead, CircleMemberRead
from app.schemas.response import APIResponse

router = APIRouter()

@router.post("/", response_model=APIResponse[CircleRead])
async def create_circle(
    circle_in: CircleCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    # generate invite code
    invite_code = str(uuid.uuid4())[:8]
    
    circle = Circle.model_validate(
        circle_in, 
        update={"invite_code": invite_code}
    )
    session.add(circle)
    await session.commit()
    await session.refresh(circle)
    
    # Add creator as host
    member = CircleMember(
        circle_id=circle.id,
        user_id=current_user.id,
        role="host",
        payout_order=1
    )
    session.add(member)
    await session.commit()
    
    return APIResponse(message="Circle created successfully", data=circle)

@router.get("/", response_model=APIResponse[List[CircleRead]])
async def get_circles(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    # Join Circle and CircleMember to get circles where user is a member
    query = select(Circle).join(CircleMember).where(CircleMember.user_id == current_user.id)
    result = await session.execute(query)
    return APIResponse(message="Circles retrieved", data=result.scalars().all())

@router.get("/{circle_id}", response_model=APIResponse[CircleRead])
async def get_circle(
    circle_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    circle = await session.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")
        
    # Check membership
    query = select(CircleMember).where(
        CircleMember.circle_id == circle_id, 
        CircleMember.user_id == current_user.id
    )
    result = await session.execute(query)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this circle")
        
    return APIResponse(message="Circle details retrieved", data=circle)

@router.post("/join", response_model=APIResponse[dict])
async def join_circle(
    invite_code: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    query = select(Circle).where(Circle.invite_code == invite_code)
    result = await session.execute(query)
    circle = result.scalar_one_or_none()
    
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")
        
    # Check if already member
    query = select(CircleMember).where(
        CircleMember.circle_id == circle.id,
        CircleMember.user_id == current_user.id
    )
    result = await session.execute(query)
    existing_member = result.scalar_one_or_none()
    
    if existing_member:
        raise HTTPException(status_code=400, detail="Already a member")
        
    # Get next payout order
    query = select(CircleMember).where(CircleMember.circle_id == circle.id)
    result = await session.execute(query)
    members = result.scalars().all()
    next_order = len(members) + 1
    
    new_member = CircleMember(
        circle_id=circle.id,
        user_id=current_user.id,
        role="member",
        payout_order=next_order
    )
    session.add(new_member)
    await session.commit()
    
    return APIResponse(message="Joined circle successfully", data={"circle_id": circle.id})
