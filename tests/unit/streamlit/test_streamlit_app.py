import streamlit as st
import websockets
import asyncio
import json
import queue
import threading
import sys
import os

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
            print(f"Attempting to connect to WebSocket at {self.websocket_url}...")
            self.connection = await websockets.connect(self.websocket_url)
            self.connected = True
            print("WebSocket connection established successfully!")

            # Start listening for messages in a separate task
            asyncio.create_task(self._listen_for_messages())
        except Exception as e:
            print(f"Connection error: {str(e)}")
            self.connected = False
            # Print more detailed error information
            import traceback
            traceback.print_exc()

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

def main():
    st.set_page_config(page_title="WebSocket Test App", page_icon="🔌")

    # Initialize WebSocket client in session state if not already present
    if "websocket_client" not in st.session_state:
        st.session_state.websocket_client = WebSocketChatClient("ws://localhost:8000/chat")
        st.session_state.websocket_client.initialize()
        st.session_state.connection_status = "Connecting..."

    # Use the persistent WebSocket client from session state
    chat_client = st.session_state.websocket_client

    # Update connection status
    if "connection_status" not in st.session_state:
        st.session_state.connection_status = "Unknown"

    # Force a connection check
    if not chat_client.connected:
        st.session_state.connection_status = "Reconnecting..."
        # This will trigger a reconnection attempt in the background thread
        chat_client.initialize()

    st.title("🔌 Persistent WebSocket Test")

    # Add connection status indicator with more details
    col1, col2 = st.columns(2)

    with col1:
        if chat_client.connected:
            st.success("WebSocket Connected")
            st.session_state.connection_status = "Connected"
        else:
            st.error("WebSocket Disconnected")
            st.session_state.connection_status = "Disconnected"

    with col2:
        st.info(f"Status: {st.session_state.connection_status}")
        st.info(f"Message ID Counter: {chat_client.next_message_id}")

    # Create a consistent session ID for this Streamlit session
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit_{id(st.session_state)}"

    st.sidebar.info(f"Session ID: {st.session_state.session_id}")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    user_query = st.chat_input("Type your message here...")

    if user_query:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_query})

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)

        # Display assistant response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            # Stream the response from WebSocket
            try:
                # Use the consistent session ID
                session_id = st.session_state.session_id

                for chunk in chat_client.stream_response(user_query, session_id=session_id):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")

                response_placeholder.markdown(full_response)

                # Add to session state
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                error_msg = f"Connection error: {str(e)}"
                response_placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

    # Add buttons for connection management
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Check Connection Status"):
            if chat_client.connected:
                st.success(f"WebSocket is connected. Message ID counter: {chat_client.next_message_id}")
            else:
                st.error("WebSocket is disconnected")
                # Try to reconnect
                st.info("Attempting to reconnect...")
                chat_client.initialize()

    with col2:
        if st.button("Force Reconnect"):
            # Force a reconnection by setting connected to False
            chat_client.connected = False
            chat_client.initialize()
            st.info("Forcing reconnection attempt...")

    # Add a debug section
    with st.expander("Debug Information"):
        st.write(f"WebSocket URL: {chat_client.websocket_url}")
        st.write(f"Connection Status: {chat_client.connected}")
        st.write(f"Message Queue Size: {chat_client.message_queue.qsize()}")
        st.write(f"Response Queues: {len(chat_client.response_queues)}")
        st.write(f"Next Message ID: {chat_client.next_message_id}")
        st.write(f"Session ID: {st.session_state.session_id}")

# Register a cleanup function to be called when the app is closed
def cleanup():
    if "websocket_client" in st.session_state:
        st.session_state.websocket_client.shutdown()

# We can't register the cleanup function with newer Streamlit versions
# Just make sure to call shutdown manually if needed

if __name__ == "__main__":
    main()
