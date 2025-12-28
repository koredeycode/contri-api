
import pytest
import datetime
from httpx import AsyncClient
from app.core.config import settings
from app.models.circle import Circle, CircleMember
from app.models.chat import ChatMessage
from tests.utils import create_user_and_get_headers

@pytest.mark.asyncio
async def test_chat_pagination(client: AsyncClient, session):
    """
    Test chat pagination.
    """
    # 0. Setup User
    user_data, headers = await create_user_and_get_headers(client) # Returns dict, headers
    
    # We need the user ID. simpler to just fetch 'me' to get ID or login again.
    # But create_user_and_get_headers returns user payload data, not the ID.
    # Let's fetch me.
    resp = await client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    user_id = resp.json()["data"]["id"]

    # 1. Create Circle
    # Direct DB creation might be faster/easier for checking internal ID relationships, 
    # but API is better for integration. 
    # Let's use DB for setup where specific precise state is needed (like exact timestamps if critical),
    # forcing 15 messages quickly.
    
    circle = Circle(
        name="Chat Circle",
        amount=1000,
        frequency="weekly",
        invite_code=f"CHAT_PAG_{datetime.datetime.now().timestamp()}",
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
    
    # 3. Test Cursor Pagination (Limit is fixed to 100 in code likely, we seeded 15)
    
    # Case A: Get latest messages (no cursor)
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
    # Get messages before Message 10.
    cursor_timestamp = data[10]["timestamp"] # Timestamp of Message 10
    
    resp = await client.get(
        f"{settings.API_V1_STR}/chat/{circle.id}?before={cursor_timestamp}",
        headers=headers
    )
    assert resp.status_code == 200
    data_page = resp.json()["data"]
    # Messages with timestamp < Msg10 timestamp are Msg0..Msg9 (10 messages)
    assert len(data_page) == 10
    assert data_page[-1]["content"] == "Message 9"
    assert data_page[0]["content"] == "Message 0"
