from typing import Annotated, List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationRead

router = APIRouter()

@router.get("/", response_model=List[NotificationRead])
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    query = select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.id.desc())
    result = await session.execute(query)
    return result.scalars().all()

@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    notification = await session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your notification")
        
    notification.is_read = True
    session.add(notification)
    await session.commit()
    
    return {"message": "Marked as read"}
