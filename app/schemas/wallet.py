from decimal import Decimal
import uuid
from sqlmodel import SQLModel
from app.models.wallet import Wallet, BankAccount, Card

# Wallet Schemas
class WalletRead(SQLModel):
    """
    Schema for reading wallet details.
    """
    id: uuid.UUID
    balance: Decimal
    currency: str

class WalletUpdate(SQLModel):
    """
    Schema for updating wallet balance (internal use mostly).
    """
    balance: Decimal | None = None

# Bank Account Schemas
class BankAccountCreate(SQLModel):
    """
    Schema for linking a new bank account.
    """
    bank_name: str
    account_number: str
    account_name: str
    bank_code: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "bank_name": "First Bank",
                "account_number": "1234567890",
                "account_name": "John Doe",
                "bank_code": "011"
            }
        }
    }

class BankAccountRead(BankAccountCreate):
    """
    Schema for reading bank account details.
    """
    id: uuid.UUID
    is_primary: bool
    status: str

# Card Schemas
class CardCreate(SQLModel):
    """
    Schema for linking a new card.
    """
    last4: str
    brand: str
    expiry_month: int
    expiry_year: int
    auth_token: str
    signature: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "last4": "4242",
                "brand": "Visa",
                "expiry_month": 12,
                "expiry_year": 2025,
                "auth_token": "tok_12345",
                "signature": "sig_abc123"
            }
        }
    }

class CardRead(CardCreate):
    """
    Schema for reading card details.
    """
    id: uuid.UUID
