import asyncio
import logging
import uuid
import random
from datetime import datetime, timezone, timedelta
from faker import Faker

from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.wallet import Wallet, BankAccount, Card
from app.models.circle import Circle, CircleMember, Contribution
from app.models.transaction import Transaction
from app.models.notification import Notification
from app.models.chat import ChatMessage
from app.models.enums import TransactionType, TransactionStatus, ContributionStatus, CircleStatus
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
PASSWORD = "password123"
hashed_password = get_password_hash(PASSWORD)
fake = Faker()

def get_utc_now():
    """Returns a naive UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

async def seed_data():
    async with AsyncSessionLocal() as session:
        # 0. Clear Database
        logger.info("Clearing database...")
        await session.execute(text('TRUNCATE TABLE "user", wallet, bankaccount, card, circle, circlemember, contribution, transaction, notification, chatmessage RESTART IDENTITY CASCADE'))
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

        # Generate 50 Random Users
        extra_users = []
        for i in range(50):
            profile = fake.simple_profile()
            first_name = profile['name'].split()[0]
            last_name = profile['name'].split()[-1]
            email = f"user{i}_{profile['username']}@example.com"
            
            user = User(
                email=email,
                hashed_password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                role="user",
                referral_code=f"REF{uuid.uuid4().hex[:6].upper()}",
                phone_number=f"+2348{str(random.randint(10000000, 99999999))}",
                is_verified=True,
                is_active=True
            )
            session.add(user)
            users.append(user)
            extra_users.append(user)
        
        await session.commit()
        for u in users:
            await session.refresh(u)
        
        logger.info(f"Created {len(users)} users.")

        # 2. Wallets, Banks & Cards
        logger.info("Creating financial data...")
        banks_list = [
            ("Access Bank", "044"), ("GTBank", "058"), ("Zenith Bank", "057"), ("UBA", "033"), ("First Bank", "011"), ("Kuda Bank", "090267")
        ]
        
        for i, user in enumerate(users):
            if user.role == "admin":
                balance = 100_000_000
            elif user == john:
                balance = 15_000_000
            elif user == jane:
                balance = 7_500_000
            else:
                balance = random.randint(5_000_000, 50_000_000)

            wallet = Wallet(
                user_id=user.id,
                balance=balance,
                currency="NGN"
            )
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)

            deposit_txn = Transaction(
                wallet_id=wallet.id,
                amount=balance,
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.SUCCESS,
                reference=f"DEP_{uuid.uuid4().hex[:12]}",
                description="Initial wallet funding",
                created_at=get_utc_now() - timedelta(days=60)
            )
            session.add(deposit_txn)

            num_banks = 1 if i % 3 != 0 else 2 
            files_banks = random.sample(banks_list, num_banks)
            
            for j, (b_name, b_code) in enumerate(files_banks):
                bank = BankAccount(
                    user_id=user.id,
                    bank_name=b_name,
                    account_number=f"012{str(random.randint(10000000, 99999999))}",
                    account_name=f"{user.first_name} {user.last_name}",
                    bank_code=b_code,
                    is_primary=(j == 0),
                    status="verified"
                )
                session.add(bank)

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
        # Keep static 3 circles for predictable testing
        circle_family = Circle(
            name="Family Saving",
            amount=2_000_000,
            frequency="monthly",
            cycle_start_date=get_utc_now() - timedelta(days=45),
            status=CircleStatus.ACTIVE,
            invite_code="FAM001",
            description="Saving for the rainy days.",
            target_members=5,
            payout_preference="fixed"
        )
        session.add(circle_family)
        await session.commit()
        await session.refresh(circle_family)

        fam_members = [john, jane, extra_users[0]] 
        for idx, member in enumerate(fam_members):
            cm = CircleMember(
                user_id=member.id,
                circle_id=circle_family.id,
                payout_order=idx + 1,
                role="host" if member == john else "member",
                join_date=get_utc_now() - timedelta(days=50)
            )
            session.add(cm)
        
        # Family Contributions
        for member in fam_members:
            c = Contribution(
                circle_id=circle_family.id,
                user_id=member.id,
                cycle_number=1,
                amount=circle_family.amount,
                status=ContributionStatus.PAID,
                paid_at=get_utc_now() - timedelta(days=40)
            )
            session.add(c)
            # Add transaction logic simplified for speed...

        circle_coworkers = Circle(
            name="Co-workers",
            amount=5_000_000,
            frequency="monthly",
            cycle_start_date=None,
            status=CircleStatus.PENDING,
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
                join_date=get_utc_now() - timedelta(hours=idx)
            )
            session.add(cm)

        circle_holiday = Circle(
            name="Holiday Fund 2024",
            amount=1_000_000,
            frequency="weekly",
            cycle_start_date=get_utc_now() - timedelta(days=100),
            status=CircleStatus.COMPLETED,
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
                join_date=get_utc_now() - timedelta(days=110)
            )
            session.add(cm)

        # Generate 15 Random Circles
        all_circles = [circle_family, circle_coworkers, circle_holiday]
        
        for i in range(15):
            host = random.choice(users)
            status = random.choice([CircleStatus.PENDING, CircleStatus.ACTIVE, CircleStatus.COMPLETED])
            amount = random.choice([500000, 1000000, 2000000, 5000000, 10000000]) # 5k - 100k
            
            cycle_start = None
            if status != CircleStatus.PENDING:
                cycle_start = get_utc_now() - timedelta(days=random.randint(10, 100))

            circle = Circle(
                name=f"{fake.word().capitalize()} Circle",
                amount=amount,
                frequency=random.choice(["weekly", "biweekly", "monthly"]),
                cycle_start_date=cycle_start,
                status=status,
                invite_code=uuid.uuid4().hex[:8].upper(),
                description=fake.sentence(),
                target_members=random.randint(3, 10),
                payout_preference=random.choice(["fixed", "random"])
            )
            session.add(circle)
            await session.commit() # Commit to get ID
            await session.refresh(circle)
            all_circles.append(circle)

            # Members
            num_members = random.randint(2, circle.target_members or 5)
            potential_members = [u for u in users if u != host]
            members = [host] + random.sample(potential_members, min(len(potential_members), num_members - 1))
            
            for m_idx, member in enumerate(members):
                cm = CircleMember(
                    user_id=member.id,
                    circle_id=circle.id,
                    payout_order=m_idx + 1,
                    role="host" if member == host else "member",
                    join_date=get_utc_now() - timedelta(days=random.randint(1, 30))
                )
                session.add(cm)
        
        await session.commit()
        logger.info(f"Created {len(all_circles)} total circles.")

        # 4. Chats (Heavy Generation)
        logger.info("Creating chat messages...")
        
        total_msgs = 0
        for circle in all_circles:
            # Query members for this circle
            res = await session.execute(text(f"SELECT user_id FROM circlemember WHERE circle_id = '{circle.id}'"))
            member_ids = [row[0] for row in res.fetchall()]
            
            num_msgs = random.randint(5, 50)
            
            for _ in range(num_msgs):
                sender_id = random.choice(member_ids)
                msg_content = fake.sentence()
                days_ago = random.randint(0, 30)
                
                msg = ChatMessage(
                    circle_id=circle.id,
                    user_id=sender_id,
                    content=msg_content,
                    timestamp=get_utc_now() - timedelta(days=days_ago, minutes=random.randint(0, 1440)),
                    message_type="text"
                )
                session.add(msg)
                total_msgs += 1
            
        await session.commit()
        logger.info(f"Created {total_msgs} chat messages.")

        # 5. Notifications
        logger.info("Creating notifications...")
        for user in users:
            for _ in range(random.randint(2, 5)):
                 n = Notification(
                    user_id=user.id,
                    title=fake.catch_phrase(),
                    body=fake.sentence(),
                    type="info",
                    is_read=random.choice([True, False]),
                    created_at=get_utc_now() - timedelta(days=random.randint(0, 10))
                )
                 session.add(n)
        
        await session.commit()
        logger.info("SEEDING COMPLETE! 🚀")

if __name__ == "__main__":
    asyncio.run(seed_data())
