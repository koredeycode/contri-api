from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.wallet import Wallet, BankAccount, Card
from app.schemas.wallet import WalletRead, BankAccountCreate, BankAccountRead, CardCreate, CardRead
from app.schemas.response import APIResponse

router = APIRouter()

@router.get("/", response_model=APIResponse[WalletRead])
async def get_wallet(
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
async def deposit_funds(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Initiate a deposit transaction (Mock implementation).
    """
    return APIResponse(message="Deposit initiated", data={"user": current_user.email})

@router.post("/withdraw", response_model=APIResponse[dict])
async def withdraw_funds(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Initiate a withdrawal transaction (Mock implementation).
    """
    return APIResponse(message="Withdrawal initiated", data={"user": current_user.email})

@router.get("/banks", response_model=APIResponse[List[BankAccountRead]])
async def get_banks(
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
async def link_bank(
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
async def get_cards(
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
async def link_card(
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
