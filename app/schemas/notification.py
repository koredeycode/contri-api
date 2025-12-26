import uuid
from sqlmodel import SQLModel

class NotificationRead(SQLModel):
    """
    Schema for reading a notification.
    """
    id: uuid.UUID
    title: str
    body: str
    type: str
    is_read: bool
    action_url: str | None
    priority: str
    created_at: str | None = None # Assuming created_at might be added later or computed
