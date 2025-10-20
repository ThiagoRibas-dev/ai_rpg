from dataclasses import dataclass

@dataclass
class Message:
    """
    A class to represent a single message in the chat history.
    """
    role: str
    content: str