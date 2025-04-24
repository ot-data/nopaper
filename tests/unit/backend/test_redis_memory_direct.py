"""
Direct test script for Redis-backed conversation memory.
This script imports the modules directly to avoid package structure issues.
"""
import sys
import os
import time
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the modules from backend
from backend.memory import BaseConversationMemory
from backend.redis_memory import RedisConversationMemory

def test_redis_memory_direct():
    """Test the Redis-backed conversation memory implementation directly."""
    try:
        import redis

        # Create Redis client
        redis_client = redis.Redis(
            host="localhost",
            port=6379,
            password="",
            db=0,
            decode_responses=True
        )

        # Test Redis connection
        ping_result = redis_client.ping()
        logger.info(f"Redis ping result: {ping_result}")

        # Create test session ID
        test_session_id = f"test_session_{int(time.time())}"
        logger.info(f"Using test session ID: {test_session_id}")

        # Create Redis memory
        redis_memory = RedisConversationMemory(
            session_id=test_session_id,
            redis_client=redis_client,
            max_history=5,
            ttl=86400  # 1 day
        )

        # Test adding interactions
        logger.info("Adding test interactions...")
        redis_memory.add_interaction("What is your name?", "I am an AI assistant.")
        redis_memory.add_interaction("How can you help me?", "I can answer questions and provide information.")

        # Test getting context
        context = redis_memory.get_context()
        logger.info(f"Context from Redis:\n{context}")

        # Test getting previous question
        prev_question = redis_memory.get_previous_question()
        logger.info(f"Previous question from Redis: {prev_question}")

        # Verify data in Redis directly
        key = f"conversation:{test_session_id}"
        raw_data = redis_client.get(key)
        logger.info(f"Raw data from Redis: {raw_data}")

        if raw_data:
            data = json.loads(raw_data)
            logger.info(f"Parsed data from Redis: {json.dumps(data, indent=2)}")

            # Check TTL
            ttl = redis_client.ttl(key)
            logger.info(f"TTL for key {key}: {ttl} seconds")

        # Test clearing memory
        logger.info("Testing clear method...")
        redis_memory.clear()

        # Verify data is cleared
        raw_data_after_clear = redis_client.get(key)
        logger.info(f"Raw data after clear: {raw_data_after_clear}")

        # Clean up
        if raw_data_after_clear:
            redis_client.delete(key)
            logger.info(f"Deleted test key: {key}")

        logger.info("Redis memory test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Error testing Redis memory: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_redis_memory_direct()
