from datetime import datetime
from typing import List, Dict, Optional

class ConversationMemory:
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.conversation_history: List[Dict] = []

    def add_interaction(self, question: str, answer: str):
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

    def clear(self):
        self.conversation_history = []