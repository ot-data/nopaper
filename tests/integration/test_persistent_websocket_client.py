import streamlit as st
import websockets
import asyncio
import json
import queue
import threading
import time
import pytest
from tests.conftest import WEBSOCKET_URL

# WebSocket Chat Client with persistent connection
class WebSocketChatClient:
    def __init__(self, websocket_url):
        self.websocket_url = websocket_url
        self.connection = None
        self.connected = False
        self.connection_lock = threading.Lock()
        self.event_loop = None
        self.event_loop_thread = None
        self.message_queue = queue.Queue()
        self.response_queues = {}
        self.next_message_id = 0
        self.shutdown_event = threading.Event()

    def initialize(self):
        """Initialize the WebSocket connection in a background thread."""
        if self.event_loop_thread is None:
            self.event_loop = asyncio.new_event_loop()
            self.event_loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self.event_loop_thread.start()

    def _run_event_loop(self):
        """Run the asyncio event loop in a background thread."""
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_until_complete(self._maintain_connection())

    async def _maintain_connection(self):
        """Maintain the WebSocket connection and process messages."""
        while not self.shutdown_event.is_set():
            try:
                if not self.connected:
                    await self._connect()

                # Process any pending messages
                while not self.message_queue.empty():
                    message_id, message, personal_info, institution_id, session_id = self.message_queue.get()
                    await self._send_message_internal(message_id, message, personal_info, institution_id, session_id)

                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Connection maintenance error: {str(e)}")
                self.connected = False
                await asyncio.sleep(1)  # Wait before reconnecting

        # Close connection when shutdown is requested
        if self.connection and self.connected:
            await self.connection.close()
            self.connected = False
            print("WebSocket connection closed due to shutdown")

    async def _connect(self):
        """Establish a WebSocket connection."""
        try:
            self.connection = await websockets.connect(self.websocket_url)
            self.connected = True
            print("WebSocket connection established")

            # Start listening for messages in a separate task
            asyncio.create_task(self._listen_for_messages())
        except Exception as e:
            print(f"Connection error: {str(e)}")
            self.connected = False

    async def _listen_for_messages(self):
        """Listen for messages from the WebSocket connection."""
        try:
            async for message in self.connection:
                data = json.loads(message)
                # Check if the message contains a message_id
                message_id = data.get('message_id')

                if message_id is not None and message_id in self.response_queues:
                    # Put the message in the appropriate response queue
                    self.response_queues[message_id].put(data)

                    # If it's an error or the last message, mark the end of the stream
                    if data.get('type') == 'error' or data.get('is_last', False):
                        self.response_queues[message_id].put(None)  # End of stream marker
        except Exception as e:
            print(f"WebSocket listening error: {str(e)}")
            self.connected = False

    async def _send_message_internal(self, message_id, message, personal_info=None, institution_id=None, session_id=None):
        """Send a message using the WebSocket connection."""
        if not self.connected:
            self.response_queues[message_id].put({"type": "error", "content": "Not connected to server"})
            self.response_queues[message_id].put(None)  # End of stream marker
            return

        try:
            # Send message with message_id
            await self.connection.send(json.dumps({
                'message_id': message_id,
                'query': message,
                'personal_info': personal_info or {},
                'institution_id': institution_id,
                'session_id': session_id
            }))
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            self.connected = False
            self.response_queues[message_id].put({"type": "error", "content": f"Connection error: {str(e)}"})
            self.response_queues[message_id].put(None)  # End of stream marker

    def send_message(self, message, personal_info=None, institution_id=None, session_id=None):
        """Queue a message to be sent and return a message ID."""
        with self.connection_lock:
            message_id = self.next_message_id
            self.next_message_id += 1

            # Create a queue for this message's responses
            self.response_queues[message_id] = queue.Queue()

            # Queue the message to be sent
            self.message_queue.put((message_id, message, personal_info, institution_id, session_id))

            return message_id

    def stream_response(self, message, personal_info=None, institution_id=None, session_id=None):
        """Send a message and yield response chunks synchronously."""
        # Ensure the client is initialized
        self.initialize()

        # Send the message and get a message ID
        message_id = self.send_message(message, personal_info, institution_id, session_id)

        # Yield responses from the queue
        while True:
            response = self.response_queues[message_id].get()
            if response is None:  # End of stream
                break

            if response.get('type') == 'response':
                yield response.get('content', '')
            elif response.get('type') == 'error':
                yield f"Error: {response.get('content', 'Unknown error')}"
                break

        # Clean up the response queue
        del self.response_queues[message_id]

    def shutdown(self):
        """Shutdown the WebSocket client and close the connection."""
        print("Shutting down WebSocket client...")
        self.shutdown_event.set()

        # Wait for the event loop thread to finish
        if self.event_loop_thread and self.event_loop_thread.is_alive():
            self.event_loop_thread.join(timeout=2.0)
            print("WebSocket client shutdown complete.")

# Test function
@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.skip_if_no_server
def test_persistent_websocket():
    # Create a WebSocket client
    client = WebSocketChatClient(WEBSOCKET_URL)

    # Initialize the client (establishes the connection)
    client.initialize()

    # Wait for connection to establish
    time.sleep(1)

    # Test sending multiple messages
    session_id = "test_session_123"

    # Send first message
    print("\nSending first message...")
    response1 = ""
    for chunk in client.stream_response("Hello, how are you?", session_id=session_id):
        response1 += chunk
        print(f"Received chunk: {chunk}")

    print(f"\nComplete response 1: {response1}")

    # Send second message
    print("\nSending second message...")
    response2 = ""
    for chunk in client.stream_response("What's the weather like today?", session_id=session_id):
        response2 += chunk
        print(f"Received chunk: {chunk}")

    print(f"\nComplete response 2: {response2}")

    # Send third message
    print("\nSending third message...")
    response3 = ""
    for chunk in client.stream_response("Tell me a joke", session_id=session_id):
        response3 += chunk
        print(f"Received chunk: {chunk}")

    print(f"\nComplete response 3: {response3}")

    # Shutdown the client
    print("\nShutting down client...")
    client.shutdown()
    print("Test complete!")

if __name__ == "__main__":
    test_persistent_websocket()
