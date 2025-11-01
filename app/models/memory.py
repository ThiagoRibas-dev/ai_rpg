from dataclasses import dataclass
from typing import List, Optional
import json

@dataclass
class Memory:
    id: int
    session_id: int
    kind: str  # "episodic", "semantic", "lore", "user_pref"
    content: str
    priority: int  # 1-5
    tags: str  # JSON array stored as string
    created_at: str
    last_accessed: Optional[str] = None
    access_count: int = 0
    
    def tags_list(self) -> List[str]:
        """Parse tags from JSON string to list."""
        try:
            return json.loads(self.tags) if self.tags else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_tags(self, tags_list: List[str]):
        """Convert list to JSON string for storage."""
        self.tags = json.dumps(tags_list)