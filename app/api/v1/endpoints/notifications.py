from typing import Annotated, List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationRead
from app.schemas.response import APIResponse
from app.core.rate_limit import limiter
from fastapi import Request

router = APIRouter()

@router.get("/", response_model=APIResponse[List[NotificationRead]])
@limiter.limit("20/minute")
async def get_notifications(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[deps.PageParams, Depends()]
):
    """
    Retrieve all notifications for the current user.
    """
    query = select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.id.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(query)
    return APIResponse(message="Notifications retrieved", data=result.scalars().all())

@router.post("/{notification_id}/read", response_model=APIResponse[dict])
@limiter.limit("50/minute")
async def mark_as_read(
    request: Request,
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Mark a specific notification as read.
    """
    notification = await session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your notification")
        
    notification.is_read = True
    session.add(notification)
    await session.commit()
    
    return APIResponse(message="Marked as read", data={})
