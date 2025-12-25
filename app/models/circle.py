import uuid
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field

class Circle(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    amount: Decimal = Field(max_digits=20, decimal_places=2)
    frequency: str # weekly, monthly
    cycle_start_date: datetime
    status: str = Field(default="active")
    invite_code: str = Field(unique=True)

class CircleMember(SQLModel, table=True):
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
    circle_id: uuid.UUID = Field(foreign_key="circle.id", primary_key=True)
    payout_order: int # 1, 2, 3...
    role: str = Field(default="member") # host, member

class Contribution(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    circle_id: uuid.UUID = Field(foreign_key="circle.id")
    user_id: uuid.UUID = Field(foreign_key="user.id")
    cycle_number: int
    amount: Decimal = Field(max_digits=20, decimal_places=2)
    status: str # paid, pending, late
    paid_at: datetime | None = None
