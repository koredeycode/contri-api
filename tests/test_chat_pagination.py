import pytest
import uuid
import datetime
from httpx import AsyncClient
from app.core.config import settings
from app.models.circle import Circle, CircleMember
from app.models.chat import ChatMessage

@pytest.mark.asyncio
async def test_chat_pagination(client: AsyncClient, session):
    """
    Test chat pagination.
    """
    # 0. Setup User
    email = f"user_chat_{uuid.uuid4()}@example.com"
    password = "password123"
    
    # Register & Login
    await client.post(f"{settings.API_V1_STR}/auth/signup", json={
        "email": email, "password": password, "first_name": "Chat", "last_name": "User", "phone_number": "+2348000000000"
    })
    resp = await client.post(f"{settings.API_V1_STR}/auth/login", json={"email": email, "password": password})
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get User ID
    resp = await client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    user_id = uuid.UUID(resp.json()["data"]["id"])

    # 1. Create Circle
    circle = Circle(
        name="Chat Circle",
        amount=1000,
        frequency="weekly",
        invite_code=f"CHAT{uuid.uuid4().hex[:4]}",
        status="active",
        target_members=5,
        payout_preference="fixed"
    )
    session.add(circle)
    await session.commit()
    await session.refresh(circle)
    
    # Join Circle
    cm = CircleMember(user_id=user_id, circle_id=circle.id, role="host", payout_order=1)
    session.add(cm)
    await session.commit()
    
    # 2. Seed Messages (15 messages)
    base_time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    for i in range(15):
        msg = ChatMessage(
            circle_id=circle.id,
            user_id=user_id,
            content=f"Message {i}",
            timestamp=base_time + datetime.timedelta(minutes=i),
            message_type="text"
        )
        session.add(msg)
    await session.commit()
    
    # 3. Test Cursor Pagination (Limit is fixed to 100, we seeded 15)
    
    # Case A: Get latest messages (no cursor)
    # Should return all 15 messages (100 limit > 15), reversed to chronological order.
    # Newest: Message 14, Oldest: Message 0.
    # Response: [Msg0, ..., Msg14]
    
    resp = await client.get(
        f"{settings.API_V1_STR}/chat/{circle.id}",
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 15
    assert data[-1]["content"] == "Message 14" # Newest
    assert data[0]["content"] == "Message 0"   # Oldest
    
    # Case B: Pagination using 'before' cursor
    # We want messages BEFORE Message 10.
    # Message 10 timestamp is what we pass.
    # Should get [Msg0, ..., Msg9] (10 messages total)
    
    # Identify timestamp of Message 10 from previous response
    # data is [Msg0, ..., Msg14]. Msg10 is at index 10.
    cursor_timestamp = data[10]["timestamp"] # Timestamp of Message 10
    
    resp = await client.get(
        f"{settings.API_V1_STR}/chat/{circle.id}?before={cursor_timestamp}",
        headers=headers
    )
    assert resp.status_code == 200
    data_page = resp.json()["data"]
    # Messages with timestamp < Msg10 timestamp are Msg0..Msg9
    assert len(data_page) == 10
    assert data_page[-1]["content"] == "Message 9"
    assert data_page[0]["content"] == "Message 0"
