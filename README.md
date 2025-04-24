# LPU Knowledge Assistant

A conversational AI assistant for Lovely Professional University (LPU) that provides information about the university, programs, admissions, and more.

## Features

- **Real-time Chat**: WebSocket and HTTP API for real-time, streaming responses
- **Persistent Memory**: Redis-backed conversation memory with in-memory fallback
- **Special Query Handling**: Dedicated handlers for common questions and patterns
- **LLM Integration**: Amazon Bedrock integration for AI-powered responses
- **Interactive UI**: Streamlit frontend with persistent WebSocket connection
- **Type-safe Configuration**: Pydantic BaseSettings for robust configuration management
- **Comprehensive Testing**: Pytest-based test suite with unit and integration tests

## System Architecture

### Backend (FastAPI)

- **WebSocket Endpoint**: Real-time, bidirectional communication
- **HTTP Endpoint**: Traditional request-response API
- **Memory Management**: Redis-backed persistent storage with in-memory fallback
- **Session Management**: Client-provided session IDs with UUID fallback
- **Modular Response Generation**: Broken down into smaller, focused functions

### Frontend (Streamlit)

- **Persistent WebSocket**: Single WebSocket connection per user session
- **Session Management**: Consistent session ID across interactions
- **Memory Testing**: Built-in functionality to test conversation memory

## Directory Structure

- `backend/`: Backend server code (FastAPI)
- `streamlit/`: Frontend code (Streamlit)
- `tests/`: Comprehensive test suite (pytest)
  - `unit/`: Unit tests for individual components
  - `integration/`: End-to-end tests for system functionality

## Setup

### Prerequisites

- Python 3.10+
- Redis (recommended for persistent memory)
- AWS account with Bedrock access (for LLM capabilities)

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv agentenv
   source agentenv/bin/activate  # On Windows: agentenv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   The `requirements.txt` file includes all necessary dependencies categorized as follows:
   - Core dependencies (FastAPI, Uvicorn, Pydantic)
   - AWS SDK (Boto3, Botocore)
   - LLM libraries (LiteLLM, Anthropic)
   - Storage (Redis)
   - Frontend (Streamlit, Altair, Pillow)
   - WebSockets (websockets, simple-websocket)
   - Testing (pytest and related packages)
   - Utilities (aiohttp, asyncio, etc.)
   - Documentation (Markdown)
4. Set up environment variables in a `.env` file:
   ```
   # AWS Authentication Method
   # Options: 'credentials' or 'iam_role'
   AWS_AUTH_METHOD=credentials  # For development with hardcoded credentials
   # AWS_AUTH_METHOD=iam_role   # For production with IAM roles

   # AWS Configuration
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key

   # Bedrock Configuration
   BEDROCK_MODEL_NAME=anthropic.claude-3-haiku-20240307-v1:0
   BEDROCK_MODEL_ARN=arn:aws:bedrock:region::foundation-model/model-id

   # Knowledge Base Configuration
   KB_ID=your_kb_id

   # Redis Configuration
   REDIS_ENABLED=true
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=
   REDIS_DB=0

   # Memory Configuration
   MEMORY_MAX_HISTORY=5
   MEMORY_SESSION_TTL=86400

   # Server Configuration
   PORT=8000
   WEBSOCKET_URL=ws://localhost:8000/chat
   ```

## Running the Application

### Backend Server

```bash
cd backend
python main_fastapi.py
```

The server will start on the port specified in your `.env` file (default: 8000).

### Frontend

```bash
cd streamlit
streamlit run app.py
```

The Streamlit app will be available at http://localhost:8501 by default.

## Key Implementation Details

### Persistent WebSocket Connection

The Streamlit frontend maintains a single, persistent WebSocket connection per user session, improving efficiency and reducing connection overhead:

```python
# Initialize WebSocket client in session state if not already present
if "websocket_client" not in st.session_state:
    st.session_state.websocket_client = WebSocketChatClient(WEBSOCKET_URL)
    st.session_state.websocket_client.initialize()
```

### Redis-backed Conversation Memory

The backend uses Redis as the primary storage mechanism for conversation memory with an in-memory fallback:

