from typing import Annotated
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.api import deps
from app.services.paystack import PaystackService
from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.models.enums import TransactionStatus, TransactionType
import json
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def paystack_webhook(request: Request, session: Annotated[AsyncSession, Depends(deps.get_db)]):
    """
    Handle Paystack webhooks.
    """
    # Verify signature
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No signature provided")
    
    body = await request.body()
    if not PaystackService.verify_signature(body, signature):
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    try:
        event_data = json.loads(body)
        event = event_data.get("event")
        data = event_data.get("data", {})
        
        if event == "charge.success":
            reference = data.get("reference")
            
            # Find the transaction
            result = await session.execute(select(Transaction).where(Transaction.reference == reference))
            transaction = result.scalars().first()
            
            if not transaction:
                logger.error(f"Transaction not found for reference: {reference}")
                return {"status": "ignored", "reason": "transaction_not_found"}
            
            # Idempotency check
            if transaction.status == TransactionStatus.SUCCESS:
                return {"status": "ignored", "reason": "already_processed"}
            
            # Verify amount matches (Paystack sends kobo)
            paid_amount = data.get("amount")
            if paid_amount != transaction.amount:
                 logger.error(f"Amount mismatch for {reference}. Expected {transaction.amount}, got {paid_amount}")
                 transaction.status = TransactionStatus.FAILED
                 transaction.txn_metadata = {**transaction.txn_metadata, "error": "amount_mismatch", "paid": paid_amount}
                 session.add(transaction)
                 await session.commit()
                 return {"status": "error", "message": "Amount mismatch"}

            # Update Transaction
            transaction.status = TransactionStatus.SUCCESS
            transaction.provider_reference = str(data.get("id"))
            transaction.updated_at = datetime.utcnow()
            
            # Credit Wallet
            wallet = await session.get(Wallet, transaction.wallet_id)
            if wallet:
                wallet.balance += transaction.amount
                session.add(wallet)
            
            session.add(transaction)
            await session.commit()
            
            logger.info(f"Transaction {reference} processed successfully")
            return {"status": "success"}
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "ignored"}
