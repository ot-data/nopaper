import asyncio
import websockets
import json

async def test_query(websocket, query, personal_info):
    # Send a message
    await websocket.send(json.dumps({
        'query': query,
        'personal_info': personal_info
    }))

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

async def test_websocket():
    uri = "ws://localhost:8000/chat/lpu"

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
        # In-scope query with personalization
        "What are the career opportunities after completing B.Tech in Computer Science at LPU?",

        # Out-of-scope query
        "What's the weather like in Delhi today?"
    ]

    async with websockets.connect(uri) as websocket:
        for query in queries:
            await test_query(websocket, query, personal_info)
            await asyncio.sleep(1)  # Small delay between queries

if __name__ == "__main__":
    asyncio.run(test_websocket())
