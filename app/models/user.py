import uuid
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from pydantic import EmailStr

class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True)
    first_name: str
    last_name: str
    phone_number: str | None = None
    avatar_url: str | None = None
    is_active: bool = Field(default=True)
    role: str = Field(default="user")
    is_verified: bool = Field(default=False)
    social_provider: str | None = None
    social_id: str | None = None

class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    referral_code: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
