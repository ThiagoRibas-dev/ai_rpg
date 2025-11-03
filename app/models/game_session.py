from dataclasses import dataclass

@dataclass
class GameSession:
    id: int
    name: str
    session_data: str
    prompt_id: int
    memory: str = ""
    authors_note: str = ""
    game_time: str = "Day 1, Dawn"
    game_mode: str = "SETUP" # Added for Session Zero
