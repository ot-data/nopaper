"""
Simple test script for Redis connection.
"""
import sys
import os
import time
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_redis_connection():
    """Test basic Redis connection and operations."""
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
        
        # Create test key
        test_key = f"test_key_{int(time.time())}"
        test_data = {
            "timestamp": time.time(),
            "message": "Hello Redis!",
            "test_array": ["item1", "item2", "item3"]
        }
        
        # Set test data
        redis_client.set(test_key, json.dumps(test_data))
        logger.info(f"Set test data with key: {test_key}")
        
        # Get test data
        retrieved_data = redis_client.get(test_key)
        logger.info(f"Retrieved data: {retrieved_data}")
        
        if retrieved_data:
            parsed_data = json.loads(retrieved_data)
            logger.info(f"Parsed data: {json.dumps(parsed_data, indent=2)}")
        
        # Set TTL
        redis_client.expire(test_key, 60)  # 60 seconds
        ttl = redis_client.ttl(test_key)
        logger.info(f"TTL for key {test_key}: {ttl} seconds")
        
        # Clean up
        redis_client.delete(test_key)
        logger.info(f"Deleted test key: {test_key}")
        
        logger.info("Redis connection test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error testing Redis connection: {e}")
        return False

if __name__ == "__main__":
    test_redis_connection()
