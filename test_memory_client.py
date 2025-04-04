import asyncio
import websockets
import json

async def test_query(websocket, query, session_id):
    # Send a message
    message = {
        'query': query,
        'session_id': session_id
    }
    print(f"\nSending message with session_id: {session_id}")
    await websocket.send(json.dumps(message))

    # Receive the response
    print(f"\n===== QUERY: {query} =====")

    # Try to receive responses
    try:
        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
        response_json = json.loads(response)
        if response_json.get('type') == 'response':
            print(response_json.get('content', ''))
    except asyncio.TimeoutError:
        print("\n[End of response]")
    except Exception as e:
        print(f"\nError: {e}")

async def test_websocket():
    uri = "ws://localhost:8002/chat"  # Connect to our test server
    # Use a fixed session ID for consistent memory across requests
    session_id = "test_session_123"

    # Test queries
    queries = [
        # First query - should be remembered
        "Tell me about LPU",

        # Memory query - should return the first question
        "What was my previous question?",

        # Another regular query
        "What are the career opportunities?",

        # Memory query again - should return the career opportunities question
        "What was my last question?"
    ]

    async with websockets.connect(uri) as websocket:
        for query in queries:
            await test_query(websocket, query, session_id)
            await asyncio.sleep(1)  # Small delay between queries

if __name__ == "__main__":
    asyncio.run(test_websocket())
