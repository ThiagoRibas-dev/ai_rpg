from dataclasses import dataclass

@dataclass
class GameSession:
    id: int
    name: str
    session_data: str
    prompt_id: int
