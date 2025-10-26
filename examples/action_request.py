from pydantic import BaseModel, Field
from typing import List, Type, Optional
from .session_schemas import SessionState
from .base import SchemaModel

class ChatMessage(SchemaModel):
    """A single message in the chat history."""
    role: str = Field(..., description="The role of the speaker (e.g., 'user', 'assistant').")
    content: str = Field(..., description="The content of the message.")

class ActionRequest(SchemaModel):
    """
    Represents the data sent to the LLM to request the next action.
    """
    player_input: Optional[str] = Field(None, description="The raw input from the player for their turn. Optional during initial setup phases.")
    game_state: Optional[SessionState] = Field(None, description="A snapshot of the current game state, including mode, entities, and scene details. Optional during initial setup phases.")
    available_actions: Optional[List[str]] = Field(None, description="A list of possible actions the AI can take, defined by the OperationType enum. Optional during initial setup phases.")
    
    # Fields for LLM interaction
    instruction: str = Field(..., description="The specific instruction or prompt for the LLM.")
    response_schema: Optional[Type[BaseModel]] = Field(None, description="The Pydantic schema the LLM should use for its structured response.")
    context_data: Optional[str] = Field(None, description="Additional context data for the LLM, relevant to the current phase, as a JSON string.")
    chat_history: List[ChatMessage] = Field(..., description="The history of the conversation with the LLM for the current turn/phase.")
