from datetime import datetime
import uuid
from sqlmodel import SQLModel
from app.models.enums import CircleFrequency, CircleStatus, PayoutPreference, CircleRole, ContributionStatus

# Circle Schemas
class CircleBase(SQLModel):
    """
    Base Circle schema with shared properties.
    """
    name: str
    description: str | None = None
    amount: int
    frequency: CircleFrequency
    cycle_start_date: datetime | None = None
    target_members: int | None = None
    payout_preference: PayoutPreference = PayoutPreference.FIXED

class CircleCreate(CircleBase):
    """
    Schema for creating a new circle.
    """
    pass

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Family Savings",
                "description": "Saving for summer vacation",
                "amount": 5000000,
                "frequency": "monthly",
                "cycle_start_date": "2025-01-01T00:00:00Z",
                "target_members": 5,
                "payout_preference": "random"
            }
        }
    }

class CircleRead(CircleBase):
    """
    Schema for reading circle details.
    """
    id: uuid.UUID
    status: CircleStatus
    invite_code: str

class CircleUpdate(SQLModel):
    """
    Schema for updating circle details (e.g. name or status).
    """
    name: str | None = None
    description: str | None = None
    amount: int | None = None
    frequency: CircleFrequency | None = None
    target_members: int | None = None
    payout_preference: PayoutPreference | None = None
    status: CircleStatus | None = None

# Circle Member Schemas
class CircleMemberCreate(SQLModel):
    """
    Schema for adding a member to a circle.
    """
    circle_id: uuid.UUID
    user_id: uuid.UUID
    role: CircleRole = CircleRole.MEMBER

class CircleMemberRead(CircleMemberCreate):
    """
    Schema for reading circle member details.
    """
    payout_order: int

class CircleMemberReorder(SQLModel):
    """
    Schema for reordering members.
    """
    member_ids: list[uuid.UUID]

# Contribution Schemas
class ContributionRead(SQLModel):
    id: uuid.UUID
    circle_id: uuid.UUID
    user_id: uuid.UUID
    cycle_number: int
    amount: int
    status: ContributionStatus
    paid_at: datetime | None
