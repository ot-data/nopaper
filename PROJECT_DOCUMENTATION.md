# Updated Documentation for LPU Knowledge Assistant

## Overview

The LPU Knowledge Assistant is a conversational AI system designed to provide information about Lovely Professional University (LPU) and other educational institutions. The system uses a WebSocket-based architecture to enable real-time, streaming responses and maintains conversation memory across interactions.

## System Architecture

The system consists of two main components:

1. **Backend Server (FastAPI)**: Handles WebSocket connections, processes queries, and generates responses using AWS Bedrock.
2. **Frontend Interface (Streamlit)**: Provides a user-friendly chat interface for interacting with the assistant.

### Key Features

- **Real-time Streaming Responses**: Responses are streamed in real-time using WebSockets.
- **Conversation Memory**: The system remembers previous interactions within a session.
- **Multi-Institution Support**: Configurable for different educational institutions.
- **Personalized Responses**: Incorporates user's personal information into responses.
- **Reference Links**: Includes relevant reference links in responses.

## Backend Implementation

### WebSocket Server (FastAPI)

The backend server is built using FastAPI and provides WebSocket endpoints for real-time communication.

```python
# WebSocket endpoint for real-time chat
@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Generate a unique session ID for this WebSocket connection
    session_id = str(id(websocket))

    while True:
        try:
            # Receive client message
            data = await websocket.receive_json()
            query = data.get('query')
            personal_info = data.get('personal_info')
            institution_id = data.get('institution_id')

            # Use client-provided session ID if available
            client_session_id = data.get('session_id')
            effective_session_id = client_session_id if client_session_id else session_id

            # Stream the response with the session ID
            async for response in generate_response(query, personal_info, institution_id, effective_session_id):
                await websocket.send_json(response)

        except WebSocketDisconnect:
            print("WebSocket disconnected")
            break
```

### HTTP Endpoint

The system also provides an HTTP endpoint for non-streaming interactions:

```python
@app.post("/chat")
async def http_chat(request: ChatRequest):
    responses = []
    # For HTTP requests, use provided session_id or generate one
    effective_session_id = request.session_id if request.session_id else "http_" + str(hash(str(request.personal_info) + str(request.institution_id)))

    async for response in generate_response(request.query, request.personal_info, request.institution_id, effective_session_id):
        responses.append(response)
    return {"responses": responses}
```

### Conversation Memory

The system maintains conversation history using a `ConversationMemory` class:

```python
class ConversationMemory:
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.conversation_history: List[Dict] = []

    def add_interaction(self, question: str, answer: str):
        timestamp = datetime.now()
        self.conversation_history.append({
            "question": question,
            "answer": answer,
            "timestamp": timestamp
        })
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

    def get_previous_question(self) -> Optional[str]:
        if self.conversation_history:
            return self.conversation_history[-1]["question"]
        return None
```

Memory is stored in a dictionary keyed by session ID:

```python
# Dictionary to store conversation memory for different sessions
memory_store: Dict[str, ConversationMemory] = {}

# Get or create memory for a session
def get_memory(session_id: str) -> ConversationMemory:
    if session_id not in memory_store:
        memory_store[session_id] = ConversationMemory(max_history=5)
    return memory_store[session_id]
```

### Memory Query Detection

The system detects memory-related queries using pattern matching:

```python
def is_memory_query(query: str) -> bool:
    processed_query = preprocess_query(query)
    memory_triggers = [
        "previous question", "last question", "what did i ask",
        "what was my question", "my previous", "earlier question"
    ]
    return any(trigger in processed_query for trigger in memory_triggers)
```

## Frontend Implementation (Streamlit)

### WebSocket Client

The Streamlit app uses a WebSocket client to communicate with the backend:

```python
class WebSocketChatClient:
    def __init__(self, websocket_url):
        self.websocket_url = websocket_url

    async def send_message(self, message, personal_info=None, institution_id=None, session_id=None):
        """Asynchronously send a message and yield response chunks from the WebSocket."""
        async with websockets.connect(self.websocket_url) as websocket:
            # Send message with session ID
            await websocket.send(json.dumps({
                'query': message,
                'personal_info': personal_info or {},
                'institution_id': institution_id,
                'session_id': session_id
            }))

            # Collect streamed responses
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'response':
                    yield data['content']
                elif data['type'] == 'error':
                    yield f"Error: {data['content']}"
                    break
```

### Session Management

The Streamlit app maintains a consistent session ID for each user session:

```python
# Create a consistent session ID for this Streamlit session
if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit_{id(st.session_state)}"
```

This session ID is passed with each WebSocket message to ensure conversation memory works correctly:

```python
# Use the consistent session ID
session_id = st.session_state.session_id
st.sidebar.info(f"Using session ID: {session_id}")

for chunk in chat_client.stream_response(user_query, personal_info, institution_id, session_id):
    full_response += chunk
    response_placeholder.markdown(full_response + "▌")
```

### Memory Testing

The app includes a "Test Memory" button to explicitly test the memory functionality:

