from decimal import Decimal
import uuid
from sqlmodel import SQLModel
from app.models.wallet import Wallet, BankAccount, Card

# Wallet Schemas
class WalletRead(SQLModel):
    id: uuid.UUID
    balance: Decimal
    currency: str

class WalletUpdate(SQLModel):
    balance: Decimal | None = None

# Bank Account Schemas
class BankAccountCreate(SQLModel):
    bank_name: str
    account_number: str
    account_name: str
    bank_code: str

class BankAccountRead(BankAccountCreate):
    id: uuid.UUID
    is_primary: bool
    status: str

# Card Schemas
class CardCreate(SQLModel):
    last4: str
    brand: str
    expiry_month: int
    expiry_year: int
    auth_token: str
    signature: str

class CardRead(CardCreate):
    id: uuid.UUID
