import uuid
from decimal import Decimal
from sqlmodel import SQLModel, Field

class Wallet(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    balance: Decimal = Field(default=0.00, max_digits=20, decimal_places=2)
    currency: str = Field(default="NGN")

class BankAccount(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    bank_name: str
    account_number: str
    account_name: str
    bank_code: str
    is_primary: bool = Field(default=False)
    status: str = Field(default="pending") # pending, verified

class Card(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    last4: str
    brand: str # visa, mastercard
    expiry_month: int
    expiry_year: int
    auth_token: str # Token from payment provider (Paystack/Stripe)
    signature: str # To prevent duplicate cards
