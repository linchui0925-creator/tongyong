from typing import List
from datetime import datetime
from app.core.base import Message

class ContextManager:
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.messages: List[Message] = []
    
    def add_message(self, role: str, content: str) -> Message:
        message = Message(
            role=role,
            content=content,
            created_at=datetime.now().isoformat()
        )
        self.messages.append(message)
        return message
    
    def get_messages(self) -> List[Message]:
        return self.messages
    
    def get_context_str(self) -> str:
        return "\n".join([
            f"{msg.role}: {msg.content}"
            for msg in self.messages
        ])
    
    def clear(self):
        self.messages = []
    
    def should_compress(self) -> bool:
        total_chars = sum(len(m.content) for m in self.messages)
        return total_chars > self.max_tokens * 4