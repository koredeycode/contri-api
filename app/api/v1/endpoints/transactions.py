from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.api import deps
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.enums import TransactionType, TransactionStatus
from app.services.paystack import PaystackService
import uuid
from pydantic import BaseModel, Field

from app.schemas.response import APIResponse

router = APIRouter()

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to deposit in main currency units (e.g., Naira)")

@router.post("/deposit")
async def initiate_deposit(
    deposit: DepositRequest,
    current_user: Annotated[User, Depends(deps.get_current_user)],
    session: Annotated[AsyncSession, Depends(deps.get_db)]
):
    """
    Initiate a wallet deposit via Paystack.
    """
    # 1. Get user wallet
    result = await session.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalars().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # 2. Convert to cents/kobo
    amount_kobo = int(deposit.amount * 100)
    reference = f"txn_{uuid.uuid4().hex}"

    # 3. Create Transaction Record
    trx = Transaction(
        wallet_id=wallet.id,
        amount=amount_kobo,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.PENDING,
        reference=reference,
        description=f"Wallet deposit of {deposit.amount}",
        txn_metadata={"user_id": str(current_user.id)}
    )
    session.add(trx)
    await session.commit()
    await session.refresh(trx)

    # 4. Initialize Paystack
    try:
        paystack_response = await PaystackService.initialize_transaction(
            email=current_user.email,
            amount_kobo=amount_kobo,
            reference=reference,
            metadata={"transaction_id": str(trx.id)}
        )
        
        return {
            "status": "success",
            "message": "Deposit initiated",
            "authorization_url": paystack_response["data"]["authorization_url"],
            "access_code": paystack_response["data"]["access_code"],
            "reference": reference
        }
    except Exception as e:
        trx.status = TransactionStatus.FAILED
        session.add(trx)
        await session.commit()
        raise HTTPException(status_code=400, detail=f"Failed to initiate payment: {str(e)}")

@router.get("/", response_model=APIResponse[list[Transaction]])
async def get_transactions(
    session: Annotated[AsyncSession, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: int = 0,
    limit: int = 50,
):
    """
    Get user transactions.
    """
    result = await session.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalars().first()
    if not wallet:
        return APIResponse(message="Transactions retrieved", data=[])

    result = await session.execute(
        select(Transaction).where(Transaction.wallet_id == wallet.id)
        .offset(skip).limit(limit).order_by(Transaction.created_at.desc())
    )
    transactions = result.scalars().all()
    return APIResponse(message="Transactions retrieved", data=transactions)
