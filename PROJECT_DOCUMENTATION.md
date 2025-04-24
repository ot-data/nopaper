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
    print(f"DEBUG - New WebSocket connection established")

    while True:
        try:
            # Receive client message
            data = await websocket.receive_json()
            query = data.get('query')
            personal_info = data.get('personal_info')
            institution_id = data.get('institution_id')
            message_id = data.get('message_id')  # Get message_id from client

            # Use client-provided session ID if available, otherwise generate a UUID
            session_id = data.get('session_id')
            if not session_id:
                # Generate a new UUID for this session
                session_id = f"ws_{uuid.uuid4()}"
                logger.info(f"Client did not provide session ID, generated new one: {session_id}")
            else:
                logger.debug(f"Using client-provided session ID: {session_id}")

            # Get the response with the session ID
            response = await generate_response(query, personal_info, institution_id, session_id)

            # Handle different response types and send with message_id and session_id
            if isinstance(response, dict) and "responses" in response:
                # If it's a special query response with multiple chunks
                for i, chunk in enumerate(response["responses"]):
                    # Add message_id and session_id to each chunk
                    chunk_with_id = {**chunk, "message_id": message_id, "session_id": session_id}
                    # Mark the last chunk
                    if i == len(response["responses"]) - 1:
                        chunk_with_id["is_last"] = True
                    await websocket.send_json(chunk_with_id)
            # Additional response handling for other types...

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
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

The system uses an abstract base class for conversation memory with multiple implementations:

```python
# Base abstract class for conversation memory
class BaseConversationMemory(ABC):
    """Abstract base class for conversation memory implementations."""

    @abstractmethod
    def add_interaction(self, question: str, answer: str) -> None:
        """Add a new interaction to the conversation history."""
        pass

    @abstractmethod
    def get_context(self) -> str:
        """Get the conversation context as a formatted string."""
        pass

    @abstractmethod
    def get_previous_question(self) -> Optional[str]:
        """Get the most recent question from the conversation history."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the conversation history."""
        pass
```

#### Redis-backed Implementation

The primary implementation uses Redis for persistent storage:

```python
class RedisConversationMemory(BaseConversationMemory):
    """Redis-backed implementation of conversation memory."""

    def __init__(self, session_id: str, redis_client: Any, max_history: int = 5, ttl: int = 86400):
        self.session_id = session_id
        self.redis = redis_client
        self.max_history = max_history
        self.ttl = ttl  # Time-to-live in seconds (default: 1 day)
        self.key_prefix = "conversation:"
        # For compatibility with code that expects it
        self.conversation_history = []

    def add_interaction(self, question: str, answer: str) -> None:
        key = f"{self.key_prefix}{self.session_id}"

        try:
            # Get current history from Redis
            history = self._get_history()

            # Add new interaction
            history.append({
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat()
            })

            # Trim if needed
            if len(history) > self.max_history:
                history = history[-self.max_history:]

            # Save back to Redis with TTL
            self.redis.set(key, json.dumps(history))
            self.redis.expire(key, self.ttl)

        except Exception as e:
            # Fallback to in-memory if Redis fails
            logger.error(f"Error adding interaction to Redis: {e}")
```

#### In-memory Fallback

A fallback implementation uses in-memory storage:

```python
class InMemoryConversationMemory(BaseConversationMemory):
    """In-memory implementation of conversation memory."""

    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.conversation_history: List[Dict] = []

    def add_interaction(self, question: str, answer: str) -> None:
        timestamp = datetime.now()
        self.conversation_history.append({
            "question": question,
            "answer": answer,
            "timestamp": timestamp
        })
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)
```

The system tries to use Redis first and falls back to in-memory storage if Redis is not available:

