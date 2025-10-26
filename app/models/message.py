from pydantic import BaseModel

class Message(BaseModel):
    """
    A class to represent a single message in the chat history.
    """
    role: str
    content: str
