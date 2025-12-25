import uuid
from pydantic import EmailStr
from sqlmodel import SQLModel
from app.models.user import UserBase

class UserCreate(UserBase):
    password: str
    referral_code: str | None = None # Optional for signup

class UserRead(UserBase):
    id: uuid.UUID
    referral_code: str

class UserUpdate(SQLModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    phone_number: str | None = None
    avatar_url: str | None = None
