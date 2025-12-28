import uuid
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

class ChatMessage(SQLModel, table=True):
    """
    Model for storing chat messages within a circle.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the message")
    circle_id: uuid.UUID = Field(foreign_key="circle.id", index=True, description="ID of the circle where the message was sent")
    user_id: uuid.UUID = Field(foreign_key="user.id", description="ID of the user who sent the message")
    content: str = Field(description="Content of the message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None), description="Time when the message was sent")
    message_type: str = Field(default="text", description="Type of message (e.g., 'text', 'system', 'image')")
    attachment_url: str | None = Field(default=None, description="URL of an attached file or image")
