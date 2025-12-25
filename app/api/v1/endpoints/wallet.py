from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.wallet import Wallet, BankAccount, Card
from app.schemas.wallet import WalletRead, BankAccountCreate, BankAccountRead, CardCreate, CardRead

router = APIRouter()

@router.get("/", response_model=WalletRead)
async def get_wallet(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    query = select(Wallet).where(Wallet.user_id == current_user.id)
    result = await session.execute(query)
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        # Create wallet if it doesn't exist
        wallet = Wallet(user_id=current_user.id)
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)
        
    return wallet

@router.post("/deposit")
async def deposit_funds(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    return {"message": "Deposit initiated", "user": current_user.email}

@router.post("/withdraw")
async def withdraw_funds(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    return {"message": "Withdrawal initiated", "user": current_user.email}

@router.get("/banks", response_model=List[BankAccountRead])
async def get_banks(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    query = select(BankAccount).where(BankAccount.user_id == current_user.id)
    result = await session.execute(query)
    return result.scalars().all()

@router.post("/banks", response_model=BankAccountRead)
async def link_bank(
    bank_in: BankAccountCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    bank = BankAccount.model_validate(bank_in, update={"user_id": current_user.id})
    session.add(bank)
    await session.commit()
    await session.refresh(bank)
    return bank

@router.get("/cards", response_model=List[CardRead])
async def get_cards(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    query = select(Card).where(Card.user_id == current_user.id)
    result = await session.execute(query)
    return result.scalars().all()

@router.post("/cards", response_model=CardRead)
async def link_card(
    card_in: CardCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    card = Card.model_validate(card_in, update={"user_id": current_user.id})
    session.add(card)
    await session.commit()
    await session.refresh(card)
    return card
