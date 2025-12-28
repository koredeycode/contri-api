from typing import Annotated, List, Any
import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.models.user import User
from app.models.circle import CircleMember
from app.models.chat import ChatMessage
from app.schemas.chat import ChatMessageCreate, ChatMessageRead
from app.schemas.response import APIResponse
from app.core.rate_limit import limiter

router = APIRouter()

@router.get("/{circle_id}", response_model=APIResponse[List[ChatMessageRead]])
@limiter.limit("30/minute")
async def get_circle_messages(
    request: Request,
    circle_id: uuid.UUID,
    current_user: Annotated[User, Depends(deps.get_current_user)],
    session: Annotated[AsyncSession, Depends(deps.get_db)],
    before: datetime.datetime | None = None
) -> Any:
    """
    Retrieve message history for a circle.
    Returns latest 100 messages. 
    Use 'before' timestamp (ISO format) to paginate backwards.
    """
    # Verify membership
    membership = await session.execute(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == current_user.id
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this circle")

    # Fetch messages with sender info
    # Cursor pagination: WHERE timestamp < before ORDER BY timestamp DESC LIMIT 100
    query = select(ChatMessage, User).join(User, ChatMessage.user_id == User.id)\
        .where(ChatMessage.circle_id == circle_id)
        
    if before:
        query = query.where(ChatMessage.timestamp < before)

    query = query.order_by(ChatMessage.timestamp.desc())\
        .limit(100)
    
    result = await session.execute(query)
    rows = result.all()
    
    message_list = []
    for message, user in rows:
        msg_read = ChatMessageRead(
            id=message.id,
            circle_id=message.circle_id,
            user_id=message.user_id,
            content=message.content,
            timestamp=message.timestamp,
            message_type=message.message_type,
            attachment_url=message.attachment_url,
            sender_name=f"{user.first_name} {user.last_name}"
        )
        message_list.append(msg_read)
    
    # Reverse to return in chronological order (oldest -> newest)
    return APIResponse(message="Messages retrieved", data=message_list[::-1])

@router.post("/{circle_id}", response_model=APIResponse[ChatMessageRead])
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    circle_id: uuid.UUID,
    message_in: ChatMessageCreate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
    session: Annotated[AsyncSession, Depends(deps.get_db)]
) -> Any:
    """
    Send a message to a circle.
    """
    # Verify membership
    membership = await session.execute(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == current_user.id
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this circle")
    
    # Determine message type
    msg_type = "text"
    if message_in.attachment_url:
        msg_type = "image" if any(ext in message_in.attachment_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']) else "file"

    message = ChatMessage(
        circle_id=circle_id,
        user_id=current_user.id,
        content=message_in.content,
        attachment_url=message_in.attachment_url,
        message_type=msg_type
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    
    return APIResponse(
        message="Message sent", 
        data=ChatMessageRead(
            id=message.id,
            circle_id=message.circle_id,
            user_id=message.user_id,
            content=message.content,
            timestamp=message.timestamp,
            message_type=message.message_type,
            attachment_url=message.attachment_url,
            sender_name=f"{current_user.first_name} {current_user.last_name}"
        )
    )
