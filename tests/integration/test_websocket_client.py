import asyncio
import pytest
import websockets
from tests.conftest import WEBSOCKET_URL

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.skip_if_no_server
async def test_websocket():
    uri = WEBSOCKET_URL
    async with websockets.connect(uri) as websocket:
        # Send a message in the expected JSON format
        import json
        import uuid
        message = {
            "query": "Hello, WebSocket!",
            "personal_info": {},
            "institution_id": "lpu",
            "message_id": 1,
            "session_id": str(uuid.uuid4())
        }
        await websocket.send(json.dumps(message))

        # Receive the response
        response = await websocket.recv()
        response_data = json.loads(response)
        print(f"Received: {response_data}")

        # Verify we got a response
        assert "content" in response_data

if __name__ == "__main__":
    asyncio.run(test_websocket())