```python
# User input form
with st.form("chat_form", clear_on_submit=True):
    user_query = st.text_input("Your Question", placeholder=f"Ask about {selected_institution}...", key="input")
    col1, col2 = st.columns(2)
    submit_button = col1.form_submit_button("Send")
    memory_test_button = col2.form_submit_button("Test Memory")

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

            # Add to memory and session state
            memory.add_interaction(memory_query, full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            response_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
```

## Configuration

### Environment Variables

The system uses environment variables for configuration:

```python
# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Bedrock Configuration
BEDROCK_MODEL_NAME = os.getenv("BEDROCK_MODEL_NAME")
BEDROCK_MODEL_ARN = os.getenv("BEDROCK_MODEL_ARN")

# Knowledge Base Configuration
KB_ID = os.getenv("KB_ID")

# Institution-specific Knowledge Base IDs
LPU_KB_ID = os.getenv("LPU_KB_ID", KB_ID)
AMITY_KB_ID = os.getenv("AMITY_KB_ID")

# WebSocket Configuration
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:8000/chat")

# Server Configuration
PORT = int(os.getenv("PORT", "8000"))
```

## Testing

### WebSocket Testing

The system includes test scripts for verifying WebSocket functionality:

```python
async def test_websocket():
    uri = "ws://localhost:8000/chat"
    institution_id = "lpu"
    # Use a fixed session ID for consistent memory across requests
    session_id = "test_session_123"

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
```

### HTTP Testing

The system also includes test scripts for verifying HTTP functionality:

```python
def test_query(query, personal_info, institution_id, session_id):
    # Prepare the request
    url = "http://localhost:8000/chat"
    data = {
        'query': query,
        'personal_info': personal_info,
        'institution_id': institution_id,
        'session_id': session_id
    }

    # Send the request
    response = requests.post(url, json=data)

    # Process the response
    if response.status_code == 200:
        print(f"\n\n===== QUERY: {query} =====")
        responses = response.json().get('responses', [])
        for resp in responses:
            if resp.get('type') == 'response':
                print(resp.get('content', ''), end='')
        print("\n\n[End of response]")
    else:
        print(f"\nError: {response.status_code} - {response.text}")
```

### Memory Testing

The system includes a dedicated test server for verifying memory functionality:

```python
# Simple memory store
memory_store: Dict[str, List[Dict]] = {}

def get_previous_question(session_id: str) -> Optional[str]:
    if session_id in memory_store and memory_store[session_id]:
        return memory_store[session_id][-1]["question"]
    return None

def add_interaction(session_id: str, question: str, answer: str):
    if session_id not in memory_store:
        memory_store[session_id] = []
    memory_store[session_id].append({"question": question, "answer": answer})
    # Keep only the last 5 interactions
    if len(memory_store[session_id]) > 5:
        memory_store[session_id].pop(0)
```

## Running the System

### Backend Server

```bash
cd backend
pip install -r requirements.txt
python main_fastapi.py
```

### Streamlit Frontend

```bash
cd streamlit
pip install -r requirements.txt
streamlit run app.py
```

### Testing

```bash
# WebSocket testing
python test_websocket_lpu.py

# HTTP testing
python test_http_lpu.py

# Memory testing
python test_memory_server.py  # In one terminal
python test_memory_client.py  # In another terminal
```

## Key Insights and Lessons Learned

1. **Session ID Consistency**: For memory functionality to work correctly, a consistent session ID must be used across all messages from the same user session.

2. **WebSocket Connection Management**: The Streamlit app creates a new WebSocket connection for each message, so the session ID must be passed explicitly to maintain conversation context.

3. **Memory Query Detection**: The system uses pattern matching to detect memory-related queries, which allows it to respond appropriately to questions about previous interactions.

4. **Testing Approach**: Separate test scripts for WebSocket, HTTP, and memory functionality help verify that each component works correctly.

5. **Environment-Based Configuration**: Using environment variables for configuration makes the system more flexible and easier to deploy in different environments.

## Troubleshooting

### Memory Not Working

If memory functionality is not working:

1. Verify that a consistent session ID is being used across messages.
2. Check that the session ID is being passed correctly in the WebSocket message.
3. Ensure that the server is correctly storing and retrieving conversation history based on the session ID.

### WebSocket Connection Issues

If WebSocket connections are failing:

1. Verify that the WebSocket server is running on the expected port.
2. Check for any network issues or firewall restrictions.
3. Ensure that the WebSocket URL is correctly configured in the client.

### Response Streaming Issues

If response streaming is not working:

1. Verify that the WebSocket connection is being established correctly.
2. Check that the server is sending responses in the expected format.
3. Ensure that the client is correctly processing the streamed responses.

## Future Improvements

1. **Persistent Memory**: Implement database storage for conversation memory to persist across server restarts.
2. **User Authentication**: Add user authentication to associate conversation memory with specific users.
3. **Enhanced Memory Queries**: Improve memory query detection to handle more complex questions about previous interactions.
4. **Multi-Session Support**: Allow users to manage multiple conversation sessions.
5. **Performance Optimization**: Optimize WebSocket connections and response streaming for better performance.

