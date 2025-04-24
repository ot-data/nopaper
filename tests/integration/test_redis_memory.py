"""
Integration tests for Redis memory implementation.
"""
import pytest
import uuid
import time
import json

from backend.redis_memory import RedisConversationMemory

@pytest.mark.integration
@pytest.mark.redis
class TestRedisMemoryIntegration:
    """Integration tests for Redis memory implementation."""

    def test_add_and_retrieve(self, redis_client):
        """Test adding and retrieving interactions."""
        # Create a unique session ID for this test
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
        
        # Parse the data and check its contents
        parsed_data = json.loads(data)
        assert len(parsed_data) == 2
        assert parsed_data[0]["question"] == "Question 1"
        assert parsed_data[0]["answer"] == "Answer 1"
        assert parsed_data[1]["question"] == "Question 2"
        assert parsed_data[1]["answer"] == "Answer 2"
        
        # Clean up
        memory.clear()

    def test_max_history(self, redis_client):
        """Test max_history parameter."""
        # Create a unique session ID for this test
        session_id = f"test_session_{uuid.uuid4()}"
        
        # Create memory instance with max_history=3
        memory = RedisConversationMemory(
            session_id=session_id,
            redis_client=redis_client,
            max_history=3,
            ttl=60  # Short TTL for tests
        )
        
        # Clear any existing data
        memory.clear()
        
        # Add more interactions than max_history
        memory.add_interaction("Question 1", "Answer 1")
        memory.add_interaction("Question 2", "Answer 2")
        memory.add_interaction("Question 3", "Answer 3")
        memory.add_interaction("Question 4", "Answer 4")
        memory.add_interaction("Question 5", "Answer 5")
        
        # Check that only the last max_history interactions were stored
        context = memory.get_context()
        assert "Question 1" not in context
        assert "Question 2" not in context
        assert "Question 3" in context
        assert "Question 4" in context
        assert "Question 5" in context
        
        # Check that the previous question is correct
        assert memory.get_previous_question() == "Question 5"
        
        # Clean up
        memory.clear()

    def test_ttl(self, redis_client):
        """Test TTL (time-to-live) parameter."""
        # Create a unique session ID for this test
        session_id = f"test_session_{uuid.uuid4()}"
        
        # Create memory instance with a very short TTL
        memory = RedisConversationMemory(
            session_id=session_id,
            redis_client=redis_client,
            max_history=5,
            ttl=2  # 2 seconds
        )
        
        # Clear any existing data
        memory.clear()
        
        # Add an interaction
        memory.add_interaction("Question", "Answer")
        
        # Check that the data is in Redis
        key = f"conversation:{session_id}"
        assert redis_client.get(key) is not None
        
        # Check TTL
        ttl = redis_client.ttl(key)
        assert 0 < ttl <= 2
        
        # Wait for TTL to expire
        time.sleep(3)
        
        # Check that the data is gone
        assert redis_client.get(key) is None
        
        # Check that get_context returns empty string
        assert memory.get_context() == ""
        
        # Check that get_previous_question returns None
        assert memory.get_previous_question() is None

    def test_clear(self, redis_client):
        """Test clear method."""
        # Create a unique session ID for this test
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
        
        # Add an interaction
        memory.add_interaction("Question", "Answer")
        
        # Check that the data is in Redis
        key = f"conversation:{session_id}"
        assert redis_client.get(key) is not None
        
        # Clear the data
        memory.clear()
        
        # Check that the data is gone
        assert redis_client.get(key) is None
