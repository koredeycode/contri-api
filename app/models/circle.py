import uuid
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field

class Circle(SQLModel, table=True):
    """
    Circle (Ajo) model representing a group savings circle.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the circle")
    name: str = Field(description="Name of the circle")
    amount: Decimal = Field(max_digits=20, decimal_places=2, description="Contribution amount per cycle")
    frequency: str = Field(description="Frequency of contributions (e.g., 'weekly', 'monthly')")
    cycle_start_date: datetime = Field(description="Start date of the circle cycle")
    status: str = Field(default="active", description="Current status of the circle")
    invite_code: str = Field(unique=True, description="Unique code for inviting members")

class CircleMember(SQLModel, table=True):
    """
    Association model between User and Circle.
    """
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True, description="ID of the user")
    circle_id: uuid.UUID = Field(foreign_key="circle.id", primary_key=True, description="ID of the circle")
    payout_order: int = Field(description="Order in which the member receives the payout (1, 2, 3...)")
    role: str = Field(default="member", description="Role in the circle (e.g., 'host', 'member')")

class Contribution(SQLModel, table=True):
    """
    Model tracking individual contributions to a circle.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the contribution")
    circle_id: uuid.UUID = Field(foreign_key="circle.id", description="ID of the circle")
    user_id: uuid.UUID = Field(foreign_key="user.id", description="ID of the user making the contribution")
    cycle_number: int = Field(description="The cycle number for this contribution")
    amount: Decimal = Field(max_digits=20, decimal_places=2, description="Amount contributed")
    status: str = Field(description="Status of the contribution (e.g., 'paid', 'pending', 'late')")
    paid_at: datetime | None = Field(default=None, description="Timestamp when the contribution was paid")
