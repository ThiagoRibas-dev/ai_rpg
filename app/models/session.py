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

    def save_to_file(self, file_path: str):
        """Saves the session history to a JSON file."""
        with open(file_path, 'w') as f:
            json.dump([message.__dict__ for message in self.history], f, indent=2)

    @classmethod
    def load_from_file(cls, file_path: str, session_id: str):
        """Loads a session history from a JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        session = cls(session_id)
        session.history = [Message(**item) for item in data]
        return session