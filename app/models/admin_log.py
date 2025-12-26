from datetime import datetime
import uuid
from sqlmodel import SQLModel, Field

class AdminLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admin_id: uuid.UUID
    action: str
    target_id: str
    target_model: str
    ip_address: str | None = None
    details: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
