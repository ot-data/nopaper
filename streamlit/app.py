import os
import streamlit as st
import websockets
import asyncio
import json
import queue
import threading
import sys
import os
import logging

# Configure logging to suppress the ScriptRunContext warnings
logging.getLogger('streamlit.runtime.scriptrunner.script_runner').setLevel(logging.ERROR)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_full_config, set_aws_credentials, WEBSOCKET_URL
from utils import load_config

# WebSocket Chat Client
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

                # Check if the message contains a session_id
                if 'session_id' in data and data['session_id']:
                    # Store the session ID in Streamlit session state
                    # We need to use an asyncio event loop to update the session state
                    # from this async function
                    import streamlit as st
                    if hasattr(st, 'session_state') and 'session_id' in st.session_state:
                        if st.session_state.session_id != data['session_id']:
                            print(f"Updating session ID from {st.session_state.session_id} to {data['session_id']}")
                            st.session_state.session_id = data['session_id']

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
    st.set_page_config(page_title="LPU Knowledge Assistant", page_icon="🎓")

    # Load configuration directly from environment variables
    try:
        config = load_config()
        set_aws_credentials()
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        config = {}

    # Memory is now handled by the backend

    # Initialize WebSocket client in session state if not already present
    if "websocket_client" not in st.session_state:
        st.session_state.websocket_client = WebSocketChatClient(WEBSOCKET_URL)
        st.session_state.websocket_client.initialize()

    # Use the persistent WebSocket client from session state
    chat_client = st.session_state.websocket_client

    # Title with institution selection
    institution_options = ["Lovely Professional University (LPU)", "Amity University"]
    institution_ids = {"Lovely Professional University (LPU)": "lpu", "Amity University": "amity"}

    selected_institution = st.selectbox("Select Institution", institution_options)
    institution_id = institution_ids[selected_institution]

    st.title(f"🎓 {selected_institution} Knowledge Assistant")

    # Sidebar for Personal Information
    with st.sidebar:
        st.header("Personal Information")
        student_id = st.text_input("Student ID (optional)", "")
        program = st.text_input("Program of Interest (optional)", "")

        # Personal info dictionary
        personal_info = {}
        if student_id:
            personal_info['student_id'] = student_id
        if program:
            personal_info['program'] = program

    # Initialize chat history and session ID
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Create a consistent session ID for this Streamlit session
    if "session_id" not in st.session_state:
        # Generate a UUID for the initial session ID
        import uuid
        st.session_state.session_id = f"streamlit_{uuid.uuid4()}"
        print(f"Generated new client session ID: {st.session_state.session_id}")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input form
    with st.form("chat_form", clear_on_submit=True):
        user_query = st.text_input("Your Question", placeholder=f"Ask about {selected_institution}...", key="input")
        col1, col2 = st.columns(2)
        submit_button = col1.form_submit_button("Send")
        memory_test_button = col2.form_submit_button("Test Memory")

    # Handle user submission
    if submit_button and user_query:
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
                st.sidebar.info(f"Using session ID: {session_id}")

                for chunk in chat_client.stream_response(user_query, personal_info, institution_id, session_id):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")

                response_placeholder.markdown(full_response)

                # Add to session state (memory is handled by the backend)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                error_msg = f"Connection error: {str(e)}"
                response_placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

    # Handle memory test button
    if memory_test_button:
        # Add memory test message to chat history
        memory_query = "What was my previous question?"
        st.session_state.messages.append({"role": "user", "content": memory_query})

        # Display user message
        with st.chat_message("user"):
            st.markdown(memory_query)

        # Display assistant response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            # Stream the response from WebSocket
            try:
                # Use the consistent session ID
                session_id = st.session_state.session_id

                for chunk in chat_client.stream_response(memory_query, personal_info, institution_id, session_id):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")

                response_placeholder.markdown(full_response)

                # Add to session state (memory is handled by the backend)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                error_msg = f"Connection error: {str(e)}"
                response_placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Register a cleanup function to be called when the app is closed
def cleanup():
    if "websocket_client" in st.session_state:
        st.session_state.websocket_client.shutdown()

# Register the cleanup function using the current API
import atexit
atexit.register(cleanup)

if __name__ == "__main__":
    main()