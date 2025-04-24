from datetime import datetime
import json
import logging
from typing import List, Dict, Optional, Protocol, Union, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

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

# In-memory implementation
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

    def get_context(self) -> str:
        if not self.conversation_history:
            return ""
        context = "Previous conversation context:\n"
        for entry in self.conversation_history:
            context += f"Q: {entry['question']}\nA: {entry['answer']}\n\n"
        return context

    def get_previous_question(self) -> Optional[str]:
        if self.conversation_history:
            return self.conversation_history[-1]["question"]
        return None

    def clear(self) -> None:
        self.conversation_history = []

# For backward compatibility
ConversationMemory = InMemoryConversationMemory