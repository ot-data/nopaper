import asyncio
import pytest
import websockets
import json
import time
from tests.conftest import WEBSOCKET_URL

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.skip_if_no_server
async def test_websocket_functionality():
    """Test the WebSocket server functionality with multiple messages."""
    print("\n=== Testing WebSocket Functionality ===\n")

    # Connect to the WebSocket server
    print("Connecting to WebSocket server...")
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        print("Connection established!")

        # Test messages
        test_messages = [
            "Hello, this is message 1",
            "This is message 2",
            "And this is message 3"
        ]

        # Send each message and collect responses
        for i, message in enumerate(test_messages):
            print(f"\n--- Sending message {i+1}: '{message}' ---")

            # Create message with ID
            message_data = {
                'message_id': i,
                'query': message,
                'session_id': 'test_session_123'
            }

            # Send the message
            await websocket.send(json.dumps(message_data))
            print(f"Message {i+1} sent!")

            # Collect and print responses
            full_response = ""
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Received chunk: {data}")

                if data.get('type') == 'response':
                    full_response += data.get('content', '')

                # Check if this is the last chunk
                if data.get('is_last', False):
                    break

            print(f"Complete response: {full_response}")

            # Small delay between messages
            if i < len(test_messages) - 1:
                print("Waiting before sending next message...")
                await asyncio.sleep(1)

        print("\n=== Test completed successfully! ===")

if __name__ == "__main__":
    asyncio.run(test_websocket_functionality())
