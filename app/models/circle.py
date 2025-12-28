import uuid
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger
from app.models.enums import CircleFrequency, CircleStatus, PayoutPreference, CircleRole, ContributionStatus

class Circle(SQLModel, table=True):
    """
    Circle (Ajo) model representing a group savings circle.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the circle")
    name: str = Field(description="Name of the circle")
    description: str | None = Field(default=None, description="Description of the circle goal")
    amount: int = Field(sa_type=BigInteger, description="Contribution amount per cycle in cents")
    frequency: CircleFrequency = Field(description="Frequency of contributions")
    cycle_start_date: datetime | None = Field(default=None, description="Start date of the circle cycle")
    status: CircleStatus = Field(default=CircleStatus.PENDING, description="Current status of the circle")
    invite_code: str = Field(unique=True, description="Unique code for inviting members")
    target_members: int | None = Field(default=None, description="Target number of members needed to start")
    payout_preference: PayoutPreference = Field(default=PayoutPreference.FIXED, description="Payout order preference")

class CircleMember(SQLModel, table=True):
    """
    Association model between User and Circle.
    """
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True, description="ID of the user")
    circle_id: uuid.UUID = Field(foreign_key="circle.id", primary_key=True, description="ID of the circle")
    payout_order: int = Field(description="Order in which the member receives the payout (1, 2, 3...)")
    role: CircleRole = Field(default=CircleRole.MEMBER, description="Role in the circle")
    join_date: datetime = Field(default_factory=datetime.now, description="Timestamp when the user joined the circle")

class Contribution(SQLModel, table=True):
    """
    Model tracking individual contributions to a circle.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the contribution")
    circle_id: uuid.UUID = Field(foreign_key="circle.id", description="ID of the circle")
    user_id: uuid.UUID = Field(foreign_key="user.id", description="ID of the user making the contribution")
    cycle_number: int = Field(description="The cycle number for this contribution")
    amount: int = Field(sa_type=BigInteger, description="Amount contributed in cents")
    status: ContributionStatus = Field(description="Status of the contribution")
    paid_at: datetime | None = Field(default=None, description="Timestamp when the contribution was paid")
