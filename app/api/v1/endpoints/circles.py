from typing import Annotated, List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

import random
from datetime import datetime

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.circle import Circle, CircleMember
from app.schemas.circle import CircleCreate, CircleRead, CircleUpdate, CircleMemberRead, CircleMemberReorder
from app.schemas.response import APIResponse
from app.core.config import settings

router = APIRouter()

@router.post("/", response_model=APIResponse[CircleRead])
async def create_circle(
    circle_in: CircleCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Create a new circle.
    
    The user creating the circle becomes the host and the first member.
    """
    # generate invite code
    invite_code = str(uuid.uuid4())[:8]

    # Validate target_members limit
    if circle_in.target_members is not None and circle_in.target_members > settings.MAX_CIRCLE_MEMBERS:
        raise HTTPException(status_code=400, detail=f"Target members cannot exceed {settings.MAX_CIRCLE_MEMBERS}")
    
    circle = Circle.model_validate(
        circle_in, 
        update={
            "invite_code": invite_code,
            "status": "pending"
        }
    )
    session.add(circle)
    await session.commit()
    await session.refresh(circle)
    
    # Add creator as host
    member = CircleMember(
        circle_id=circle.id,
        user_id=current_user.id,
        role="host",
        payout_order=1,
        join_date=datetime.now()
    )
    session.add(member)
    await session.commit()
    
    return APIResponse(message="Circle created successfully", data=circle)

@router.get("/", response_model=APIResponse[List[CircleRead]])
async def get_circles(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    List all circles where the current user is a member.
    """
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
    """
    Get details of a specific circle.
    
    Only members of the circle can view its details.
    """
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
    """
    Join a circle using an invite code.
    
    Assigns the next available payout slot to the new member.
    """
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
    
    if len(members) >= settings.MAX_CIRCLE_MEMBERS:
        raise HTTPException(status_code=400, detail=f"Circle has reached the maximum limit of {settings.MAX_CIRCLE_MEMBERS} members")
    
    new_member = CircleMember(
        circle_id=circle.id,
        user_id=current_user.id,
        role="member",
        payout_order=next_order,
        join_date=datetime.now()
    )
    session.add(new_member)
    await session.commit()
    
    return APIResponse(message="Joined circle successfully", data={"circle_id": circle.id})

@router.patch("/{circle_id}", response_model=APIResponse[CircleRead])
async def update_circle(
    circle_id: uuid.UUID,
    circle_in: CircleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Update circle details. Only the host can update details, and only before the circle starts.
    """
    circle = await session.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")

    # Check if user is host
    query = select(CircleMember).where(
        CircleMember.circle_id == circle_id,
        CircleMember.user_id == current_user.id,
        CircleMember.role == "host"
    )
    result = await session.execute(query)
    host_member = result.scalar_one_or_none()

    if not host_member:
        raise HTTPException(status_code=403, detail="Only the host can edit the circle")

    if circle.status != "pending":
         raise HTTPException(status_code=400, detail="Cannot edit circle after it has started")

    # Detect payout preference change to 'fixed'
    old_preference = circle.payout_preference
    
    circle_data = circle_in.model_dump(exclude_unset=True)
    for key, value in circle_data.items():
        setattr(circle, key, value)
    
    # Validate target_members limit if updated
    if circle.target_members is not None and circle.target_members > settings.MAX_CIRCLE_MEMBERS:
         raise HTTPException(status_code=400, detail=f"Target members cannot exceed {settings.MAX_CIRCLE_MEMBERS}")
    
    # If changed to fixed, reorder by join_date
    if old_preference != "fixed" and circle.payout_preference == "fixed":
        query = select(CircleMember).where(CircleMember.circle_id == circle_id).order_by(CircleMember.join_date)
        result = await session.execute(query)
        members = result.scalars().all()
        
        for index, member in enumerate(members):
            member.payout_order = index + 1
            session.add(member)

    session.add(circle)
    await session.commit()
    await session.refresh(circle)

    return APIResponse(message="Circle updated successfully", data=circle)

@router.delete("/{circle_id}/members/{member_id}", response_model=APIResponse[dict])
async def remove_member(
    circle_id: uuid.UUID,
    member_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Remove a member from the circle. Only the host can remove members.
    """
    circle = await session.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")
        
    if circle.status != "pending":
         raise HTTPException(status_code=400, detail="Cannot remove members after circle has started")

    # Check if user is host
    query = select(CircleMember).where(
        CircleMember.circle_id == circle_id,
        CircleMember.user_id == current_user.id,
        CircleMember.role == "host"
    )
    result = await session.execute(query)
    host_member = result.scalar_one_or_none()

    if not host_member:
        raise HTTPException(status_code=403, detail="Only the host can remove members")
        
    if member_id == current_user.id:
        raise HTTPException(status_code=400, detail="Host cannot remove themselves")

    # Get the member to remove
    member_to_remove = await session.get(CircleMember, (member_id, circle_id))
    if not member_to_remove:
        raise HTTPException(status_code=404, detail="Member not found")

    session.delete(member_to_remove)
    await session.commit()
    
    # Re-calculate payout orders for remaining members? 
    # For now, we'll leave gaps or handle reorder later since it's pending state.

    return APIResponse(message="Member removed successfully", data={"member_id": member_id})

@router.get("/{circle_id}/members", response_model=APIResponse[List[CircleMemberRead]])
async def get_circle_members(
    circle_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get all members of a circle.
    """
    circle = await session.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")

    # Check if user is a member
    query = select(CircleMember).where(
        CircleMember.circle_id == circle_id,
        CircleMember.user_id == current_user.id
    )
    result = await session.execute(query)
    member = result.scalar_one_or_none()
    
    if not member:
         raise HTTPException(status_code=403, detail="Not a member of this circle")
         
    # Get all members
    query = select(CircleMember).where(CircleMember.circle_id == circle_id).order_by(CircleMember.payout_order)
    result = await session.execute(query)
    members = result.scalars().all()
    
    return APIResponse(message="Members retrieved", data=members)

@router.post("/{circle_id}/start", response_model=APIResponse[CircleRead])
async def start_circle(
    circle_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Start the circle. Finalizes members and payout order.
    """
    circle = await session.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")

    # Check if user is host
    query = select(CircleMember).where(
        CircleMember.circle_id == circle_id,
        CircleMember.user_id == current_user.id,
        CircleMember.role == "host"
    )
    result = await session.execute(query)
    host_member = result.scalar_one_or_none()

    if not host_member:
        raise HTTPException(status_code=403, detail="Only the host can start the circle")

    if circle.status != "pending":
        raise HTTPException(status_code=400, detail="Circle is already active or completed")

    # Check member count if target set
    query = select(CircleMember).where(CircleMember.circle_id == circle_id)
    result = await session.execute(query)
    members = result.scalars().all()
    
    if circle.target_members and len(members) < circle.target_members:
         raise HTTPException(status_code=400, detail=f"Cannot start circle. Need {circle.target_members} members, but have {len(members)}")
         
    if len(members) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 members to start a circle")

    # Handle Payout Order
    if circle.payout_preference == "random":
        # Shuffle members list (excluding host if host wants first? usually host is first, but 'random' implies full shuffle or partial)
        # Let's assume random shuffles everyone including host unless we want to enforce host first.
        # Requirement: "payout order can be randomized or ordered set by the host"
        # Let's shuffle everyone for now.
        member_indices = list(range(len(members)))
        random.shuffle(member_indices)
        
        for i, member in enumerate(members):
            member.payout_order = member_indices[i] + 1
            session.add(member)
    
    # Update Circle status
    circle.status = "active"
    if not circle.cycle_start_date:
        circle.cycle_start_date = datetime.now()
        
    session.add(circle)
    await session.commit()
    await session.refresh(circle)
    
    return APIResponse(message="Circle started successfully", data=circle)

@router.put("/{circle_id}/members/order", response_model=APIResponse[list[CircleMemberRead]])
async def reorder_members(
    circle_id: uuid.UUID,
    order_data: CircleMemberReorder,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Manually set the payout order of members.
    """
    circle = await session.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")

    # Check if user is host
    query = select(CircleMember).where(
        CircleMember.circle_id == circle_id,
        CircleMember.user_id == current_user.id,
        CircleMember.role == "host"
    )
    result = await session.execute(query)
    host_member = result.scalar_one_or_none()

    if not host_member:
        raise HTTPException(status_code=403, detail="Only the host can reorder members")

    if circle.status != "pending":
        raise HTTPException(status_code=400, detail="Cannot reorder members after circle has started")

    # Fetch all members
    query = select(CircleMember).where(CircleMember.circle_id == circle_id)
    result = await session.execute(query)
    current_members = result.scalars().all()
    member_map = {m.user_id: m for m in current_members}

    # Validate input: ensure all members are present in the list and no duplicates
    provided_ids = set(order_data.member_ids)
    existing_ids = set(m.user_id for m in current_members)
    
    if provided_ids != existing_ids:
        raise HTTPException(status_code=400, detail="Provided member list does not match actual circle members")

    # Update order
    updated_members = []
    for index, user_id in enumerate(order_data.member_ids):
        member = member_map[user_id]
        member.payout_order = index + 1
        session.add(member)
        updated_members.append(member)
        
    await session.commit()
    
    return APIResponse(message="Members reordered successfully", data=updated_members)
