import uuid
from datetime import datetime
from sqlmodel import SQLModel

class ChatMessageCreate(SQLModel):
    """
    Schema for creating a new chat message.
    """
    content: str
    attachment_url: str | None = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "content": "Check out this receipt!",
                "attachment_url": "https://example.com/receipt.jpg"
            }
        }
    }

class ChatMessageRead(SQLModel):
    """
    Schema for reading a chat message.
    """
    id: uuid.UUID
    circle_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    timestamp: datetime
    message_type: str
    attachment_url: str | None = None
    sender_name: str | None = None # To easily display who sent it
