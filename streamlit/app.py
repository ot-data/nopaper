import os
import streamlit as st
import websockets
import asyncio
import json
import queue
import threading

# Import configuration and utilities
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_full_config, set_aws_credentials, WEBSOCKET_URL
from utils import load_config
from memory import ConversationMemory

# WebSocket Chat Client
class WebSocketChatClient:
    def __init__(self, websocket_url):
        self.websocket_url = websocket_url

    async def send_message(self, message, personal_info=None):
        """Asynchronously send a message and yield response chunks from the WebSocket."""
        async with websockets.connect(self.websocket_url) as websocket:
            # Send message
            await websocket.send(json.dumps({
                'query': message,
                'personal_info': personal_info or {}
            }))

            # Collect streamed responses
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'response':
                    yield data['content']
                elif data['type'] == 'error':
                    yield f"Error: {data['content']}"
                    break

    def stream_response(self, message, personal_info=None):
        """Run the async send_message in a separate thread and yield chunks synchronously."""
        q = queue.Queue()

        def run_loop():
            """Run the asyncio event loop in a background thread."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def put_chunks():
                """Put WebSocket response chunks into the queue."""
                try:
                    async for chunk in self.send_message(message, personal_info):
                        q.put(chunk)
                except Exception as e:
                    q.put(f"Connection error: {str(e)}")
                finally:
                    q.put(None)  # Sentinel to indicate the end

            loop.run_until_complete(put_chunks())
            loop.close()

        # Start the background thread
        thread = threading.Thread(target=run_loop)
        thread.start()

        # Yield chunks from the queue in the main thread
        while True:
            chunk = q.get()
            if chunk is None:  # Check for sentinel
                break
            yield chunk

        # Wait for the thread to finish
        thread.join()

def main():
    st.set_page_config(page_title="LPU Knowledge Assistant", page_icon="🎓")

    # Load configuration directly from environment variables
    try:
        config = load_config()
        set_aws_credentials()
    except Exception as e:
        st.error(f"Error loading configuration: {e}")
        config = {}

    # Initialize memory
    memory = ConversationMemory(max_history=5)

    # Use WebSocket URL from config
    chat_client = WebSocketChatClient(WEBSOCKET_URL)

    # Title
    st.title("🎓 LPU Knowledge Assistant")

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

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input form
    with st.form("chat_form", clear_on_submit=True):
        user_query = st.text_input("Your Question", placeholder="Ask about LPU...", key="input")
        submit_button = st.form_submit_button("Send")

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
                for chunk in chat_client.stream_response(user_query, personal_info):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")

                response_placeholder.markdown(full_response)

                # Add to memory and session state
                memory.add_interaction(user_query, full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                error_msg = f"Connection error: {str(e)}"
                response_placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()