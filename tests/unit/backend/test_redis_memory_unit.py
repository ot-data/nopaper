"""
Unit tests for Redis memory implementation.
"""
import pytest
import json
from datetime import datetime

from backend.redis_memory import RedisConversationMemory

@pytest.mark.unit
@pytest.mark.redis
class TestRedisMemory:
    """Test Redis memory implementation."""

    def test_init(self, mock_redis_client):
        """Test initialization."""
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client,
            max_history=5,
            ttl=86400
        )
        assert memory.session_id == "test_session"
        assert memory.max_history == 5
        assert memory.ttl == 86400
        assert memory.key_prefix == "conversation:"
        assert memory.conversation_history == []

    def test_get_key(self, mock_redis_client):
        """Test _get_key method."""
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client
        )
        assert memory._get_key() == "conversation:test_session"

    def test_get_history_empty(self, mock_redis_client):
        """Test _get_history method with empty history."""
        mock_redis_client.get.return_value = None
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client
        )
        assert memory._get_history() == []

    def test_get_history_with_data(self, mock_redis_client):
        """Test _get_history method with data."""
        test_data = [
            {"question": "What is LPU?", "answer": "LPU is Lovely Professional University.", "timestamp": "2023-01-01T12:00:00"}
        ]
        mock_redis_client.get.return_value = json.dumps(test_data)
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client
        )
        assert memory._get_history() == test_data

    def test_add_interaction(self, mock_redis_client):
        """Test add_interaction method."""
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client
        )
        memory.add_interaction("What is LPU?", "LPU is Lovely Professional University.")
        
        # Check that Redis set was called
        mock_redis_client.set.assert_called_once()
        mock_redis_client.expire.assert_called_once()
        
        # Check that conversation_history was updated
        assert len(memory.conversation_history) == 1
        assert memory.conversation_history[0]["question"] == "What is LPU?"
        assert memory.conversation_history[0]["answer"] == "LPU is Lovely Professional University."
        assert isinstance(memory.conversation_history[0]["timestamp"], datetime)

    def test_get_context_empty(self, mock_redis_client):
        """Test get_context method with empty history."""
        mock_redis_client.get.return_value = None
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client
        )
        assert memory.get_context() == ""

    def test_get_context_with_data(self, mock_redis_client):
        """Test get_context method with data."""
        test_data = [
            {"question": "What is LPU?", "answer": "LPU is Lovely Professional University.", "timestamp": "2023-01-01T12:00:00"}
        ]
        mock_redis_client.get.return_value = json.dumps(test_data)
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client
        )
        expected = "Previous conversation context:\nQ: What is LPU?\nA: LPU is Lovely Professional University.\n\n"
        assert memory.get_context() == expected

    def test_get_previous_question_empty(self, mock_redis_client):
        """Test get_previous_question method with empty history."""
        mock_redis_client.get.return_value = None
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client
        )
        assert memory.get_previous_question() is None

    def test_get_previous_question_with_data(self, mock_redis_client):
        """Test get_previous_question method with data."""
        test_data = [
            {"question": "What is LPU?", "answer": "LPU is Lovely Professional University.", "timestamp": "2023-01-01T12:00:00"}
        ]
        mock_redis_client.get.return_value = json.dumps(test_data)
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client
        )
        assert memory.get_previous_question() == "What is LPU?"

    def test_clear(self, mock_redis_client):
        """Test clear method."""
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client
        )
        memory.clear()
        mock_redis_client.delete.assert_called_once_with("conversation:test_session")

    @pytest.mark.parametrize("max_history,expected_length", [
        (1, 1),
        (2, 2),
        (3, 3)
    ])
    def test_max_history(self, mock_redis_client, max_history, expected_length):
        """Test max_history parameter."""
        # Setup mock to return existing history
        existing_history = [
            {"question": f"Question {i}", "answer": f"Answer {i}", "timestamp": "2023-01-01T12:00:00"}
            for i in range(max_history)
        ]
        mock_redis_client.get.return_value = json.dumps(existing_history)
        
        memory = RedisConversationMemory(
            session_id="test_session",
            redis_client=mock_redis_client,
            max_history=max_history
        )
        
        # Add a new interaction
        memory.add_interaction("New question", "New answer")
        
        # Check that the history was trimmed
        args, kwargs = mock_redis_client.set.call_args
        saved_data = json.loads(args[1])
        assert len(saved_data) == expected_length
        assert saved_data[-1]["question"] == "New question"
        assert saved_data[-1]["answer"] == "New answer"

    @pytest.mark.integration
    def test_real_redis_integration(self, redis_client):
        """Integration test with real Redis."""
        # Skip if Redis is not available
        if redis_client is None:
            pytest.skip("Redis not available")
            
        # Create a unique session ID for this test
        import uuid
        session_id = f"test_session_{uuid.uuid4()}"
        
        # Create memory instance
        memory = RedisConversationMemory(
            session_id=session_id,
            redis_client=redis_client,
            max_history=5,
            ttl=60  # Short TTL for tests
        )
        
        # Clear any existing data
        memory.clear()
        
        # Add some interactions
        memory.add_interaction("Question 1", "Answer 1")
        memory.add_interaction("Question 2", "Answer 2")
        
        # Check that the interactions were stored
        assert memory.get_previous_question() == "Question 2"
        assert "Question 1" in memory.get_context()
        assert "Answer 1" in memory.get_context()
        assert "Question 2" in memory.get_context()
        assert "Answer 2" in memory.get_context()
        
        # Check that the data is in Redis
        key = f"conversation:{session_id}"
        data = redis_client.get(key)
        assert data is not None
        
        # Check TTL
        ttl = redis_client.ttl(key)
        assert 0 < ttl <= 60
        
        # Clear the data
        memory.clear()
        assert redis_client.get(key) is None
