from dataclasses import dataclass

@dataclass
class WorldInfo:
    id: int
    prompt_id: int
    keywords: str
    content: str