```python
# Get or create memory for a session
def get_memory(session_id: str) -> BaseConversationMemory:
    # Use Redis for persistent storage if enabled and available
    if settings.redis.enabled and redis_client is not None:
        return RedisConversationMemory(
            session_id=session_id,
            redis_client=redis_client,
            max_history=settings.memory.max_history,
            ttl=settings.memory.session_ttl
        )

    # Fall back to in-memory storage if Redis is not available
    if session_id not in memory_store:
        memory_store[session_id] = InMemoryConversationMemory(max_history=settings.memory.max_history)
    return memory_store[session_id]
```

### Type-safe Configuration with Pydantic

Configuration is managed using Pydantic's BaseSettings for type safety and validation:

```python
class Settings(BaseSettings):
    """Main settings class that combines all configuration settings."""
    aws: AWSSettings = Field(default_factory=AWSSettings)
    bedrock: BedrockSettings = Field(default_factory=BedrockSettings)
    knowledge_base: KnowledgeBaseSettings = Field(default_factory=KnowledgeBaseSettings)
    # ... other settings

    model_config = ConfigDict(env_file=".env", extra="ignore")
```

### Session ID Management

The backend prioritizes client-provided session IDs with UUID generation as fallback:

```python
# Use client-provided session ID if available, otherwise generate a UUID
session_id = data.get('session_id')
if not session_id:
    # Generate a new UUID for this session
    session_id = f"ws_{uuid.uuid4()}"
```

### Modular Response Generation

The backend's response generation is broken down into smaller, focused functions:

```python
async def generate_response(query: str, personal_info: Optional[Dict] = None,
                           institution_id: Optional[str] = None, session_id: str = "default") -> Any:
    try:
        # Get or create memory for this session
        memory = get_memory(session_id)

        # 1. Handle special queries
        special_response = await _handle_special_query(query, memory, personal_info, institution_id)
        if special_response:
            return special_response

        # 2. Check cache
        cached_response = _check_cache(query, memory)
        if cached_response:
            return cached_response

        # 3. Retrieve and format context
        context_data = await _retrieve_and_format_context(query, institution_id)

        # 4. Build prompt
        prompts = _build_prompt(query, memory, personal_info, context_data, institution_id)

        # 5. Invoke LLM
        return await _invoke_llm(prompts, context_data, memory, query)

    except Exception as e:
        # Error handling
        logger.exception(f"Error processing query: {query}")
        return {"responses": [{"type": "error", "content": f"Error processing query: {str(e)}"}]}
```

## Testing

The project includes a comprehensive test suite using pytest. See [tests/README.md](tests/README.md) for details.

### Running Tests

Using the test script:

```bash
# Run unit tests (default)
./run_tests.sh

# Run unit tests explicitly
./run_tests.sh unit

# Run integration tests
./run_tests.sh integration

# Run all tests
./run_tests.sh all

# Generate coverage report
./run_tests.sh coverage
```

Using pytest directly:

```bash
# Run all tests
python -m pytest

# Run unit tests
python -m pytest tests/unit -v

# Run integration tests
python -m pytest tests/integration -v
```

## AWS Authentication

The application supports two authentication methods for AWS services, controlled by the `AWS_AUTH_METHOD` feature flag:

### Authentication Methods

1. **Credential-based Authentication** (`AWS_AUTH_METHOD=credentials`):
   - Uses hardcoded AWS credentials from the `.env` file
   - Requires `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to be set
   - Suitable for development environments or when IAM roles are not available

2. **IAM Role Authentication** (`AWS_AUTH_METHOD=iam_role`):
   - Uses the AWS default credential provider chain
   - Does not require hardcoded credentials
   - Automatically uses the IAM role attached to the deployment environment
   - Recommended for production deployments

### Configuration

To configure the authentication method, set the following in your `.env` file:

```
# AWS Authentication Method
# Options: 'credentials' or 'iam_role'
AWS_AUTH_METHOD=credentials  # For development with hardcoded credentials
# AWS_AUTH_METHOD=iam_role   # For production with IAM roles
```

### IAM Role Requirements

When using IAM role authentication (`AWS_AUTH_METHOD=iam_role`), ensure your deployment environment has an IAM role with the following permissions:

- Bedrock: `bedrock:InvokeModel`, `bedrock-agent-runtime:Retrieve`
- S3: `s3:GetObject` (for accessing knowledge base documents)

For different deployment environments:
- EC2: Attach an instance profile with the required permissions
- ECS: Configure a task execution role with the required permissions
- Lambda: Configure a function execution role with the required permissions

## License

This project is licensed under the MIT License - see the LICENSE file for details.
