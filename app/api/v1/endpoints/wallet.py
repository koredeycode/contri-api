from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.wallet import Wallet, BankAccount, Card
from app.schemas.wallet import WalletRead, BankAccountCreate, BankAccountRead, CardCreate, CardRead
from app.schemas.response import APIResponse
from app.core.rate_limit import limiter

router = APIRouter()

@router.get("/", response_model=APIResponse[WalletRead])
@limiter.limit("20/minute")
async def get_wallet(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get current user's wallet details.
    
    Creates a wallet if one does not exist for the user.
    """
    query = select(Wallet).where(Wallet.user_id == current_user.id)
    result = await session.execute(query)
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        # Create wallet if it doesn't exist
        wallet = Wallet(user_id=current_user.id)
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)
        
    return APIResponse(message="Wallet details retrieved", data=wallet)

@router.post("/deposit", response_model=APIResponse[dict])
@limiter.limit("10/minute")
async def deposit_funds(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Initiate a deposit transaction (Mock implementation).
    """
    return APIResponse(message="Deposit initiated", data={"user": current_user.email})

@router.post("/withdraw", response_model=APIResponse[dict])
@limiter.limit("10/minute")
async def withdraw_funds(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Initiate a withdrawal transaction (Mock implementation).
    """
    return APIResponse(message="Withdrawal initiated", data={"user": current_user.email})

@router.get("/banks", response_model=APIResponse[List[BankAccountRead]])
@limiter.limit("10/minute")
async def get_banks(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    List all linked bank accounts.
    """
    query = select(BankAccount).where(BankAccount.user_id == current_user.id)
    result = await session.execute(query)
    return APIResponse(message="Bank accounts retrieved", data=result.scalars().all())

@router.post("/banks", response_model=APIResponse[BankAccountRead])
@limiter.limit("10/minute")
async def link_bank(
    request: Request,
    bank_in: BankAccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Link a new bank account.
    """
    bank = BankAccount.model_validate(bank_in, update={"user_id": current_user.id})
    session.add(bank)
    await session.commit()
    await session.refresh(bank)
    return APIResponse(message="Bank account added successfully", data=bank)

@router.get("/cards", response_model=APIResponse[List[CardRead]])
@limiter.limit("10/minute")
async def get_cards(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    List all linked cards.
    """
    query = select(Card).where(Card.user_id == current_user.id)
    result = await session.execute(query)
    return APIResponse(message="Cards retrieved", data=result.scalars().all())

@router.post("/cards", response_model=APIResponse[CardRead])
@limiter.limit("10/minute")
async def link_card(
    request: Request,
    card_in: CardCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Link a new debit/credit card.
    """
    card = Card.model_validate(card_in, update={"user_id": current_user.id})
    session.add(card)
    await session.commit()
    await session.refresh(card)
    return APIResponse(message="Card added successfully", data=card)
