import logging
import re
from typing import List, Any, Optional
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
        extra_tags: Optional[List[str]] = None,
    ) -> dict[str, List[Any]]:
        """
        Retrieve relevant memories using Tag Funnel and Dual-System Retrieval.
        Returns a dictionary categorized by kind (rule, lore, episodic, etc).
        """
        if not session or not session.id:
            return {}

        active_tags = set(extra_tags or [])
        if hasattr(session, "game_mode") and session.game_mode:
            active_tags.add(session.game_mode.lower())

        # Extract keywords from recent messages
        query_parts = []
        if len(recent_messages) >= 2:
            last_ai = next((m for m in reversed(recent_messages[:-1]) if m.role == "assistant"), None)
            if last_ai and last_ai.content:
                query_parts.append(last_ai.content[-3000:])
        if recent_messages and recent_messages[-1].role == "user":
            query_parts.append(recent_messages[-1].content)

        recent_text = " ".join(query_parts) if query_parts else "Start of session"
        keywords = self.extract_keywords(recent_text)
        active_tags.update(keywords)

        # Harvest tags from last N TurnMetadata entries
        # We need the current round number (approximate based on message history)
        history = session.get_history() if hasattr(session, "get_history") else recent_messages
        current_round = len(history) // 2
        try:
            recent_metadata = self.db.turn_metadata.get_range(
                session.id,
                start_round=max(0, current_round - 2),
                end_round=current_round,
            )
            for meta in recent_metadata:
                active_tags.update(meta.get("tags", []))
        except Exception as e:
            self.logger.warning(f"Failed to fetch recent metadata tags: {e}")

        sem_hits = []
        # Vector-Assisted Expansion (The Semantic Bridge) for tags and hit IDs
        if self.vs:
            try:
                sem_hits = self.vs.search_memories(session.id, recent_text, k=15, min_priority=1)
                for h in sem_hits:
                    active_tags.update(h.get("tags", []))
            except Exception as e:
                self.logger.warning(f"Vector search failed: {e}")

        # === 1. CODEX RETRIEVAL (Rules, Lore, User Preferences) ===
        codex_kinds = ["rule", "lore", "user_pref"]
        # Convert active_tags to lower case for consistent matching
        active_tags = {t.lower() for t in active_tags}
        
        candidates_codex = self.db.memories.query(
            session.id, kind=codex_kinds, tags=list(active_tags)[:15], limit=50
        )
        # Add a blanket query to make sure priority 4+ rules/lore are considered even if tags miss slightly
        high_pri_codex = self.db.memories.query(session.id, kind=codex_kinds, limit=20)
        candidates_codex_dict = {m.id: m for m in candidates_codex + high_pri_codex}

        scored_codex = []
        for mem in candidates_codex_dict.values():
            score = mem.priority * 100
            mem_tags = {t.lower() for t in mem.tags_list()}
            score += len(active_tags & mem_tags) * 50
            if any(kw in mem.content.lower() for kw in keywords):
                score += 30
            # Semantic boost for codex
            if any(h["memory_id"] == mem.id for h in sem_hits):
                score += 100
            if score > 50: # Must have some relevance or high priority
                scored_codex.append((score, mem))
        
        scored_codex.sort(key=lambda x: x[0], reverse=True)
        final_codex = [m for s, m in scored_codex]

        # === 2. CHRONICLE RETRIEVAL (Episodic) ===
        episodic_mems = self.db.memories.query(session.id, kind="episodic", limit=50) # fetch most recent/highest prio
        candidate_ids_ep = {m.id for m in episodic_mems}
        hit_ids_ep = {h["memory_id"] for h in sem_hits if h["memory_id"] in candidate_ids_ep}
        
        # Build Chat History Fingerprint for Deduplication
        history_words = set(self.extract_keywords(" ".join(m.content for m in history[-10:] if m.content)))
        
        scored_episodic = []
        for mem in episodic_mems:
            score = 0
            if mem.id in hit_ids_ep: 
                score += 100
            if mem.priority >= 4: 
                score += 50
            
            # Keyword overlap boost
            mem_words = set(self.extract_keywords(mem.content))
            score += len(mem_words & set(keywords)) * 15
        
            # INVERTED RECENCY: Boost older memories
            try:
                created = datetime.fromisoformat(mem.created_at)
                age_days = (datetime.now() - created).days
                if age_days >= 1:
                    score += min(age_days * 2, 30) # Max +30 for old memories
            except Exception:
                pass
        
            # DEDUPLICATION: Penalize if already in recent memory
            overlap_ratio = len(mem_words & history_words) / max(len(mem_words), 1)
            if overlap_ratio > 0.6:
                score -= 200 # Kill it
                
            if score > 0:
                scored_episodic.append((score, mem))

        scored_episodic.sort(key=lambda x: x[0], reverse=True)
        final_episodic = [m for s, m in scored_episodic[:3]] # Top 3 limit for episodic

        # Organize budgets (e.g. max 3 rule, 2 lore, 2 user_pref)
        result_dict = {"rule": [], "lore": [], "user_pref": [], "episodic": final_episodic}
        budgets = {"rule": 5, "lore": 5, "user_pref": 2}
        for mem in final_codex:
            if len(result_dict[mem.kind]) < budgets.get(mem.kind, 2):
                result_dict[mem.kind].append(mem)

        # Filter out empty lists
        return {k: v for k, v in result_dict.items() if v}

    def format_for_prompt(
        self, categorized_memories: dict[str, List[Any]], title: str = "RETRIEVED KNOWLEDGE"
    ) -> str:
        if not categorized_memories:
            return ""
            
        lines = []
        if categorized_memories.get('rule') or categorized_memories.get('user_pref'):
            lines.append("# ACTIVE CONSTRAINTS #")
            for m in categorized_memories.get('rule', []):
                tags = f" [{', '.join(m.tags_list())}]" if m.tags_list() else ""
                lines.append(f"⚖️ {m.content}{tags}")
            for m in categorized_memories.get('user_pref', []):
                lines.append(f"⚙️ {m.content}")
            lines.append("")
                
        if categorized_memories.get('lore'):
            lines.append("# WORLD LORE #")
            for m in categorized_memories.get('lore', []):
                tags = f" [{', '.join(m.tags_list())}]" if m.tags_list() else ""
                lines.append(f"📜 {m.content}{tags}")
            lines.append("")
                
        if categorized_memories.get('episodic'):
            lines.append("# RECALLED EVENTS #")
            for m in categorized_memories.get('episodic', []):
                lines.append(f"📖 {m.content}")
                
        return "\n".join(lines).strip()

