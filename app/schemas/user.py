import uuid
from pydantic import EmailStr
from sqlmodel import SQLModel
from app.models.user import UserBase

class LoginRequest(SQLModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(SQLModel):
    token: str

class AppleLoginRequest(SQLModel):
    token: str
    first_name: str | None = None
    last_name: str | None = None

class UserCreate(SQLModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone_number: str | None = None
    referral_code: str | None = None

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
