from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class Message(BaseModel):
    """
    A class to represent a single message in the chat history.
    Supports standard roles (user, assistant, system) and LLM-specific tool protocols.
    """
    role: str
    content: Optional[str] = None  # Content is optional for pure tool calls
    
    # For Assistant messages that call tools (OpenAI/Llama format)
    # Format: [{'id': 'call_123', 'function': {'name': 'x', 'arguments': '{}'}}]
    # We store normalized dicts here: [{'name': 'x', 'arguments': {...}, 'id': '...'}]
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    # For Tool Result messages (The Answer)
    # OpenAI requires 'tool_call_id' to link result to request.
    tool_call_id: Optional[str] = None
    
    # Some local models or Gemini use 'name' to link function results
    name: Optional[str] = None
