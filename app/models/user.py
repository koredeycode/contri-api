import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import EmailStr

class UserBase(SQLModel):
    """
    Base User model containing shared attributes.
    """
    email: EmailStr = Field(unique=True, index=True, description="User's email address")
    first_name: str = Field(description="User's first name")
    last_name: str = Field(description="User's last name")
    phone_number: str | None = Field(default=None, description="User's phone number")
    avatar_url: str | None = Field(default=None, description="URL to user's avatar image")
    is_active: bool = Field(default=True, description="Whether the user account is active")
    role: str = Field(default="user", description="User role (e.g., 'user', 'admin')")
    is_verified: bool = Field(default=False, description="Whether the user is verified")
    social_provider: str | None = Field(default=None, description="Social auth provider name (e.g., 'google', 'apple')")
    social_id: str | None = Field(default=None, description="Unique ID from the social provider")

class User(UserBase, table=True):
    """
    User database model.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the user")
    hashed_password: str = Field(description="Hashed version of the user's password")
    referral_code: str = Field(unique=True, index=True, description="Unique referral code for invitations")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the user was created")
