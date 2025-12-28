from typing import Annotated, List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

import random
from datetime import datetime

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.circle import Circle, CircleMember, Contribution
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.enums import ContributionStatus, TransactionType, TransactionStatus
from app.schemas.circle import CircleCreate, CircleRead, CircleUpdate, CircleMemberRead, CircleMemberReorder
from app.schemas.response import APIResponse
from app.core.config import settings
from app.utils.financials import calculate_current_cycle

router = APIRouter()
from app.worker import send_email_task

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
    
    # Send Joined Email
    send_email_task.delay(
        email_to=current_user.email,
        subject=f"You joined {circle.name}",
        html_template="circle_joined.html",
        environment={
             "project_name": "Contri",
             "name": current_user.first_name,
             "circle_name": circle.name,
             "currency": "NGN",
             "amount": f"{circle.amount / 100:,.2f}",
             "frequency": circle.frequency,
             "payout_order": next_order,
             "circle_link": f"https://contri.app/circles/{circle.id}"
        }
    )

    # Notify Host
    query = select(CircleMember).where(
        CircleMember.circle_id == circle.id,
        CircleMember.role == "host"
    )
    result = await session.execute(query)
    host = result.scalar_one_or_none()

    if host:
         host_user = await session.get(User, host.user_id)
         if host_user:
             send_email_task.delay(
                email_to=host_user.email,
                subject=f"New Member Joined {circle.name}",
                html_template="member_joined.html",
                environment={
                     "project_name": "Contri",
                     "name": host_user.first_name,
                     "member_name": current_user.first_name,
                     "circle_name": circle.name,
                     "current_members": len(members) + 1, # +1 for the new member
                     "target_members": circle.target_members or "Unlimited",
                     "circle_link": f"https://contri.app/circles/{circle.id}"
                }
             )

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
    
    # Notify all members
    # Optimize: Fetch all users in one query
    member_user_ids = [m.user_id for m in members]
    query = select(User).where(User.id.in_(member_user_ids))
    result = await session.execute(query)
    users = result.scalars().all()
    user_map = {u.id: u for u in users}

    for member in members:
         member_user = user_map.get(member.user_id)
         if member_user:
             send_email_task.delay(
                email_to=member_user.email,
                subject=f"{circle.name} has started! 🚀",
                html_template="circle_started.html",
                environment={
                     "project_name": "Contri",
                     "name": member_user.first_name,
                     "circle_name": circle.name,
                     "start_date": circle.cycle_start_date.strftime("%Y-%m-%d"),
                     "currency": "NGN",
                     "amount": f"{circle.amount / 100:,.2f}",
                     "frequency": circle.frequency,
                     "circle_link": f"https://contri.app/circles/{circle.id}"
                }
             )
    
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


