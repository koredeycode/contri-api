import asyncio
import logging
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from sqlalchemy.future import select
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.wallet import Wallet, BankAccount, Card
from app.models.circle import Circle, CircleMember, Contribution
from app.models.notification import Notification
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_data():
    async with AsyncSessionLocal() as session:
        # 0. Clear Database
        logger.info("Clearing database...")
        # Get table names from models to be safe, or hardcode known ones
        # Using TRUNCATE ... CASCADE to clear everything cleanly
        # Note: "user" is quoted because it's a keyword
        await session.execute(text('TRUNCATE TABLE "user", wallet, bankaccount, card, circle, circlemember, contribution, notification RESTART IDENTITY CASCADE'))
        await session.commit()
        logger.info("Database cleared.")

        # 1. Create Users
        users_data = [
            {
                "email": "admin@example.com",
                "password": "password123",
                "first_name": "Admin",
                "last_name": "User",
                "role": "admin",
                "referral_code": "ADMIN001",
                "phone_number": "+2348000000000"
            },
            {
                "email": "john.doe@example.com",
                "password": "password123",
                "first_name": "John",
                "last_name": "Doe",
                "role": "user",
                "referral_code": "JOHND001",
                "phone_number": "+2348000000001"
            },
            {
                "email": "jane.smith@example.com",
                "password": "password123",
                "first_name": "Jane",
                "last_name": "Smith",
                "role": "user",
                "referral_code": "JANES001",
                "phone_number": "+2348000000002"
            }
        ]

        users = {}
        for user_data in users_data:
            result = await session.execute(select(User).where(User.email == user_data["email"]))
            existing_user = result.scalars().first()
            
            if not existing_user:
                new_user = User(
                    email=user_data["email"],
                    hashed_password=get_password_hash(user_data["password"]),
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    role=user_data["role"],
                    referral_code=user_data["referral_code"],
                    phone_number=user_data["phone_number"],
                    is_verified=True,
                    is_active=True
                )
                session.add(new_user)
                users[user_data["email"]] = new_user
                logger.info(f"Created user: {user_data['email']}")
            else:
                users[user_data["email"]] = existing_user
                logger.info(f"User already exists: {user_data['email']}")
        
        await session.commit()
        # Refresh users to get IDs
        for email, user in users.items():
            await session.refresh(user)

        john = users["john.doe@example.com"]
        jane = users["jane.smith@example.com"]

        # 2. Create Wallets
        for user in users.values():
            result = await session.execute(select(Wallet).where(Wallet.user_id == user.id))
            if not result.scalars().first():
                wallet = Wallet(
                    user_id=user.id,
                    balance=Decimal("50000.00") if user.role == "user" else Decimal("0.00"),
                    currency="NGN"
                )
                session.add(wallet)
                logger.info(f"Created wallet for {user.email}")
        
        await session.commit()

        # 3. Create Bank Accounts & Cards (for John)
        result = await session.execute(select(BankAccount).where(BankAccount.user_id == john.id))
        if not result.scalars().first():
            bank = BankAccount(
                user_id=john.id,
                bank_name="Access Bank",
                account_number="0123456789",
                account_name="John Doe",
                bank_code="044",
                is_primary=True,
                status="verified"
            )
            session.add(bank)
            logger.info("Created bank account for John")

        result = await session.execute(select(Card).where(Card.user_id == john.id))
        if not result.scalars().first():
            card = Card(
                user_id=john.id,
                last4="4242",
                brand="visa",
                expiry_month=12,
                expiry_year=2025,
                auth_token="AUTH_TOKEN_123",
                signature="SIG_123"
            )
            session.add(card)
            logger.info("Created card for John")

        await session.commit()

        # 4. Create Circle (John hosts)
        circle_invite_code = "CIRCLE01"
        result = await session.execute(select(Circle).where(Circle.invite_code == circle_invite_code))
        circle = result.scalars().first()
        
        if not circle:
            circle = Circle(
                name="Family Saving",
                amount=Decimal("10000.00"),
                frequency="monthly",
                cycle_start_date=datetime.now(timezone.utc).replace(tzinfo=None),
                status="active",
                invite_code=circle_invite_code
            )
            session.add(circle)
            await session.commit()
            await session.refresh(circle)
            logger.info("Created circle 'Family Saving'")

            # Add Members
            # John is Host (Payout 1)
            member_john = CircleMember(
                user_id=john.id,
                circle_id=circle.id,
                payout_order=1,
                role="host"
            )
            session.add(member_john)

            # Jane is Member (Payout 2)
            member_jane = CircleMember(
                user_id=jane.id,
                circle_id=circle.id,
                payout_order=2,
                role="member"
            )
            session.add(member_jane)
            
            await session.commit()
            logger.info("Added members to circle")

            # 5. Create Contributions
            # Cycle 1: Both paid
            contribution1 = Contribution(
                circle_id=circle.id,
                user_id=john.id,
                cycle_number=1,
                amount=Decimal("10000.00"),
                status="paid",
                paid_at=(datetime.now(timezone.utc) - timedelta(days=30)).replace(tzinfo=None)
            )
            session.add(contribution1)

            contribution2 = Contribution(
                circle_id=circle.id,
                user_id=jane.id,
                cycle_number=1,
                amount=Decimal("10000.00"),
                status="paid",
                paid_at=(datetime.now(timezone.utc) - timedelta(days=29)).replace(tzinfo=None)
            )
            session.add(contribution2)

            # Cycle 2: John paid, Jane pending
            contribution3 = Contribution(
                circle_id=circle.id,
                user_id=john.id,
                cycle_number=2,
                amount=Decimal("10000.00"),
                status="paid",
                paid_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            session.add(contribution3)

            contribution4 = Contribution(
                circle_id=circle.id,
                user_id=jane.id,
                cycle_number=2,
                amount=Decimal("10000.00"),
                status="pending"
            )
            session.add(contribution4)

            await session.commit()
            logger.info("Created contributions")
        else:
            logger.info("Circle already exists")

    logger.info("Database seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
