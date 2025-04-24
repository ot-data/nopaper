import asyncio
import pytest
import websockets
import json
import requests
from tests.conftest import WEBSOCKET_URL, SERVER_URL

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.skip_if_no_server
async def test_websocket():
    print("Testing WebSocket connection...")
    uri = WEBSOCKET_URL
    try:
        async with websockets.connect(uri) as websocket:
            # Send a message
            message = {
                "query": "Tell me about the Computer Science program at LPU",
                "session_id": "test-websocket-session"
            }
            await websocket.send(json.dumps(message))
            print(f"Sent: {message}")

            # Receive responses
            response_count = 0
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    response_data = json.loads(response)
                    response_count += 1

                    # Print the first few responses and the last one
                    if response_count <= 3 or response_data.get("is_last", False):
                        print(f"Received response {response_count}: {response_data.get('type', 'unknown')}")
                        if response_data.get("is_last", False):
                            print("Last response received")
                            break

                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    break
    except Exception as e:
        print(f"WebSocket connection error: {e}")

@pytest.mark.integration
@pytest.mark.http
def test_http():
    print("\nTesting HTTP endpoint...")
    url = f"{SERVER_URL}/chat"
    data = {
        "query": "What are the admission requirements for LPU?",
        "session_id": "test-http-session"
    }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()

        # Print response status and first part of content
        print(f"Response status: {response.status_code}")
        response_data = response.json()
        print(f"Session ID: {response_data.get('session_id')}")
        print(f"Number of response chunks: {len(response_data.get('responses', []))}")

        # Print the first few response chunks
        for i, chunk in enumerate(response_data.get('responses', [])[:3]):
            print(f"Response chunk {i+1}: {chunk.get('type')}")

    except requests.exceptions.RequestException as e:
        print(f"HTTP request error: {e}")

@pytest.mark.integration
@pytest.mark.http
def test_error_handling():
    print("\nTesting error handling...")
    url = f"{SERVER_URL}/chat"

    # Test with empty query
    data = {
        "query": "",
        "session_id": "test-error-session"
    }

    try:
        response = requests.post(url, json=data)
        print(f"Empty query response status: {response.status_code}")
        print(f"Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"HTTP request error: {e}")

    # Test with invalid JSON
    try:
        response = requests.post(url, data="invalid json", headers={"Content-Type": "application/json"})
        print(f"Invalid JSON response status: {response.status_code}")
        print(f"Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"HTTP request error: {e}")

async def main():
    # Test HTTP endpoint
    test_http()

    # Test WebSocket connection
    await test_websocket()

    # Test error handling
    test_error_handling()

if __name__ == "__main__":
    asyncio.run(main())
