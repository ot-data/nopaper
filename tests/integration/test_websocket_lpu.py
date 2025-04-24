import asyncio
import pytest
import websockets
import json
from tests.conftest import WEBSOCKET_URL

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.skip_if_no_server
async def test_query(websocket, query, personal_info, institution_id, session_id):
    # Send a message
    message = {
        'query': query,
        'personal_info': personal_info,
        'institution_id': institution_id,
        'session_id': session_id
    }
    print(f"\nSending message with session_id: {session_id}")
    await websocket.send(json.dumps(message))

    # Receive the response
    print(f"\n\n===== QUERY: {query} =====")

    # Try to receive responses
    try:
        while True:
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            response_json = json.loads(response)
            if response_json.get('type') == 'response':
                print(response_json.get('content', ''), end='')
    except asyncio.TimeoutError:
        print("\n\n[End of response]")
    except Exception as e:
        print(f"\nError: {e}")

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.skip_if_no_server
async def test_websocket():
    uri = WEBSOCKET_URL
    institution_id = "lpu"
    # Use a fixed session ID for consistent memory across requests
    session_id = "test_session_123"

    # Personal information
    personal_info = {
        'name': 'Rahul Sharma',
        'program': 'B.Tech Computer Science',
        'current_semester': '5',
        'academic_background': 'Science',
        'location': 'Delhi',
        'career_interest': 'Artificial Intelligence',
        'industry_preference': 'Information Technology, Research'
    }

    # Test queries
    queries = [
        # First query - should be remembered
        "Tell me about LPU's Computer Science program",

        # Memory query - should return the first question
        "What was my previous question?",

        # Another regular query
        "What are the career opportunities after completing B.Tech in Computer Science at LPU?",

        # Memory query again - should return the career opportunities question
        "What was my last question?"
    ]

    async with websockets.connect(uri) as websocket:
        for query in queries:
            await test_query(websocket, query, personal_info, institution_id, session_id)
            await asyncio.sleep(1)  # Small delay between queries

if __name__ == "__main__":
    asyncio.run(test_websocket())
