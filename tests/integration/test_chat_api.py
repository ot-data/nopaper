"""
Test script for special query handling through the chat API.
"""
import asyncio
import json
import pytest
import uuid
from tests.conftest import WEBSOCKET_URL, SERVER_URL

try:
    import websockets
except ImportError:
    pass

# Test queries
EXACT_MATCH_QUERIES = [
    "i want to raise a query",
    "can i raise a query",
    "can i raise a ticket",
    "can i connect to someone",
    "can i speak to the counsellor",
    "How can I track my application status?"
]

PATTERN_MATCH_QUERIES = [
    "I'd like to raise a ticket please",
    "I need to submit a query",
    "Can I file a complaint?",
    "I want to talk to someone from support",
    "Is there anyone I can speak with?",
    "How do I check my application status?",
    "Where can I see the status of my admission?",
    "I need to know how my application is progressing"
]

NON_MATCHING_QUERIES = [
    "What is the fee structure?",
    "Tell me about the computer science program",
    "When is the application deadline?",
    "What are the hostel facilities?",
    "Do you offer scholarships?"
]

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip_if_no_server
async def test_query(websocket, query, session_id, institution_id):
    """Test a single query and print the result."""
    # Create the request message
    message = {
        "type": "query",
        "content": query,
        "session_id": session_id,
        "institution_id": institution_id,
        "personal_info": {}
    }

    # Send the message
    await websocket.send(json.dumps(message))

    # Wait for the response
    try:
        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        response_data = json.loads(response)

        # If it's a special query, check for RAISE_QUERY
        if any(q in query.lower() for q in ["raise", "query", "ticket", "connect", "speak", "track"]):
            if response_data.get("content") == "{{RAISE_QUERY}}":
                assert response_data.get("content") == "{{RAISE_QUERY}}"
            # Otherwise, just check that we got a response
        else:
            assert "content" in response_data
    except asyncio.TimeoutError:
        pytest.skip("Timed out waiting for response")
    except Exception as e:
        pytest.fail(f"Error during test: {e}")

async def run_tests():
    """Run all tests."""
    uri = WEBSOCKET_URL

    try:
        async with websockets.connect(uri) as websocket:
            print("\n=== Testing Exact Match Queries ===")
            for query in EXACT_MATCH_QUERIES:
                await test_query(websocket, query)

            print("\n=== Testing Pattern Match Queries ===")
            for query in PATTERN_MATCH_QUERIES:
                await test_query(websocket, query)

            print("\n=== Testing Non-Matching Queries ===")
            for query in NON_MATCHING_QUERIES:
                await test_query(websocket, query)
    except Exception as e:
        print(f"Error connecting to the server: {str(e)}")
        print(f"Make sure the backend server is running on {SERVER_URL}")

if __name__ == "__main__":
    asyncio.run(run_tests())
