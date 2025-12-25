from datetime import datetime
from decimal import Decimal
import uuid
from sqlmodel import SQLModel

# Circle Schemas
class CircleBase(SQLModel):
    name: str
    amount: Decimal
    frequency: str
    cycle_start_date: datetime

class CircleCreate(CircleBase):
    pass

class CircleRead(CircleBase):
    id: uuid.UUID
    status: str
    invite_code: str

class CircleUpdate(SQLModel):
    name: str | None = None
    status: str | None = None

# Circle Member Schemas
class CircleMemberCreate(SQLModel):
    circle_id: uuid.UUID
    user_id: uuid.UUID
    role: str = "member"

class CircleMemberRead(CircleMemberCreate):
    payout_order: int

# Contribution Schemas
class ContributionRead(SQLModel):
    id: uuid.UUID
    circle_id: uuid.UUID
    user_id: uuid.UUID
    cycle_number: int
    amount: Decimal
    status: str
    paid_at: datetime | None
