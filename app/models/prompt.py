from dataclasses import dataclass


@dataclass
class Prompt:
    id: int
    name: str
    content: str
    initial_message: str = ""
