import uuid
from pydantic import EmailStr
from sqlmodel import SQLModel
from app.models.user import UserBase

class LoginRequest(SQLModel):
    """
    Schema for user login request.
    """
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "johndoe@example.com",
                "password": "securepassword123"
            }
        }
    }

class GoogleLoginRequest(SQLModel):
    """
    Schema for Google OAuth2 login.
    """
    token: str

class AppleLoginRequest(SQLModel):
    """
    Schema for Apple OAuth2 login.
    """
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

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "johndoe@example.com",
                "password": "securepassword123",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+1234567890",
                "referral_code": "REF123"
            }
        }
    }

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