```python
# Get or create memory for a session
def get_memory(session_id: str) -> BaseConversationMemory:
    # Use Redis for persistent storage if enabled and available
    if settings.redis.enabled and redis_client is not None:
        try:
            return RedisConversationMemory(
                session_id=session_id,
                redis_client=redis_client,
                max_history=settings.memory.max_history,
                ttl=settings.memory.session_ttl
            )
        except Exception as e:
            logger.error(f"Error creating Redis memory: {e}")
            logger.warning("Falling back to in-memory storage.")

    # Fall back to in-memory storage
    if session_id not in memory_store:
        memory_store[session_id] = InMemoryConversationMemory(max_history=settings.memory.max_history)
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

The Streamlit app uses a persistent WebSocket client to communicate with the backend:

```python
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
```

This implementation maintains a single, persistent WebSocket connection per user session, improving efficiency by avoiding the overhead of creating a new connection for each message.

### Session Management

The Streamlit app maintains a consistent session ID for each user session using UUID generation:

```python
# Create a consistent session ID for this Streamlit session
if "session_id" not in st.session_state:
    # Generate a UUID for the initial session ID
    import uuid
    st.session_state.session_id = f"streamlit_{uuid.uuid4()}"
    print(f"Generated new client session ID: {st.session_state.session_id}")
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

The backend prioritizes client-provided session IDs and only generates UUIDs as a fallback:

```python
# Use client-provided session ID if available, otherwise generate a UUID
session_id = data.get('session_id')
if not session_id:
    # Generate a new UUID for this session
    session_id = f"ws_{uuid.uuid4()}"
    logger.info(f"Client did not provide session ID, generated new one: {session_id}")
else:
    logger.debug(f"Using client-provided session ID: {session_id}")
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

### Configuration with Pydantic BaseSettings

The system uses Pydantic's BaseSettings for type-safe configuration management:

```python
class AWSSettings(BaseSettings):
    """AWS-related configuration settings."""
    region: str = Field(
        default=os.getenv("AWS_REGION"),
        description="AWS region",
        json_schema_extra={"env": "AWS_REGION"}
    )
    access_key_id: str = Field(
        default=os.getenv("AWS_ACCESS_KEY_ID"),
        description="AWS access key ID",
        json_schema_extra={"env": "AWS_ACCESS_KEY_ID"}
    )
    secret_access_key: str = Field(
        default=os.getenv("AWS_SECRET_ACCESS_KEY"),
        description="AWS secret access key",
        json_schema_extra={"env": "AWS_SECRET_ACCESS_KEY"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    enabled: bool = Field(
        default=os.getenv("REDIS_ENABLED", "false").lower() == "true",
        description="Whether Redis is enabled",
        json_schema_extra={"env": "REDIS_ENABLED"}
    )
    host: str = Field(
        default=os.getenv("REDIS_HOST", "localhost"),
        description="Redis host",
        json_schema_extra={"env": "REDIS_HOST"}
    )
    # ... other Redis settings

class Settings(BaseSettings):
    """Main settings class that combines all configuration settings."""
    aws: AWSSettings = Field(default_factory=AWSSettings)
    bedrock: BedrockSettings = Field(default_factory=BedrockSettings)
    knowledge_base: KnowledgeBaseSettings = Field(default_factory=KnowledgeBaseSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    websocket: WebSocketSettings = Field(default_factory=WebSocketSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

    model_config = ConfigDict(env_file=".env", extra="ignore")

# Create a global settings instance
settings = Settings()
```

This approach provides several advantages:
1. Type safety and validation
2. Default values
3. Documentation through field descriptions
4. Automatic loading from environment variables and .env files
5. Nested configuration structure

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

2. **WebSocket Connection Management**: The Streamlit app maintains a persistent WebSocket connection for each user session, improving efficiency while still passing the session ID explicitly to maintain conversation context.

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

1. **IAM Role Integration**: Replace hardcoded AWS credentials with IAM roles for improved security.
2. **User Authentication**: Add user authentication to associate conversation memory with specific users.
3. **Enhanced Memory Queries**: Improve memory query detection to handle more complex questions about previous interactions.
4. **Multi-Session Support**: Allow users to manage multiple conversation sessions.
5. **Performance Optimization**: Further optimize WebSocket connections and response streaming for better performance.
6. **Improved Test Coverage**: Increase test coverage, especially for frontend components.

