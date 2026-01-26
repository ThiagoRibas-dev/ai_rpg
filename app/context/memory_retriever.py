import logging
import re
from typing import List, Any, Optional, Union
from datetime import datetime
from app.models.message import Message


class MemoryRetriever:
    """Retrieves and formats relevant memories."""

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
        self,
        session,
        recent_messages: List[Message],
        limit: int = 10,
        kinds: Union[str, List[str]] = None,
        extra_tags: Optional[List[str]] = None,
    ) -> List[Any]:
        """
        Retrieve relevant memories.
        Query Text = [Last Assistant Message] + [Current User Message]
        """

        if extra_tags is None:
            extra_tags = []

        if not session or not session.id:
            return []

        # --- REFINED QUERY CONSTRUCTION ---
        # Capture the "Stimulus" (Last AI) and "Response" (User)
        query_parts = []
        if len(recent_messages) >= 2:
            # Check for AI message
            last_ai = next(
                (m for m in reversed(recent_messages[:-1]) if m.role == "assistant"),
                None,
            )
            if last_ai and last_ai.content:
                query_parts.append(
                    last_ai.content[-3000:]
                )  # Limit AI noise to last 3000 chars

        # Always add User message
        if recent_messages and recent_messages[-1].role == "user":
            query_parts.append(recent_messages[-1].content)

        recent_text = " ".join(query_parts)
        if not recent_text:
            # Fallback for start of game
            recent_text = "Start of session"

        keywords = self.extract_keywords(recent_text)

        # 1. Fetch Candidates from SQL (Filtered by Kind)
        candidates = self.db.memories.query(session.id, kind=kinds, limit=100)
        if not candidates:
            return []

        candidate_ids = {m.id for m in candidates}

        # 2. Semantic Search (Boost)
        hit_ids = set()
        if self.vs:
            try:
                sem_hits = self.vs.search_memories(
                    session.id, recent_text, k=20, min_priority=1
                )
                for h in sem_hits:
                    mid = int(h["memory_id"])
                    if mid in candidate_ids:
                        hit_ids.add(mid)
            except Exception:
                pass

        # 3. Scoring
        scored = []
        for mem in candidates:
            score = 0
            # Priority
            if mem.priority >= 4:
                score += 50
            if mem.priority == 5:
                score += 50

            # Keyword Match
            mem_text = (mem.content + " " + " ".join(mem.tags_list())).lower()
            score += sum(1 for kw in keywords if kw in mem_text) * 15

            # Semantic Match
            if mem.id in hit_ids:
                score += 60

            # Extra Tags (Active Conditions / Features)
            for tag in extra_tags:
                if tag.lower() in mem.tags_list() or tag.lower() in mem.content.lower():
                    score += 100  # Huge boost for relevant rules

            # Recency (Only for episodic)
            if mem.kind == "episodic":
                try:
                    created = datetime.fromisoformat(mem.created_at)
                    age_days = (datetime.now() - created).days
                    score += max(0, 10 - age_days)
                except Exception as e:
                    self.logger.warning(f"Failed to parse memory date: {e}")
                    pass

            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for s, m in scored[:limit] if s > 0]

    def format_for_prompt(
        self, memories: List[Any], title: str = "RELEVANT MEMORIES"
    ) -> str:
        if not memories:
            return ""
        lines = [f"# {title} #"]
        kind_emoji = {
            "episodic": "📖",
            "semantic": "💡",
            "lore": "📜",
            "rule": "⚖️",
            "user_pref": "⚙️",
        }
        for mem in memories:
            emoji = kind_emoji.get(mem.kind, "•")
            tags = f" [{', '.join(mem.tags_list())}]" if mem.tags_list() else ""
            lines.append(f"{emoji} {mem.content}{tags}")

        return "\n".join(lines)
