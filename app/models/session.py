import json
from typing import List, Optional
from app.models.message import Message


class Session:
    """
    A class to manage a single conversation session.
    """

    def __init__(
        self, session_id: str, system_prompt: str = "You are a helpful assistant."
    ):
        self.session_id = session_id
        self.id: Optional[int] = None
        self.system_prompt = system_prompt  # ✅ Store separately, not in history
        self.history: List[
            Message
        ] = []  # ✅ Start empty - only user/assistant messages

    def add_message(self, role: str, content: str):
        """Adds a message to the session history."""
        if role == "system":
            # Don't add system messages to history - update system_prompt instead
            self.system_prompt = content
        else:
            self.history.append(Message(role=role, content=content))

    def get_history(self) -> List[Message]:
        """Returns the entire conversation history (user/assistant only)."""
        return self.history

    def get_system_prompt(self) -> str:
        """Returns the system prompt."""
        return self.system_prompt

    def to_json(self) -> str:
        """Serializes the session to a JSON string."""
        return json.dumps(
            {
                "session_id": self.session_id,
                "system_prompt": self.system_prompt,  # ✅ Store separately
                "history": [message.model_dump() for message in self.history],
            }
        )

    @classmethod
    def from_json(cls, json_str: str):
        """Deserializes a session from a JSON string."""
        data = json.loads(json_str)
        session = cls(
            data["session_id"],
            system_prompt=data.get("system_prompt", "You are a helpful assistant."),
        )
        session.history = [Message(**item) for item in data["history"]]
        return session
