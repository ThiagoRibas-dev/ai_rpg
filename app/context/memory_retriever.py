import logging
import re
from typing import List, Any
from datetime import datetime
from app.models.message import Message


class MemoryRetriever:
    """Retrieves and formats relevant memories by mixing keyword, priority, recency, and semantic signals."""

    def __init__(self, db_manager, vector_store, logger: logging.Logger | None = None):
        self.db = db_manager
        self.vs = vector_store
        self.logger = logger or logging.getLogger(__name__)

    def extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        words = re.findall(r"\b\w+\b", text.lower())
        stop_words = {
            "the",
            "and",
            "but",
            "for",
            "not",
            "with",
            "this",
            "that",
            "from",
            "have",
            "been",
            "are",
            "was",
            "were",
        }
        return list({w for w in words if len(w) >= min_length and w not in stop_words})

    def get_relevant(
        self, session, recent_messages: List[Message], limit: int = 10
    ) -> List[Any]:
        if not session or not session.id:
            return []
        recent_text = (
            " ".join([m.content for m in recent_messages[-5:]])
            if recent_messages
            else ""
        )
        keywords = self.extract_keywords(recent_text)

        all_memories = self.db.memories.get_by_session(session.id) or []
        if not all_memories:
            return []

        # Semantic hits
        hit_ids = set()
        try:
            sem_hits = self.vs.search_memories(
                session.id, recent_text, k=min(12, limit * 2), min_priority=1
            )
            hit_ids = {int(h["memory_id"]) for h in sem_hits}
        except Exception:
            pass

        # Score
        scored = []
        for mem in all_memories:
            score = 0
            if mem.priority == 5:
                score += 100
            elif mem.priority == 4:
                score += 50
            elif mem.priority == 3:
                score += 20
            # keywords
            mem_text = (mem.content + " " + " ".join(mem.tags_list())).lower()
            score += sum(1 for kw in keywords if kw in mem_text) * 10
            # recency
            try:
                created = datetime.fromisoformat(mem.created_at)
                age_days = (datetime.now() - created).days
                score += max(0, 10 - age_days)
            except Exception:
                pass
            # semantic
            if mem.id in hit_ids:
                score += 50
            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [m for s, m in scored[:limit] if s > 0]
        for mem in top:
            try:
                self.db.memories.update_access(mem.id)
            except Exception:
                pass
        return top

    def format_for_prompt(self, memories: List[Any]) -> str:
        if not memories:
            return ""
        lines = ["# RELEVANT MEMORIES #"]
        kind_emoji = {
            "episodic": "📖",
            "semantic": "💡",
            "lore": "📜",
            "user_pref": "⚙️",
        }
        for mem in memories:
            emoji = kind_emoji.get(mem.kind, "ðŸ—’ï¸ ")
            stars = "â˜…" * int(mem.priority or 0)
            tags_str = f" [{', '.join(mem.tags_list())}]" if mem.tags_list() else ""
            time_str = f" (Time: {mem.fictional_time})" if mem.fictional_time else ""

            lines.append(
                f"{emoji} [{mem.kind.title()}] (Priority: {stars}, ID: {mem.id}){tags_str}{time_str}\n"
                f"   {mem.content}"
            )
        lines.append("")
        return "\n".join(lines)
