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
from app.models.enums import TransactionType, TransactionStatus, ContributionStatus, CircleStatus, CircleFrequency
from app.core.security import get_password_hash
from app.utils.financials import calculate_current_cycle

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
        # Order matters for constraints
        await session.execute(text('TRUNCATE TABLE "user", wallet, bankaccount, card, circle, circlemember, contribution, transaction, notification, chatmessage RESTART IDENTITY CASCADE'))
        await session.commit()
        logger.info("Database cleared.")

        # 1. Create Users (100+)
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

        # Generate 120 Random Users
        extra_users = []
        for i in range(120):
            profile = fake.simple_profile()
            first_name = profile['name'].split()[0]
            last_name = profile['name'].split()[-1]
            # Ensure unique email even if names collide
            email = f"user_{uuid.uuid4().hex[:6]}@example.com"
            
            user = User(
                email=email,
                hashed_password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                role="user",
                referral_code=f"REF{uuid.uuid4().hex[:8].upper()}",
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
        logger.info("Creating financial data (Wallets, Banks, Cards)...")
        banks_list = [
            ("Access Bank", "044"), ("GTBank", "058"), ("Zenith Bank", "057"), ("UBA", "033"), ("First Bank", "011"), ("Kuda Bank", "090267"), ("Opay", "999992")
        ]
        
        for i, user in enumerate(users):
            if user.role == "admin":
                balance = 500_000_000 # 5m
            elif user in [john, jane]:
                balance = 50_000_000 # 500k
            else:
                balance = random.randint(1_000_000, 100_000_000) # 10k - 1m

            wallet = Wallet(
                user_id=user.id,
                balance=balance,
                currency="NGN"
            )
            session.add(wallet)
            # Need ID for transactions
            await session.commit()
            await session.refresh(wallet)

            # Initial Deposit Transaction
            deposit_txn = Transaction(
                wallet_id=wallet.id,
                amount=balance,
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.SUCCESS,
                reference=f"DEP_{uuid.uuid4().hex[:12]}",
                description="Initial wallet funding",
                created_at=get_utc_now() - timedelta(days=random.randint(60, 365))
            )
            session.add(deposit_txn)

            # Bank Accounts
            num_banks = 1 if i % 5 != 0 else 2 
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

            # Cards
            card_brand = "visa" if i % 2 == 0 else "mastercard"
            card = Card(
                user_id=user.id,
                last4=f"{random.randint(1000, 9999)}",
                brand=card_brand,
                expiry_month=random.randint(1, 12),
                expiry_year=random.randint(2025, 2028),
                auth_token=f"AUTH_{user.id}_{i}",
                signature=f"SIG_{user.id}_{i}"
            )
            session.add(card)

        await session.commit()
        logger.info("Financial data created.")

        # 3. Circles (50+ Random Circles)
        logger.info("Creating Core & Random Circles...")
        
        # Pre-define types of circles for realism
        circle_configs = [
            {"name": "Family Savings", "amount": 500000, "freq": CircleFrequency.MONTHLY, "desc": "Monthly family contribution"},
            {"name": "Office Thrift", "amount": 2000000, "freq": CircleFrequency.MONTHLY, "desc": "Colleagues saving together"},
            {"name": "December Detty", "amount": 1000000, "freq": CircleFrequency.WEEKLY, "desc": "Saving for December rocks"},
            {"name": "Car Fund", "amount": 10000000, "freq": CircleFrequency.MONTHLY, "desc": "Saving to buy cars"},
            {"name": "Rent Ajo", "amount": 5000000, "freq": CircleFrequency.MONTHLY, "desc": "House rent savings"},
            {"name": "School Fees", "amount": 3000000, "freq": CircleFrequency.BIWEEKLY, "desc": "Kids school fees"},
            {"name": "Japa Plans", "amount": 20000000, "freq": CircleFrequency.MONTHLY, "desc": "Migration funds"},
            {"name": "Biz Capital", "amount": 5000000, "freq": CircleFrequency.WEEKLY, "desc": "Business capital rotation"}
        ]
        
        all_circles = []
        
        # Create 60 Circles
        for i in range(60):
            config = random.choice(circle_configs)
            host = random.choice(users)
            
            # Status distribution: 10% Pending, 70% Active, 20% Completed
            rand_val = random.random()
            if rand_val < 0.1:
                status = CircleStatus.PENDING
                cycle_start = None
                current_cycle = 0
            elif rand_val < 0.8:
                status = CircleStatus.ACTIVE
                # Started somewhere between 10 days and 6 months ago
                cycle_start = get_utc_now() - timedelta(days=random.randint(10, 180))
                # Cycle will be calc later
                current_cycle = 1 
            else:
                status = CircleStatus.COMPLETED
                cycle_start = get_utc_now() - timedelta(days=random.randint(200, 400))
                current_cycle = 0 # Or max

            circle = Circle(
                name=f"{config['name']} {i+1}",
                amount=config['amount'],
                frequency=config['freq'],
                cycle_start_date=cycle_start,
                status=status,
                invite_code=uuid.uuid4().hex[:8].upper(),
                description=config['desc'],
                target_members=random.randint(3, 12),
                payout_preference=random.choice(["fixed", "random"])
            )
            session.add(circle)
            await session.commit()
            await session.refresh(circle)
            
            # Create Circle Wallet (IMPORTANT fix)
            circle_wallet = Wallet(circle_id=circle.id, balance=0, currency="NGN")
            session.add(circle_wallet)
            await session.commit()
            await session.refresh(circle_wallet)
            
            all_circles.append(circle)

            # Add Members
            num_members = circle.target_members
            # If pending, maybe not full
            if status == CircleStatus.PENDING:
                num_members = random.randint(1, circle.target_members)
            
            potential_members = [u for u in users if u != host]
            members = [host] + random.sample(potential_members, min(len(potential_members), num_members - 1))
            
            # Create Member Records
            circle_members = []
            for m_idx, member in enumerate(members):
                join_date = get_utc_now() - timedelta(days=random.randint(10, 30))
                if cycle_start and cycle_start < join_date:
                     join_date = cycle_start - timedelta(days=random.randint(1, 5))

                cm = CircleMember(
                    user_id=member.id,
                    circle_id=circle.id,
                    payout_order=m_idx + 1,
                    role="host" if member == host else "member",
                    join_date=join_date
                )
                session.add(cm)
                circle_members.append(cm)
            
            await session.commit()

            # Simulate History for Active/Completed Circles
            if status in [CircleStatus.ACTIVE, CircleStatus.COMPLETED]:
                # Calculate what the cycle SHOULD be
                # We need to use the logic from utils, but let's approximate or reuse function if possible.
                # Since we imported calculate_current_cycle:
                real_current_cycle = calculate_current_cycle(circle)
                
                # If completed, simulate all cycles
                if status == CircleStatus.COMPLETED:
                     real_current_cycle = num_members + 1 # All done
                
                # Update circle current cycle
                circle.current_cycle = real_current_cycle
                if status == CircleStatus.COMPLETED:
                     circle.current_cycle = num_members # Cap at max
                elif status == CircleStatus.ACTIVE:
                     # Cap at num_members if random/fixed ensures single rotation, 
                     # but keep as is for multi-rotations if supported. 
                     # Assume single rotation for now:
                     if circle.current_cycle > num_members:
                          circle.current_cycle = num_members 
                          # Ideally status should flip to completed if automated
                
                session.add(circle)
                await session.commit()

                # Simulate Contributions & Transactions for Past Cycles
                # Iterate from Cycle 1 to current_cycle (inclusive if < current_cycle, or exclusive? 
                # usually current cycle is in progress, so simulate up to current_cycle - 1 fully, 
                # and maybe partial for current_cycle)
                
                loops = circle.current_cycle if status == CircleStatus.COMPLETED else circle.current_cycle
                
                for cycle_num in range(1, loops + 1):
                    # For each cycle, all members contribute
                    for member in members:
                        # Find member wallet
                        res = await session.execute(text(f"SELECT id, balance FROM wallet WHERE user_id = '{member.id}'"))
                        u_wallet = res.fetchone()
                        
                        # Contribution Record
                        contrib = Contribution(
                            circle_id=circle.id,
                            user_id=member.id,
                            cycle_number=cycle_num,
                            amount=circle.amount,
                            status=ContributionStatus.PAID,
                            paid_at=cycle_start + timedelta(weeks=cycle_num-1) # Approximate
                        )
                        session.add(contrib)
                        
                        # Transactions
                        # 1. User Debit
                        u_txn = Transaction(
                            wallet_id=u_wallet[0],
                            amount=circle.amount,
                            type=TransactionType.CONTRIBUTION,
                            status=TransactionStatus.SUCCESS,
                            reference=f"CONTRIB_{circle.id}_{member.id}_{cycle_num}",
                            description=f"Contribution to {circle.name} (Cycle {cycle_num})",
                            created_at=contrib.paid_at
                        )
                        session.add(u_txn)
                        
                        # 2. Circle Credit
                        c_txn = Transaction(
                            wallet_id=circle_wallet.id,
                            amount=circle.amount,
                            type=TransactionType.CONTRIBUTION,
                            status=TransactionStatus.SUCCESS,
                            reference=f"CREDIT_{circle.id}_{member.id}_{cycle_num}",
                            description=f"Contribution from {member.first_name} (Cycle {cycle_num})",
                            created_at=contrib.paid_at
                        )
                        session.add(c_txn)
                        
                        # Update Balances (Simulated)
                        # We don't want to actually drain user wallets to negative if we didn't give them enough
                        # But seeded wallets have random amounts. Let's assume infinite money for seed or 
                        # just log transactions without enforcing precise balance history for old txns 
                        # (since we set balance at start).
                        # However, for ACCURACY, we should update circle wallet balance.
                        circle_wallet.balance += circle.amount
                    
                    # Payout Logic Simulation
                    # If everyone contributed, payout happens
                    payout_amount = circle.amount * len(members)
                    recipient_idx = (cycle_num - 1) % len(members)
                    recipient = members[recipient_idx]
                    
                    # Only payout if cycle is done or we are simulating past history
                    # Let's say payouts happen automatically for seed data
                    recipient_wallet = await session.get(Wallet, recipient.id)
                    # Use get to fetch wallet obj properly if not in session? 
                    # We have ID, let's query.
                     # Re-query wallet to be safe
                    res = await session.execute(text(f"SELECT id FROM wallet WHERE user_id = '{recipient.id}'"))
                    rw_id = res.scalar()
                    
                    # Circle Debit
                    p_txn_c = Transaction(
                        wallet_id=circle_wallet.id,
                        amount=payout_amount,
                        type=TransactionType.PAYOUT,
                        status=TransactionStatus.SUCCESS,
                        reference=f"PAYOUT_DEBIT_{circle.id}_{cycle_num}",
                        description=f"Payout to {recipient.first_name} (Cycle {cycle_num})",
                        created_at=contrib.paid_at + timedelta(hours=1)
                    )
                    session.add(p_txn_c)
                    
                    # User Credit
                    p_txn_u = Transaction(
                        wallet_id=rw_id,
                        amount=payout_amount,
                        type=TransactionType.PAYOUT,
                        status=TransactionStatus.SUCCESS,
                        reference=f"PAYOUT_CREDIT_{circle.id}_{cycle_num}",
                        description=f"Payout from {circle.name} (Cycle {cycle_num})",
                        created_at=contrib.paid_at + timedelta(hours=1)
                    )
                    session.add(p_txn_u)
                    
                    circle_wallet.balance -= payout_amount
                
                session.add(circle_wallet)
                await session.commit()
                
        logger.info(f"Created {len(all_circles)} circles with {len(all_circles)*5} avg transactions.")

        # 4. Chats (Heavy Generation)
        logger.info("Creating chat messages...")
        total_msgs = 0
        for circle in all_circles:
            # Get members
            res = await session.execute(text(f"SELECT user_id FROM circlemember WHERE circle_id = '{circle.id}'"))
            member_ids = [row[0] for row in res.fetchall()]
            
            if not member_ids: continue
            
            num_msgs = random.randint(10, 100)
            base_time = circle.cycle_start_date or (get_utc_now() - timedelta(days=30))
            
            for _ in range(num_msgs):
                sender_id = random.choice(member_ids)
                msg_content = fake.sentence()
                
                # Random time after start
                msg_time = base_time + timedelta(minutes=random.randint(1, 10000))
                if msg_time > get_utc_now(): msg_time = get_utc_now()
                
                msg = ChatMessage(
                    circle_id=circle.id,
                    user_id=sender_id,
                    content=msg_content,
                    timestamp=msg_time,
                    message_type="text"
                )
                session.add(msg)
                total_msgs += 1
            
        await session.commit()
        logger.info(f"Created {total_msgs} chat messages.")

        # 5. Notifications
        logger.info("Creating notifications...")
        for user in users:
            for _ in range(random.randint(5, 15)):
                 n = Notification(
                    user_id=user.id,
                    title=random.choice(["Contribution Received", "Payout Ready", "New Message", "Welcome"]),
                    body=fake.sentence(),
                    type="info",
                    is_read=random.choice([True, False]),
                    created_at=get_utc_now() - timedelta(days=random.randint(0, 30))
                )
                 session.add(n)
        
        await session.commit()
        logger.info("SEEDING COMPLETE! 🚀")

if __name__ == "__main__":
    asyncio.run(seed_data())
