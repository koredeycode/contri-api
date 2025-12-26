import uuid
from sqlmodel import SQLModel, Field

class Notification(SQLModel, table=True):
    """
    Model for user notifications.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the notification")
    user_id: uuid.UUID = Field(foreign_key="user.id", description="ID of the user receiving the notification")
    title: str = Field(description="Notification title")
    body: str = Field(description="Content of the notification")
    type: str = Field(description="Type of notification (e.g., 'action_required', 'info', 'success')")
    is_read: bool = Field(default=False, description="Whether the notification has been read")
    action_url: str | None = Field(default=None, description="Deep link for action required")
    priority: str = Field(default="normal", description="Priority level (e.g., 'high', 'normal')")