@router.post("/{circle_id}/contribute", response_model=APIResponse[dict])
async def contribute_to_circle(
    circle_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Contribute to the circle for the current cycle.
    """
    circle = await session.get(Circle, circle_id)
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found")

    if circle.status != "active":
        raise HTTPException(status_code=400, detail="Circle is not active")

    # Check membership
    query = select(CircleMember).where(
        CircleMember.circle_id == circle_id, 
        CircleMember.user_id == current_user.id
    )
    result = await session.execute(query)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this circle")

    current_cycle = calculate_current_cycle(circle)
    
    # Check if already contributed for this cycle
    query = select(Contribution).where(
        Contribution.circle_id == circle_id,
        Contribution.user_id == current_user.id,
        Contribution.cycle_number == current_cycle,
        Contribution.status == ContributionStatus.PAID
    )
    result = await session.execute(query)
    existing_contribution = result.scalar_one_or_none()
    
    if existing_contribution:
        raise HTTPException(status_code=400, detail=f"Already contributed for cycle {current_cycle}")

    # Process Payment: Debit User Wallet
    # Get user wallet
    query = select(Wallet).where(Wallet.user_id == current_user.id)
    result = await session.execute(query)
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(status_code=400, detail="User wallet not found")
        
    contribution_amount_cents = circle.amount
    if wallet.balance < contribution_amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        
    # Deduct from wallet
    wallet.balance -= contribution_amount_cents
    session.add(wallet)
    
    # Create Debit Transaction
    debit_txn = Transaction(
        wallet_id=wallet.id,
        amount=contribution_amount_cents,
        type=TransactionType.CONTRIBUTION,
        status=TransactionStatus.SUCCESS,
        reference=str(uuid.uuid4()),
        description=f"Contribution to circle {circle.name} (Cycle {current_cycle})"
    )
    session.add(debit_txn)
    
    # Record Contribution
    contribution = Contribution(
        circle_id=circle.id,
        user_id=current_user.id,
        cycle_number=current_cycle,
        amount=circle.amount,
        status=ContributionStatus.PAID,
        paid_at=datetime.now()
    )
    session.add(contribution)
    
    # Check for Payout Logic
    # 1. Get total members count
    query = select(CircleMember).where(CircleMember.circle_id == circle_id)
    result = await session.execute(query)
    all_members = result.scalars().all()
    total_members_count = len(all_members)
    
    # 2. Get count of paid contributions for this cycle (including the one just added)
    # Since we haven't committed yet, the new contribution acts as +1
    query = select(Contribution).where(
        Contribution.circle_id == circle_id,
        Contribution.cycle_number == current_cycle,
        Contribution.status == ContributionStatus.PAID
    )
    result = await session.execute(query)
    paid_contributions = result.scalars().all()
    paid_count = len(paid_contributions) + 1 # Add 1 for the current pending contribution
    
    payout_triggered = False
    recipient_name = ""
    
    if paid_count == total_members_count:
        # Everyone has contributed -> Trigger Payout
        payout_triggered = True
        
        # Identify Recipient: Payout Order == Cycle Number
        # If cycle > members, we might need modulo logic or implementation of multi-rounds. 
        # For MVP, let's assume Payout Order matches Cycle Number exactly.
        
        target_order = current_cycle
        if target_order > total_members_count:
             # Fallback or loop? Let's use modulo logic just in case: (cycle - 1) % members + 1
             target_order = ((current_cycle - 1) % total_members_count) + 1
        
        recipient_member = next((m for m in all_members if m.payout_order == target_order), None)
        
        if recipient_member:
            # Credit Recipient Wallet
            query = select(Wallet).where(Wallet.user_id == recipient_member.user_id)
            result = await session.execute(query)
            recipient_wallet = result.scalar_one_or_none()
            
            if recipient_wallet:
                total_payout_cents = contribution_amount_cents * total_members_count
                recipient_wallet.balance += total_payout_cents
                session.add(recipient_wallet)
                
                # Create Credit Transaction
                credit_txn = Transaction(
                    wallet_id=recipient_wallet.id,
                    amount=total_payout_cents,
                    type=TransactionType.PAYOUT,
                    status=TransactionStatus.SUCCESS,
                    reference=str(uuid.uuid4()),
                    description=f"Payout from circle {circle.name} (Cycle {current_cycle})"
                )
                session.add(credit_txn)
                recipient_name = str(recipient_member.user_id) # Ideally get user name, but ID is fine for log

    await session.commit()
    
    # Send Contribution Email
    send_email_task.delay(
        email_to=current_user.email,
        subject=f"Contribution Received - {circle.name}",
        html_template="contribution_success.html",
        environment={
             "project_name": "Contri",
             "name": current_user.first_name,
             "amount": f"{circle.amount / 100:,.2f}",
             "currency": "NGN",
             "cycle": current_cycle,
             "circle_name": circle.name,
             "date": datetime.now().strftime("%Y-%m-%d"),
             "circle_link": f"https://contri.app/circles/{circle.id}"
        }
    )
    
    # Send Payout Email
    if payout_triggered and recipient_member:
        recipient_user = await session.get(User, recipient_member.user_id)
        if recipient_user:
             send_email_task.delay(
                email_to=recipient_user.email,
                subject=f"Payout Received from {circle.name}!",
                html_template="payout_received.html",
                environment={
                     "project_name": "Contri",
                     "name": recipient_user.first_name,
                     "amount": f"{(circle.amount * total_members_count) / 100:,.2f}",
                     "currency": "NGN",
                     "cycle": current_cycle,
                     "circle_name": circle.name,
                     "dashboard_link": "https://contri.app/wallet"
                }
             )

    return APIResponse(
        message="Contribution successful", 
        data={
            "contribution_id": contribution.id,
            "cycle": current_cycle,
            "payout_triggered": payout_triggered,
            "recipient": recipient_name if payout_triggered else None
        }
    )
