"""
Demo script for the /ask chat feature.

Tests the ChatService directly (no server needed) or via HTTP
against a running server.

Usage:
    cd backend

    # Direct test (calls Gemini API directly):
    python -m scripts.demo_chat

    # HTTP test (requires server running on port 8000):
    python -m scripts.demo_chat --http
"""

import sys
import os
import asyncio
import argparse

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Load .env before importing anything else
from dotenv import load_dotenv
load_dotenv()


async def test_direct():
    """Test ChatService directly (no server needed)."""
    from services.chat.chat_service import get_chat_service

    chat = get_chat_service()
    print("=" * 60)
    print("🤖 ChatService Direct Test")
    print("=" * 60)

    # Test 1: Question within context (math - fractions)
    print("\n--- Test 1: Question about fractions (should be CONFIDENT) ---")
    q1 = "Làm sao để cộng phân số khác mẫu ạ?"
    print(f"📝 Q: {q1}")
    a1 = await chat.answer("test-user-1", q1)
    print(f"💬 A: {a1}\n")

    # Test 2: Question within context (science)
    print("--- Test 2: Question about science (should be CONFIDENT) ---")
    q2 = "Hệ tiêu hoá gồm những bộ phận nào?"
    print(f"📝 Q: {q2}")
    a2 = await chat.answer("test-user-1", q2)
    print(f"💬 A: {a2}\n")

    # Test 3: Question outside context (should ESCALATE)
    print("--- Test 3: Question outside context (should ESCALATE) ---")
    q3 = "Cho con hỏi lịch thi cuối kỳ lớp 4B5 là khi nào ạ?"
    print(f"📝 Q: {q3}")
    a3 = await chat.answer("test-user-2", q3)
    print(f"💬 A: {a3}\n")

    # Test 4: Follow-up question (test conversation history)
    print("--- Test 4: Follow-up (tests conversation history) ---")
    q4 = "Cho con ví dụ cụ thể hơn được không ạ?"
    print(f"📝 Q: {q4}")
    a4 = await chat.answer("test-user-1", q4)
    print(f"💬 A: {a4}\n")

    print("=" * 60)
    print("✅ Direct tests complete!")
    print("=" * 60)


async def test_http():
    """Test via HTTP against a running server."""
    import httpx

    base = "http://localhost:8000"
    print("=" * 60)
    print(f"🌐 HTTP Chat Test (server: {base})")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30) as client:
        # Check server is running
        try:
            r = await client.get(f"{base}/")
            print(f"Server status: {r.json().get('status', 'unknown')}\n")
        except httpx.ConnectError:
            print(f"❌ Cannot connect to {base}. Start the server first:")
            print("   cd backend && python -m scripts.run_zalo_server")
            return

        # Test 1: /ask question
        print("--- Test 1: /ask about math ---")
        r = await client.post(f"{base}/api/zalo/chat", json={
            "sender": "Phụ huynh Alex",
            "text": "/ask Bài tập Toán tuần này là gì ạ?",
        })
        data = r.json()
        print(f"Success: {data['success']}")
        print(f"Is /ask: {data['is_ask']}")
        print(f"Reply: {data['reply'][:200]}...\n" if len(data.get('reply', '')) > 200 else f"Reply: {data.get('reply', '')}\n")

        # Test 2: Regular message (no /ask)
        print("--- Test 2: Regular message (no /ask) ---")
        r = await client.post(f"{base}/api/zalo/chat", json={
            "sender": "Phụ huynh Alex",
            "text": "Cảm ơn cô ạ!",
        })
        data = r.json()
        print(f"Success: {data['success']}, Is /ask: {data['is_ask']}, Reply: '{data.get('reply', '')}'\n")

        # Test 3: /ask without question
        print("--- Test 3: /ask without question (should get hint) ---")
        r = await client.post(f"{base}/api/zalo/chat", json={
            "sender": "Phụ huynh Alex",
            "text": "/ask",
        })
        data = r.json()
        print(f"Reply: {data.get('reply', '')}\n")

        # Test 4: Check messages store
        print("--- Test 4: Check stored messages ---")
        r = await client.get(f"{base}/api/zalo/messages")
        data = r.json()
        print(f"Total messages in store: {data['count']}")
        for msg in data['messages'][-4:]:
            marker = "🤖" if msg['is_ai'] else "👤"
            print(f"  {marker} [{msg['time']}] {msg['sender']}: {msg['text'][:80]}...")

    print("\n" + "=" * 60)
    print("✅ HTTP tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the /ask chat feature")
    parser.add_argument("--http", action="store_true", help="Test via HTTP (requires running server)")
    args = parser.parse_args()

    if args.http:
        asyncio.run(test_http())
    else:
        asyncio.run(test_direct())
