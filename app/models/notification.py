import uuid
from sqlmodel import SQLModel, Field

class Notification(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    title: str
    body: str
    type: str # action_required, info, success
    is_read: bool = Field(default=False)
    action_url: str | None = None # Deep link
    priority: str = Field(default="normal") # high, normal
