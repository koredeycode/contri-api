from typing import Annotated, List, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.models.user import User
from app.models.circle import CircleMember
from app.models.chat import ChatMessage
from app.schemas.chat import ChatMessageCreate, ChatMessageRead
from app.schemas.response import APIResponse

router = APIRouter()

@router.get("/{circle_id}", response_model=APIResponse[List[ChatMessageRead]])
async def get_circle_messages(
    circle_id: uuid.UUID,
    current_user: Annotated[User, Depends(deps.get_current_user)],
    session: Annotated[AsyncSession, Depends(deps.get_db)]
) -> Any:
    """
    Retrieve message history for a circle.
    Only members of the circle can view messages.
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
    query = select(ChatMessage, User).join(User, ChatMessage.user_id == User.id).where(ChatMessage.circle_id == circle_id).order_by(ChatMessage.timestamp.asc())
    result = await session.execute(query)
    
    message_list = []
    for message, user in result:
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
        
    return APIResponse(message="Messages retrieved", data=message_list)

@router.post("/{circle_id}", response_model=APIResponse[ChatMessageRead])
async def send_message(
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
