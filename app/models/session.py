import json
from typing import List
from app.models.message import Message

class Session:
    """
    A class to manage a single conversation session.
    """

    def __init__(self, session_id: str, system_prompt: str = "You are a helpful assistant."):
        self.session_id = session_id
        self.history: List[Message] = [Message(role="system", content=system_prompt)]

    def add_message(self, role: str, content: str):
        """Adds a message to the session history."""
        self.history.append(Message(role=role, content=content))

    def get_history(self) -> List[Message]:
        """Returns the entire conversation history."""
        return self.history

    def to_json(self) -> str:
        """Serializes the session to a JSON string."""
        return json.dumps({"session_id": self.session_id, "history": [message.__dict__ for message in self.history]})

    @classmethod
    def from_json(cls, json_str: str):
        """Deserializes a session from a JSON string."""
        data = json.loads(json_str)
        session = cls(data["session_id"])
        session.history = [Message(**item) for item in data["history"]]
        return session