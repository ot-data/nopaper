"""
Unit tests for session ID management.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from starlette.websockets import WebSocketState

# Import the WebSocket endpoint function
from backend.main_fastapi import websocket_endpoint, http_chat, ChatRequest

@pytest.mark.unit
class TestSessionIdManagement:
    """Test session ID management."""

    @pytest.mark.asyncio
    async def test_websocket_client_provided_session_id(self):
        """Test that WebSocket endpoint uses client-provided session ID."""
        # Create a mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.state = WebSocketState.CONNECTED
        
        # Setup the receive_json method to return a message with a session_id
        client_session_id = "client_session_123"
        mock_websocket.receive_json.side_effect = [
            {
                "query": "Test query",
                "personal_info": {},
                "institution_id": "lpu",
                "message_id": 1,
                "session_id": client_session_id
            },
            Exception("Stop the loop")  # To break out of the infinite loop
        ]
        
        # Mock the generate_response function
        with patch("backend.main_fastapi.generate_response") as mock_generate_response:
            mock_generate_response.return_value = {
                "responses": [{"type": "response", "content": "Test response"}]
            }
            
            # Call the WebSocket endpoint
            try:
                await websocket_endpoint(mock_websocket)
            except Exception:
                pass
            
            # Check that generate_response was called with the client-provided session_id
            mock_generate_response.assert_called_once()
            args, kwargs = mock_generate_response.call_args
            assert args[3] == client_session_id  # session_id is the 4th argument

    @pytest.mark.asyncio
    async def test_websocket_generated_session_id(self):
        """Test that WebSocket endpoint generates a session ID if not provided."""
        # Create a mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.state = WebSocketState.CONNECTED
        
        # Setup the receive_json method to return a message without a session_id
        mock_websocket.receive_json.side_effect = [
            {
                "query": "Test query",
                "personal_info": {},
                "institution_id": "lpu",
                "message_id": 1
                # No session_id
            },
            Exception("Stop the loop")  # To break out of the infinite loop
        ]
        
        # Mock the generate_response function
        with patch("backend.main_fastapi.generate_response") as mock_generate_response:
            mock_generate_response.return_value = {
                "responses": [{"type": "response", "content": "Test response"}]
            }
            
            # Call the WebSocket endpoint
            try:
                await websocket_endpoint(mock_websocket)
            except Exception:
                pass
            
            # Check that generate_response was called with a generated session_id
            mock_generate_response.assert_called_once()
            args, kwargs = mock_generate_response.call_args
            assert args[3].startswith("ws_")  # session_id is the 4th argument
            
            # Verify it's a valid UUID
            session_id = args[3][3:]  # Remove "ws_" prefix
            try:
                uuid.UUID(session_id)
                is_valid_uuid = True
            except ValueError:
                is_valid_uuid = False
            assert is_valid_uuid

    @pytest.mark.asyncio
    async def test_http_client_provided_session_id(self):
        """Test that HTTP endpoint uses client-provided session ID."""
        # Create a mock request
        client_session_id = "client_session_123"
        request = ChatRequest(
            query="Test query",
            personal_info={},
            institution_id="lpu",
            session_id=client_session_id
        )
        
        # Mock the generate_response function
        with patch("backend.main_fastapi.generate_response") as mock_generate_response:
            mock_generate_response.return_value = {
                "responses": [{"type": "response", "content": "Test response"}]
            }
            
            # Call the HTTP endpoint
            await http_chat(request)
            
            # Check that generate_response was called with the client-provided session_id
            mock_generate_response.assert_called_once()
            args, kwargs = mock_generate_response.call_args
            assert args[3] == client_session_id  # session_id is the 4th argument

    @pytest.mark.asyncio
    async def test_http_generated_session_id(self):
        """Test that HTTP endpoint generates a session ID if not provided."""
        # Create a mock request without a session_id
        request = ChatRequest(
            query="Test query",
            personal_info={},
            institution_id="lpu"
            # No session_id
        )
        
        # Mock the generate_response function
        with patch("backend.main_fastapi.generate_response") as mock_generate_response:
            mock_generate_response.return_value = {
                "responses": [{"type": "response", "content": "Test response"}]
            }
            
            # Call the HTTP endpoint
            await http_chat(request)
            
            # Check that generate_response was called with a generated session_id
            mock_generate_response.assert_called_once()
            args, kwargs = mock_generate_response.call_args
            assert args[3].startswith("http_")  # session_id is the 4th argument
            
            # Verify it's a valid UUID
            session_id = args[3][5:]  # Remove "http_" prefix
            try:
                uuid.UUID(session_id)
                is_valid_uuid = True
            except ValueError:
                is_valid_uuid = False
            assert is_valid_uuid
