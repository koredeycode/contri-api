import uuid
from decimal import Decimal
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger

class Wallet(SQLModel, table=True):
    """
    User wallet model.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the wallet")
    user_id: uuid.UUID = Field(foreign_key="user.id", description="ID of the wallet owner")
    balance: int = Field(default=0, sa_type=BigInteger, description="Current wallet balance in kobo/cents")
    currency: str = Field(default="NGN", description="Currency code (e.g., 'NGN')")

class BankAccount(SQLModel, table=True):
    """
    User bank account model for withdrawals.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the bank account")
    user_id: uuid.UUID = Field(foreign_key="user.id", description="ID of the bank account owner")
    bank_name: str = Field(description="Name of the bank")
    account_number: str = Field(description="Bank account number")
    account_name: str = Field(description="Name on the bank account")
    bank_code: str = Field(description="Bank code for transfers")
    is_primary: bool = Field(default=False, description="Whether this is the primary bank account")
    status: str = Field(default="pending", description="Verification status (e.g., 'pending', 'verified')")

class Card(SQLModel, table=True):
    """
    User linked card model for deposits.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the card")
    user_id: uuid.UUID = Field(foreign_key="user.id", description="ID of the card owner")
    last4: str = Field(description="Last 4 digits of the card")
    brand: str = Field(description="Card brand (e.g., 'visa', 'mastercard')")
    expiry_month: int = Field(description="Card expiry month")
    expiry_year: int = Field(description="Card expiry year")
    auth_token: str = Field(description="Token from payment provider (Paystack/Stripe) for recurring charges")
    signature: str = Field(description="Signature to prevent duplicate card addition")
