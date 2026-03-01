import logging
import re
from typing import List, Any, Optional
from datetime import datetime
from app.models.message import Message
from app.models.vocabulary import MemoryKind


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
        kinds: Optional[List[MemoryKind]] = None,
        limit: Optional[int] = None,
    ) -> dict[str, List[Any]]:
        """
        Retrieve relevant memories using Tag Funnel and Dual-System Retrieval.
        Returns a dictionary categorized by kind (rule, lore, episodic, etc).
        """
        if not session or not session.id:
            return {}

        # 1. EXTRACT PRIMARY CONTEXT
        # Fetch last message and last AI response to build the query context
        query_parts = []
        if len(recent_messages) >= 2:
            last_ai = next((m for m in reversed(recent_messages[:-1]) if m.role == "assistant"), None)
            if last_ai and last_ai.content:
                query_parts.append(last_ai.content[-3000:])
        
        if recent_messages and recent_messages[-1].role == "user":
            query_parts.append(recent_messages[-1].content)

        recent_text = " ".join(query_parts) if query_parts else "Start of session"
        keywords = self.extract_keywords(recent_text)
        
        # 2. GATHER CONTEXTUAL TAGS
        active_tags = set(extra_tags or [])

        # Fetch tags from last 2 rounds of TurnMetadata
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

        # Perform Semantic Expansion (Vector Bridge)
        sem_hits = []
        if self.vs:
            try:
                sem_hits = self.vs.search_memories(session.id, recent_text, k=100, min_priority=1)
                for h in sem_hits:
                    active_tags.update(h.get("tags", []))
            except Exception as e:
                self.logger.warning(f"Vector search failed: {e}")

        # Finalize tag set for database query
        active_tags = {t.lower() for t in active_tags}
        self.logger.info(f"Active retrieval tags: {active_tags}")

        # 3. CODEX RETRIEVAL (Rules, Lore, User Preferences)
        codex_kinds = [MemoryKind.RULE, MemoryKind.LORE, MemoryKind.USER_PREF]
        if kinds is not None:
             codex_kinds = [k for k in codex_kinds if k in kinds]

        final_codex = []
        if codex_kinds:
            # Fetch candidates based on tags OR high priority
            candidates_codex = self.db.memories.query(
                session.id, kind=codex_kinds, tags=list(active_tags), limit=100
            )
            high_pri_codex = self.db.memories.query(session.id, kind=codex_kinds, limit=100)
            
            # Merge and score
            candidates_codex_dict = {m.id: m for m in candidates_codex + high_pri_codex}
            scored_codex = []
            for mem in candidates_codex_dict.values():
                score = mem.priority * 100
                mem_tags = {t.lower() for t in mem.tags_list()}
                
                score += len(active_tags & mem_tags) * 50
                
                if any(kw in mem.content.lower() for kw in keywords):
                    score += 30
                
                if any(h["memory_id"] == mem.id for h in sem_hits):
                    score += 100
                
                if score > 50: # Minimum filter
                    scored_codex.append((score, mem))
            
            scored_codex.sort(key=lambda x: x[0], reverse=True)
            final_codex = [m for s, m in scored_codex]

        # 4. CHRONICLE RETRIEVAL (Episodic)
        final_episodic = []
        if kinds is None or MemoryKind.EPISODIC in kinds:
            # Fetch candidate episodic memories
            episodic_mems = self.db.memories.query(session.id, kind=MemoryKind.EPISODIC, limit=50)
            candidate_ids_ep = {m.id for m in episodic_mems}
            hit_ids_ep = {h["memory_id"] for h in sem_hits if h["memory_id"] in candidate_ids_ep}
            
            # Create history fingerprint for deduplication
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
            
                # Recency inversion
                try:
                    created = datetime.fromisoformat(mem.created_at)
                    age_days = (datetime.now() - created).days
                    if age_days >= 1:
                        score += min(age_days * 2, 30)
                except Exception:
                    pass
            
                # Deduplication: Penalize if already clearly in recent history
                overlap_ratio = len(mem_words & history_words) / max(len(mem_words), 1)
                if overlap_ratio > 0.6:
                    score -= 200
                    
                if score > 0:
                    scored_episodic.append((score, mem))

            scored_episodic.sort(key=lambda x: x[0], reverse=True)
            final_episodic = [m for s, m in scored_episodic[:3]]

        # 5. ORGANIZE AND BUDGET
        result_dict = {
            MemoryKind.RULE: [],
            MemoryKind.LORE: [],
            MemoryKind.USER_PREF: [],
            MemoryKind.EPISODIC: final_episodic
        }
        
        # Override default budgets if explicit limit is provided
        if limit is not None:
             default_limit = max(1, limit // len(codex_kinds)) if codex_kinds else limit
             budgets = {k: default_limit for k in codex_kinds}
             # Episodic already limited to 3 above, let's respect the limit for it too if it was requested
             if MemoryKind.EPISODIC in result_dict:
                  result_dict[MemoryKind.EPISODIC] = final_episodic[:limit]
        else:
             budgets = {MemoryKind.RULE: 5, MemoryKind.LORE: 5, MemoryKind.USER_PREF: 2}

        for mem in final_codex:
            if len(result_dict[mem.kind]) < budgets.get(mem.kind, 2):
                result_dict[mem.kind].append(mem)

        # Final pass if limit was global (sum of all results)
        if limit is not None:
            # Flatten, sort by priority if needed (but they are already sorted within kinds)
            # For now, let's just ensure we don't exceed global limit
            all_mems = []
            for k in [MemoryKind.RULE, MemoryKind.LORE, MemoryKind.USER_PREF, MemoryKind.EPISODIC]:
                all_mems.extend(result_dict.get(k, []))
            
            if len(all_mems) > limit:
                 # Truncate result_dict to meet limit
                 current_total = 0
                 new_result = {}
                 for k in [MemoryKind.RULE, MemoryKind.LORE, MemoryKind.USER_PREF, MemoryKind.EPISODIC]:
                      available = result_dict.get(k, [])
                      take = min(len(available), limit - current_total)
                      if take > 0:
                           new_result[k] = available[:take]
                           current_total += take
                 result_dict = new_result

        return {k: v for k, v in result_dict.items() if v}


    def format_for_prompt(
        self, categorized_memories: dict[str, List[Any]], title: str = "# KNOWLEDGE AND MEMORIES\n"
    ) -> str:
        if not categorized_memories:
            return ""
            
        lines = []
        if categorized_memories.get(MemoryKind.RULE) or categorized_memories.get(MemoryKind.USER_PREF):
            lines.append("## GAME RULES REMINDER\n")
            for m in categorized_memories.get(MemoryKind.RULE, []):
                tags = f" [{', '.join(m.tags_list())}]" if m.tags_list() else ""
                lines.append(f"⚖️ {m.content}{tags}")
            for m in categorized_memories.get(MemoryKind.USER_PREF, []):
                lines.append(f"⚙️ {m.content}")
            lines.append("")
                
        if categorized_memories.get(MemoryKind.LORE):
            lines.append("## WORLD LORE\n")
            for m in categorized_memories.get(MemoryKind.LORE, []):
                tags = f" [{', '.join(m.tags_list())}]" if m.tags_list() else ""
                lines.append(f"📜 {m.content}{tags}")
            lines.append("")
                
        if categorized_memories.get(MemoryKind.EPISODIC):
            lines.append("## RECALLED PAST EVENTS\n")
            for m in categorized_memories.get(MemoryKind.EPISODIC, []):
                lines.append(f"📖 {m.content}")
                
        return "\n".join(lines).strip()

