import json
from dataclasses import dataclass


@dataclass
class Memory:
    id: int
    session_id: int
    kind: str
    content: str
    priority: int
    tags: str
    created_at: str
    fictional_time: str | None = None
    last_accessed: str | None = None
    access_count: int = 0

    def tags_list(self) -> list[str]:
        """Parse tags from JSON string to list."""
        try:
            return json.loads(self.tags) if self.tags else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags(self, tags_list: list[str]):
        """Convert list to JSON string for storage."""
        self.tags = json.dumps(tags_list)
