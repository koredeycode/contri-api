import asyncio
import logging
import uuid
import random
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from sqlalchemy import text
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.wallet import Wallet, BankAccount, Card
from app.models.circle import Circle, CircleMember, Contribution
from app.models.notification import Notification
from app.models.chat import ChatMessage
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
PASSWORD = "password123"
hashed_password = get_password_hash(PASSWORD)

async def seed_data():
    async with AsyncSessionLocal() as session:
        # 0. Clear Database
        logger.info("Clearing database...")
        await session.execute(text('TRUNCATE TABLE "user", wallet, bankaccount, card, circle, circlemember, contribution, notification, chatmessage RESTART IDENTITY CASCADE'))
        await session.commit()
        logger.info("Database cleared.")

        # 1. Create Users
        logger.info("Creating users...")
        users = []
        
        # Admin
        admin = User(
            email="admin@example.com",
            hashed_password=hashed_password,
            first_name="Admin",
            last_name="User",
            role="admin",
            referral_code="ADMIN001",
            phone_number="+2348000000000",
            is_verified=True,
            is_active=True
        )
        session.add(admin)
        users.append(admin)

        # Core Users (John & Jane)
        john = User(
            email="john.doe@example.com",
            hashed_password=hashed_password,
            first_name="John",
            last_name="Doe",
            role="user",
            referral_code="JOHND001",
            phone_number="+2348000000001",
            is_verified=True,
            is_active=True
        )
        session.add(john)
        users.append(john)

        jane = User(
            email="jane.smith@example.com",
            hashed_password=hashed_password,
            first_name="Jane",
            last_name="Smith",
            role="user",
            referral_code="JANES001",
            phone_number="+2348000000002",
            is_verified=True,
            is_active=True
        )
        session.add(jane)
        users.append(jane)

        # Additional Random Users
        extra_users = []
        names = [("Michael", "Brown"), ("Emily", "Davis"), ("David", "Wilson"), ("Sarah", "Taylor"), ("Chris", "Anderson")]
        for i, (first, last) in enumerate(names):
            user = User(
                email=f"{first.lower()}.{last.lower()}@example.com",
                hashed_password=hashed_password,
                first_name=first,
                last_name=last,
                role="user",
                referral_code=f"{first.upper()[:3]}{last.upper()[:1]}00{i+1}",
                phone_number=f"+234800000000{i+3}",
                is_verified=True,
                is_active=True
            )
            session.add(user)
            users.append(user)
            extra_users.append(user)
        
        await session.commit()
        # Refresh to get IDs
        for u in users:
            await session.refresh(u)
        
        logger.info(f"Created {len(users)} users.")

        # 2. Wallets, Banks & Cards (For ALL Users)
        logger.info("Creating financial data for all users...")
        banks_list = [
            ("Access Bank", "044"), ("GTBank", "058"), ("Zenith Bank", "057"), ("UBA", "033"), ("First Bank", "011"), ("Kuda Bank", "090267")
        ]
        
        for i, user in enumerate(users):
            # Wallet
            # Admin gets more, John/Jane get specific, others get random
            if user.role == "admin":
                balance = Decimal("1000000.00")
            elif user == john:
                balance = Decimal("150000.00")
            elif user == jane:
                balance = Decimal("75000.00")
            else:
                balance = Decimal(random.randint(20000, 100000))

            wallet = Wallet(
                user_id=user.id,
                balance=balance,
                currency="NGN"
            )
            session.add(wallet)

            # Bank Accounts - Everyone gets at least one
            # Give some users multiple banks
            num_banks = 1 if i % 3 != 0 else 2 
            files_banks = random.sample(banks_list, num_banks)
            
            for j, (b_name, b_code) in enumerate(files_banks):
                bank = BankAccount(
                    user_id=user.id,
                    bank_name=b_name,
                    account_number=f"012{user.phone_number[-4:]}{j}{i}", # Generating semi-unique numbers
                    account_name=f"{user.first_name} {user.last_name}",
                    bank_code=b_code,
                    is_primary=(j == 0),
                    status="verified"
                )
                session.add(bank)

            # Cards - Everyone gets at least one
            card_brand = "visa" if i % 2 == 0 else "mastercard"
            card = Card(
                user_id=user.id,
                last4=f"{random.randint(1000, 9999)}",
                brand=card_brand,
                expiry_month=random.randint(1, 12),
                expiry_year=random.randint(2025, 2028),
                auth_token=f"AUTH_{user.email}_{i}",
                signature=f"SIG_{user.email}_{i}"
            )
            session.add(card)

        await session.commit()

        # 3. Circles
        logger.info("Creating circles...")
        
        # A. Active Circle: "Family Saving" (John Host)
        circle_family = Circle(
            name="Family Saving",
            amount=Decimal("20000.00"),
            frequency="monthly",
            cycle_start_date=(datetime.now(timezone.utc) - timedelta(days=45)).replace(tzinfo=None),
            status="active",
            invite_code="FAM001",
            description="Saving for the rainy days.",
            target_members=5,
            payout_preference="fixed"
        )
        session.add(circle_family)
        await session.commit()
        await session.refresh(circle_family)

        # Members for Family Circle
        fam_members = [john, jane, extra_users[0]] # 3 members
        for idx, member in enumerate(fam_members):
            cm = CircleMember(
                user_id=member.id,
                circle_id=circle_family.id,
                payout_order=idx + 1,
                role="host" if member == john else "member",
                join_date=(datetime.now(timezone.utc) - timedelta(days=50)).replace(tzinfo=None)
            )
            session.add(cm)
        
        # Contributions for Family Circle
        # Cycle 1
        for member in fam_members:
            c = Contribution(
                circle_id=circle_family.id,
                user_id=member.id,
                cycle_number=1,
                amount=circle_family.amount,
                status="paid",
                paid_at=(datetime.now(timezone.utc) - timedelta(days=40)).replace(tzinfo=None)
            )
            session.add(c)
        
        # Cycle 2
        for member in fam_members:
            status = "pending"
            paid_at = None
            if member in [john, jane]:
                status = "paid"
                paid_at = (datetime.now(timezone.utc) - timedelta(days=5)).replace(tzinfo=None)
            
            c = Contribution(
                circle_id=circle_family.id,
                user_id=member.id,
                cycle_number=2,
                amount=circle_family.amount,
                status=status,
                paid_at=paid_at
            )
            session.add(c)

        # B. Pending Circle: "Co-workers" (Jane Host)
        circle_coworkers = Circle(
            name="Co-workers",
            amount=Decimal("50000.00"),
            frequency="monthly",
            cycle_start_date=None,
            status="pending",
            invite_code="WORK01",
            description="Office monthly thrift",
            target_members=10,
            payout_preference="random"
        )
        session.add(circle_coworkers)
        await session.commit()
        await session.refresh(circle_coworkers)

        coworker_members = [jane, extra_users[1], extra_users[2], extra_users[3]]
        for idx, member in enumerate(coworker_members):
            cm = CircleMember(
                user_id=member.id,
                circle_id=circle_coworkers.id,
                payout_order=idx + 1,
                role="host" if member == jane else "member",
                join_date=(datetime.now(timezone.utc) - timedelta(hours=idx)).replace(tzinfo=None)
            )
            session.add(cm)

        # C. Completed Circle: "Holiday Fund" (Admin Host)
        circle_holiday = Circle(
            name="Holiday Fund 2024",
            amount=Decimal("10000.00"),
            frequency="weekly",
            cycle_start_date=(datetime.now(timezone.utc) - timedelta(days=100)).replace(tzinfo=None),
            status="completed",
            invite_code="HOL24",
            description="Saved for Dec 2024 Holidays",
            target_members=3,
            payout_preference="fixed"
        )
        session.add(circle_holiday)
        await session.commit()
        await session.refresh(circle_holiday)

        hol_members = [admin, john, jane]
        for idx, member in enumerate(hol_members):
            cm = CircleMember(
                user_id=member.id,
                circle_id=circle_holiday.id,
                payout_order=idx + 1,
                role="host" if member == admin else "member",
                join_date=(datetime.now(timezone.utc) - timedelta(days=110)).replace(tzinfo=None)
            )
            session.add(cm)
        
        # Generate 4 completed cycles
        for cycle in range(1, 5):
            for member in hol_members:
                c = Contribution(
                    circle_id=circle_holiday.id,
                    user_id=member.id,
                    cycle_number=cycle,
                    amount=circle_holiday.amount,
                    status="paid",
                    paid_at=(datetime.now(timezone.utc) - timedelta(days=100 - (cycle * 7))).replace(tzinfo=None)
                )
                session.add(c)
        
        await session.commit()

        # 4. Chat Messages
        logger.info("Creating chat messages...")
        
        # Family Circle Chat
        msgs_fam = [
            (john, "Welcome to the family circle everyone!", 44),
            (jane, "Thanks John, happy to be starting this.", 43),
            (extra_users[0], "Let's save!", 42),
            (john, "Just sent my payment for this month.", 5),
            (jane, "Received notification, I've paid mine too.", 4),
        ]
        
        for user, content, days_ago in msgs_fam:
            msg = ChatMessage(
                circle_id=circle_family.id,
                user_id=user.id,
                content=content,
                timestamp=(datetime.now(timezone.utc) - timedelta(days=days_ago)).replace(tzinfo=None),
                message_type="text"
            )
            session.add(msg)

        # Co-workers Circle Chat
        msgs_work = [
            (jane, "Hi team, invite sent to everyone.", 1),
            (extra_users[1], "Got it, joined!", 0),
            (extra_users[2], "What's the payout order?", 0),
            (jane, "Randomized for now, we can discuss.", 0),
        ]

        for user, content, days_ago in msgs_work:
            msg = ChatMessage(
                circle_id=circle_coworkers.id,
                user_id=user.id,
                content=content,
                timestamp=(datetime.now(timezone.utc) - timedelta(days=days_ago)).replace(tzinfo=None),
                message_type="text"
            )
            session.add(msg)

        await session.commit()

        # 5. Notifications (More comprehensive)
        logger.info("Creating comprehensive notifications...")
        
        # System-wide notifications for everyone
        global_notifs = [
            ("Welcome to Contri!", "We're glad to have you here. Set up your wallet to start.", "info", "high"),
            ("New Feature Alert", "You can now chat with your circle members directly in the app!", "info", "normal"),
            ("Security Update", "Please enable 2FA for enhanced security.", "info", "normal")
        ]

        for user in users:
            for title, body, n_type, priority in global_notifs:
                n = Notification(
                    user_id=user.id,
                    title=title,
                    body=body,
                    type=n_type,
                    is_read=random.choice([True, False]),
                    priority=priority
                )
                session.add(n)

        # Specific notifications
        # John - Activity
        session.add(Notification(
            user_id=john.id,
            title="Contribution Received",
            body="Jane just made a contribution to Family Saving.",
            type="success",
            is_read=False
        ))
        
        # Jane - Invite
        session.add(Notification(
            user_id=jane.id,
            title="Circle Invitation",
            body="John invited you to join 'Family Saving'.",
            type="action_required",
            action_url=f"/circle/{circle_family.id}",
            is_read=True
        ))

        # Random user - Payment Due
        session.add(Notification(
            user_id=extra_users[0].id,
            title="Payment Reminder",
            body="Your contribution for Family Saving is due in 3 days.",
            type="warning",
            priority="high",
            is_read=False
        ))

        await session.commit()
        logger.info("Notifications created.")
        
        logger.info("SEEDING COMPLETE! 🚀")

if __name__ == "__main__":
    asyncio.run(seed_data())
