import hmac
import hashlib
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

class PaystackService:
    BASE_URL = "https://api.paystack.co"

    @staticmethod
    def get_headers() -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def verify_signature(data: bytes, signature: str) -> bool:
        """
        Verify the Paystack webhook signature.
        """
        if not settings.PAYSTACK_SECRET_KEY:
            return False
            
        hash_object = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            msg=data,
            digestmod=hashlib.sha512
        )
        expected_signature = hash_object.hexdigest()
        return hmac.compare_digest(expected_signature, signature)

    @staticmethod
    async def initialize_transaction(
        email: str, 
        amount_kobo: int, 
        reference: str, 
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initialize a Paystack transaction.
        """
        url = f"{PaystackService.BASE_URL}/transaction/initialize"
        payload = {
            "email": email,
            "amount": amount_kobo,
            "reference": reference,
            "metadata": metadata or {},
        }
        if callback_url:
            payload["callback_url"] = callback_url

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=PaystackService.get_headers())
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def verify_transaction(reference: str) -> Dict[str, Any]:
        """
        Verify a transaction by reference.
        """
        url = f"{PaystackService.BASE_URL}/transaction/verify/{reference}"
        
        async with httpx.AsyncClient() as client:
            # Check for the key explicitly to avoid errors if not configured in dev
            if not settings.PAYSTACK_SECRET_KEY:
               # Return mock data for dev if no key - though this should ideally fail or be handled carefully
               # For now, let's assume keys are present or let it crash to signal config error
               pass
               
            response = await client.get(url, headers=PaystackService.get_headers())
            response.raise_for_status()
            return response.json()
