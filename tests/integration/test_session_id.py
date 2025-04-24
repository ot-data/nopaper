"""
Integration tests for session ID management.
"""
import pytest
import uuid
import asyncio
import websockets
import json
import requests
from urllib.parse import urljoin
from tests.conftest import SERVER_URL, WEBSOCKET_URL

# Mark these tests to be skipped if the server is not running
pytestmark = [pytest.mark.integration, pytest.mark.skip_if_no_server]

@pytest.mark.integration
class TestSessionIdIntegration:
    """Integration tests for session ID management."""

    # Server URLs
    HTTP_URL = SERVER_URL
    WS_URL = WEBSOCKET_URL

    @pytest.mark.asyncio
    async def test_websocket_client_provided_session_id(self):
        """Test that WebSocket endpoint uses client-provided session ID."""
        # Create a unique session ID for this test
        client_session_id = f"test_session_{uuid.uuid4()}"

        # Connect to WebSocket
        async with websockets.connect(self.WS_URL) as websocket:
            # Send a message with the session ID
            await websocket.send(json.dumps({
                "query": "What is LPU?",
                "personal_info": {},
                "institution_id": "lpu",
                "message_id": 1,
                "session_id": client_session_id
            }))

            # Receive responses until we get the last one
            while True:
                response = json.loads(await websocket.recv())
                if response.get("is_last", False):
                    break

            # Check that the response contains the same session ID
            assert response["session_id"] == client_session_id

    @pytest.mark.asyncio
    async def test_websocket_generated_session_id(self):
        """Test that WebSocket endpoint generates a session ID if not provided."""
        # Connect to WebSocket
        async with websockets.connect(self.WS_URL) as websocket:
            # Send a message without a session ID
            await websocket.send(json.dumps({
                "query": "What is LPU?",
                "personal_info": {},
                "institution_id": "lpu",
                "message_id": 1
                # No session_id
            }))

            # Receive responses until we get the last one
            while True:
                response = json.loads(await websocket.recv())
                if response.get("is_last", False):
                    break

            # Check that the response contains a generated session ID
            assert "session_id" in response
            assert response["session_id"].startswith("ws_")

            # Verify it's a valid UUID
            session_id = response["session_id"][3:]  # Remove "ws_" prefix
            try:
                uuid.UUID(session_id)
                is_valid_uuid = True
            except ValueError:
                is_valid_uuid = False
            assert is_valid_uuid

    def test_http_client_provided_session_id(self):
        """Test that HTTP endpoint uses client-provided session ID."""
        # Create a unique session ID for this test
        client_session_id = f"test_session_{uuid.uuid4()}"

        # Send a POST request with the session ID
        response = requests.post(
            urljoin(self.HTTP_URL, "/chat"),
            json={
                "query": "What is LPU?",
                "personal_info": {},
                "institution_id": "lpu",
                "session_id": client_session_id
            }
        )

        # Check that the response contains the same session ID
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == client_session_id

    def test_http_generated_session_id(self):
        """Test that HTTP endpoint generates a session ID if not provided."""
        # Send a POST request without a session ID
        response = requests.post(
            urljoin(self.HTTP_URL, "/chat"),
            json={
                "query": "What is LPU?",
                "personal_info": {},
                "institution_id": "lpu"
                # No session_id
            }
        )

        # Check that the response contains a generated session ID
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"].startswith("http_")

        # Verify it's a valid UUID
        session_id = data["session_id"][5:]  # Remove "http_" prefix
        try:
            uuid.UUID(session_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False
        assert is_valid_uuid

    @pytest.mark.asyncio
    async def test_websocket_session_persistence(self):
        """Test that session persists across WebSocket connections."""
        # Create a unique session ID for this test
        client_session_id = f"test_session_{uuid.uuid4()}"

        # First connection: Ask a question
        async with websockets.connect(self.WS_URL) as websocket:
            # Send a message with the session ID
            await websocket.send(json.dumps({
                "query": "What is your name?",
                "personal_info": {},
                "institution_id": "lpu",
                "message_id": 1,
                "session_id": client_session_id
            }))

            # Receive responses until we get the last one
            while True:
                response = json.loads(await websocket.recv())
                if response.get("is_last", False):
                    break

        # Wait a moment to ensure the server processes the message
        await asyncio.sleep(1)

        # Second connection: Ask about previous question
        async with websockets.connect(self.WS_URL) as websocket:
            # Send a message with the same session ID
            await websocket.send(json.dumps({
                "query": "What was my previous question?",
                "personal_info": {},
                "institution_id": "lpu",
                "message_id": 2,
                "session_id": client_session_id
            }))

            # Receive responses until we get the last one
            response_content = ""
            while True:
                response = json.loads(await websocket.recv())
                if response.get("type") == "response":
                    response_content += response.get("content", "")
                if response.get("is_last", False):
                    break

            # Check that the response mentions the previous question
            assert "What is your name" in response_content
