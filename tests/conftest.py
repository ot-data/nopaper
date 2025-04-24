"""
Shared test fixtures for pytest.
"""
import os
import sys
import pytest
import redis
import asyncio
import uuid
import json
from unittest.mock import MagicMock

# Get server configuration from environment variables
SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT = int(os.getenv("PORT", "8000"))
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
WEBSOCKET_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}/chat"

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import project modules
from backend.config import settings
from backend.redis_memory import RedisConversationMemory
from backend.memory import InMemoryConversationMemory

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.expire.return_value = True
    mock_client.delete.return_value = True
    return mock_client

@pytest.fixture
def redis_client():
    """Real Redis client for testing, if Redis is available."""
    try:
        client = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            password=settings.redis.password,
            db=settings.redis.db,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        # Test connection
        client.ping()
        return client
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        pytest.skip("Redis server not available")

@pytest.fixture
def redis_memory(redis_client):
    """Redis-backed conversation memory for testing."""
    memory = RedisConversationMemory(
        session_id="test_session",
        redis_client=redis_client,
        max_history=5,
        ttl=60  # Short TTL for tests
    )
    # Clear any existing data
    memory.clear()
    yield memory
    # Clean up
    memory.clear()

@pytest.fixture
def in_memory_memory():
    """In-memory conversation memory for testing."""
    return InMemoryConversationMemory(max_history=5)

# We're using pytest-asyncio's built-in event_loop fixture
# No need to define our own

# Skip tests that require a server if the server is not running
def pytest_runtest_setup(item):
    """Skip tests marked with skip_if_no_server if the server is not running."""
    if "skip_if_no_server" in item.keywords:
        # Check if the server is running
        server_running = False
        try:
            import requests
            response = requests.get(SERVER_URL)
            # Consider 404 as a sign that the server is running but the endpoint doesn't exist
            server_running = response.status_code in [200, 404]
        except:
            server_running = False

        if not server_running:
            pytest.skip(f"Server not running on {SERVER_URL}")

# Integration test fixtures

@pytest.fixture(params=[
    "i want to raise a query",
    "can i raise a query",
    "can i raise a ticket",
    "can i connect to someone",
    "can i speak to the counsellor",
    "How can I track my application status?",
    "What is the fee structure?",
    "Tell me about the computer science program"
])
def query(request):
    """Test queries for integration tests."""
    return request.param

@pytest.fixture
def personal_info():
    """Personal information for testing."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "1234567890"
    }

@pytest.fixture
def institution_id():
    """Institution ID for testing."""
    return "lpu"

@pytest.fixture
def session_id():
    """Session ID for testing."""
    return str(uuid.uuid4())

# Use pytest_asyncio.fixture if available, otherwise fall back to pytest.fixture
if pytest_asyncio is not None:
    @pytest_asyncio.fixture
    async def websocket():
        """WebSocket client for testing."""
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("websockets package not installed")

        # Check if the server is running
        server_running = False
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(SERVER_URL) as response:
                    # Consider 404 as a sign that the server is running but the endpoint doesn't exist
                    server_running = response.status in [200, 404]
        except:
            server_running = False

        if not server_running:
            pytest.skip(f"WebSocket server not running on {SERVER_URL}")

        # Connect to the WebSocket server
        try:
            ws = await websockets.connect(WEBSOCKET_URL)
            yield ws
            await ws.close()
        except Exception as e:
            pytest.skip(f"Could not connect to WebSocket server: {e}")
else:
    @pytest.fixture
    async def websocket(event_loop):
        """WebSocket client for testing."""
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("websockets package not installed")

        # Check if the server is running
        server_running = False
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(SERVER_URL) as response:
                    # Consider 404 as a sign that the server is running but the endpoint doesn't exist
                    server_running = response.status in [200, 404]
        except:
            server_running = False

        if not server_running:
            pytest.skip(f"WebSocket server not running on {SERVER_URL}")

        # Connect to the WebSocket server
        try:
            ws = await websockets.connect(WEBSOCKET_URL)
            yield ws
            await ws.close()
        except Exception as e:
            pytest.skip(f"Could not connect to WebSocket server: {e}")
