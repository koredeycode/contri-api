import uuid
from datetime import datetime
from typing import Optional, Any
from sqlmodel import SQLModel, Field, JSON, Column
from sqlalchemy import BigInteger
from .enums import TransactionType, TransactionStatus

class Transaction(SQLModel, table=True):
    """
    Transaction model for tracking all financial movements.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Unique identifier for the transaction")
    wallet_id: uuid.UUID = Field(foreign_key="wallet.id", description="ID of the wallet involved")
    amount: int = Field(sa_type=BigInteger, description="Amount in kobo/cents")
    type: TransactionType = Field(description="Type of transaction (deposit, withdrawal, etc.)")
    status: TransactionStatus = Field(default=TransactionStatus.PENDING, description="Status of the transaction")
    reference: str = Field(unique=True, index=True, description="Unique transaction reference")
    provider_reference: Optional[str] = Field(default=None, description="Payment provider's reference (e.g., Paystack)")
    description: str = Field(description="Description of the transaction")
    txn_metadata: Optional[dict[str, Any]] = Field(default={}, sa_column=Column(JSON), description="Additional metadata")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
