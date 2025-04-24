"""
Redis-backed implementation of conversation memory.
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

# Use absolute import to avoid module structure issues
try:
    from backend.memory import BaseConversationMemory
except ImportError:
    # Fallback for direct script execution
    from memory import BaseConversationMemory

logger = logging.getLogger(__name__)

class RedisConversationMemory(BaseConversationMemory):
    """Redis-backed implementation of conversation memory."""

    def __init__(self, session_id: str, redis_client: Any, max_history: int = 5, ttl: int = 86400):
        """
        Initialize Redis-backed conversation memory.

        Args:
            session_id: Unique identifier for the conversation session
            redis_client: Redis client instance
            max_history: Maximum number of interactions to keep in history
            ttl: Time-to-live for the session data in seconds (default: 1 day)
        """
        self.session_id = session_id
        self.redis = redis_client
        self.max_history = max_history
        self.ttl = ttl
        self.key_prefix = "conversation:"
        # Add a conversation_history property for compatibility with code that expects it
        self.conversation_history = []

    def _get_key(self) -> str:
        """Get the Redis key for this session."""
        return f"{self.key_prefix}{self.session_id}"

    def _get_history(self) -> List[Dict]:
        """Get the conversation history from Redis."""
        key = self._get_key()
        try:
            data = self.redis.get(key)
            if data:
                # If Redis client has decode_responses=True, data is already a string
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving conversation history from Redis: {e}")
        return []

    def add_interaction(self, question: str, answer: str) -> None:
        """Add a new interaction to the conversation history."""
        key = self._get_key()

        try:
            # Create interaction object
            timestamp = datetime.now()
            interaction = {
                "question": question,
                "answer": answer,
                "timestamp": timestamp.isoformat()
            }

            # Get current history
            history = self._get_history()

            # Add new interaction
            history.append(interaction)

            # Trim if needed
            if len(history) > self.max_history:
                history = history[-self.max_history:]

            # Save back to Redis
            self.redis.set(key, json.dumps(history))

            # Set expiry
            self.redis.expire(key, self.ttl)

            # Update conversation_history property for compatibility
            self.conversation_history = []
            for entry in history:
                # Convert ISO timestamp string back to datetime if needed
                entry_timestamp = entry.get("timestamp")
                if isinstance(entry_timestamp, str):
                    try:
                        entry_timestamp = datetime.fromisoformat(entry_timestamp)
                    except ValueError:
                        entry_timestamp = timestamp  # Use current timestamp as fallback

                self.conversation_history.append({
                    "question": entry["question"],
                    "answer": entry["answer"],
                    "timestamp": entry_timestamp
                })

        except Exception as e:
            logger.error(f"Error adding interaction to Redis: {e}")
            # Continue execution - the application will still work without persistence

            # Fallback to in-memory for this interaction
            self.conversation_history.append({
                "question": question,
                "answer": answer,
                "timestamp": datetime.now()
            })
            if len(self.conversation_history) > self.max_history:
                self.conversation_history.pop(0)

    def get_context(self) -> str:
        """Get the conversation context as a formatted string."""
        history = self._get_history()

        if not history:
            return ""

        context = "Previous conversation context:\n"
        for entry in history:
            context += f"Q: {entry['question']}\nA: {entry['answer']}\n\n"
        return context

    def get_previous_question(self) -> Optional[str]:
        """Get the most recent question from the conversation history."""
        history = self._get_history()

        if history:
            return history[-1]["question"]
        return None

    def clear(self) -> None:
        """Clear the conversation history."""
        key = self._get_key()
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.error(f"Error clearing conversation history from Redis: {e}")
