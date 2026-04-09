import functools
import logging
import re
from datetime import datetime
from typing import Any

import nltk

from app.models.message import Message
from app.models.vocabulary import WORLD_GEN_TAG, MemoryKind

# Retrieval and Budget Limits
VS_FETCH_LIMIT = 50
VS_MIN_SIMILARITY_THRESHOLD = 0.45
DB_FETCH_LIMIT_TAGS = 50
DB_FETCH_LIMIT_PRIORITY = 10
DB_FETCH_LIMIT_EPISODIC = 50

# General Scoring Constants
CODEX_PRIORITY_BUMP = 30
TAG_OVERLAP_BONUS = 40
KEYWORD_RELEVANCE_BONUS = 30
SEMANTIC_HIT_BONUS = 100

# FTS Scoring Constants
FTS_HIT_BONUS = 80
FTS_MULTIPLIER = 10

# Specific Codex Constants
MIN_CODEX_SCORE_THRESHOLD = 30

# Specific Episodic Constants
MIN_EPISODIC_SCORE_THRESHOLD = 0
EPISODIC_PRIORITY_BONUS = 50
EPISODIC_RECENCY_MULTIPLIER = 2
EPISODIC_RECENCY_MAX = 30
EPISODIC_DEDUP_THRESHOLD = 0.6
EPISODIC_DEDUP_PENALTY = 200

# Tags that are applied universally and provide zero discriminative value for retrieval
NON_DISCRIMINATIVE_TAGS = {WORLD_GEN_TAG}


class MemoryRetriever:
    """Retrieves and formats relevant memories."""

    def __init__(self, db_manager, vector_store, logger: logging.Logger | None = None):
        self.db = db_manager
        self.vs = vector_store
        self.logger = logger or logging.getLogger(__name__)

        # Initialize NLTK safely
        self.nltk_ready = False
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('punkt_tab', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            nltk.download('averaged_perceptron_tagger_eng', quiet=True)
            self.nltk_ready = True
        except Exception as e:
            self.logger.warning(f"Failed to initialize NLTK: {e}. Falling back to regex.")

        # Create an instance-bound LRU cache to drastically speed up repetitive Episodic checks
        self._cached_extract = functools.lru_cache(maxsize=200)(self._extract_keywords_internal)

    def extract_keywords(self, text: str, min_length: int = 3) -> list[str]:
        return self._cached_extract(text, min_length)

    def _extract_keywords_internal(self, text: str, min_length: int = 3) -> list[str]:
        # Process with NLTK using fast regex tokenization instead of the slow word_tokenize
        words = re.findall(r"\b\w+\b", text)
        stop_words = {
            "the", "and", "but", "for", "not", "with", "this", "that", "from",
            "have", "been", "are", "was", "were", "what", "how", "why", "you",
            "your", "will", "can", "just", "like", "into", "over", "then",
        }
        words = list({w for w in words if len(w) >= min_length and w not in stop_words})

        if not words:
            return []

        if not self.nltk_ready:
            self.logger.warning("!!NLTK not ready. Falling back to regex.")
            return words

        tagged = nltk.pos_tag(words)

        # NLTK Penn Treebank tags for Nouns and Verbs
        valid_pos = {"NN", "NNS", "NNP", "NNPS", "VB", "VBD", "VBG", "VBN", "VBP", "VBZ"}

        return list({
            w for w, pos in tagged
            if pos in valid_pos and w not in stop_words
            and len(w) >= min_length
            and w.isalpha()
        })

    def _fetch_codex_kind(
        self,
        session_id: int,
        kind: MemoryKind,
        active_tags: set[str],
        keywords: list[str],
        sem_hits: list[dict[str, Any]],
        fts_hits: dict[int, dict[str, Any]],
        exclude_ids: list[int] | None,
        limit: int,
    ) -> list[Any]:
        candidates: dict[int, Any] = {}

        # 1. Fetch natively from Vector Hits
        hit_ids = {h["memory_id"] for h in sem_hits}
        for hid in hit_ids:
            mem = self.db.memories.get_by_id(hid)
            if mem and mem.kind == kind:
                candidates[mem.id] = mem

        # 2. Fetch natively from FTS Hits
        for data in fts_hits.values():
            mem = data["mem"]
            if mem and mem.kind == kind:
                candidates[mem.id] = mem

        # 3. Fetch from DB by tags
        if active_tags:
            tag_mems = self.db.memories.query(session_id, kind=kind, tags=list(active_tags), limit=DB_FETCH_LIMIT_TAGS)
            for m in tag_mems:
                candidates[m.id] = m

        # 4. Fetch highest priority natively
        high_pri = self.db.memories.query(session_id, kind=kind, limit=DB_FETCH_LIMIT_PRIORITY)
        for m in high_pri:
            candidates[m.id] = m

        scored = []
        for mem in candidates.values():
            if exclude_ids and mem.id in exclude_ids:
                continue

            # Flat priority bump to prevent it from dominating relevance
            score = 0
            if mem.priority >= 4:
                score += CODEX_PRIORITY_BUMP

            mem_tags = {t.lower() for t in mem.tags_list()}
            score += len(active_tags & mem_tags) * TAG_OVERLAP_BONUS

            # Keyword overlap boost (Legacy NLTK intersection - kept as fallback/supplement)
            if keywords:
                mem_words = set(self.extract_keywords(mem.content))
                overlap = len(set(keywords) & mem_words)
                score += overlap * KEYWORD_RELEVANCE_BONUS

            # Semantic Boost
            if mem.id in hit_ids:
                score += SEMANTIC_HIT_BONUS

            # FTS BM25 Boost
            if mem.id in fts_hits:
                score += FTS_HIT_BONUS + (fts_hits[mem.id]["score"] * FTS_MULTIPLIER)

            if score >= MIN_CODEX_SCORE_THRESHOLD: # Minimum filter
                scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for s, m in scored[:limit]]

    def get_relevant(
        self,
        session,
        recent_messages: list[Message],
        extra_tags: list[str] | None = None,
        kinds: list[MemoryKind] | None = None,
        limit: int | None = None,
        exclude_ids: list[int] | None = None,
        explicit_query: str | None = None,
    ) -> dict[str, list[Any]]:
        """
        Retrieve relevant memories using Tag Funnel and Dual-System Retrieval.
        Returns a dictionary categorized by kind (rule, lore, episodic, etc).
        """
        if not session or not session.id:
            return {}

        # 1. EXTRACT OR USE QUERY
        fts_search_text = ""
        keywords = []

        if explicit_query:
            # If a tool provides a specific search string, we use it directly for FTS
            fts_search_text = explicit_query
            # We still might want keywords for legacy scoring bits if needed,
            # but usually explicit_query is enough
        else:
            # Passive retrieval path: build query from recent history
            query_parts = []
            if recent_messages and len(recent_messages) >= 2:
                last_ai = next((m for m in reversed(recent_messages[:-1]) if m.role == "assistant"), None)
                if last_ai and last_ai.content:
                    query_parts.append(last_ai.content[:500])

            if recent_messages and recent_messages[-1].role == "user":
                query_parts.append(recent_messages[-1].content or "")

            recent_text = "\n\n".join(query_parts) if query_parts else "Start of session"
            keywords = self.extract_keywords(recent_text)
            fts_search_text = " ".join(keywords)

        # 2. RUN SEARCHES (FTS + Vector)
        fts_hits: dict[int, dict[str, Any]] = {}
        if fts_search_text:
            try:
                bm25_results = self.db.memories.search_bm25(session.id, fts_search_text, limit=DB_FETCH_LIMIT_PRIORITY)
                for mem, score in bm25_results:
                    fts_hits[mem.id] = {"mem": mem, "score": score}
            except Exception as e:
                self.logger.warning(f"FTS search failed: {e}")

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
                raw_hits = self.vs.search_memories(session.id, recent_text, k=VS_FETCH_LIMIT, min_priority=1)
                for h in raw_hits:
                    # ChromaDB hnsw:space=cosine returns distance = 1.0 - similarity
                    similarity = 1.0 - h.get("distance", 1.0)
                    if similarity >= VS_MIN_SIMILARITY_THRESHOLD:
                        sem_hits.append(h)
                        active_tags.update(h.get("tags", []))
            except Exception as e:
                self.logger.warning(f"Vector search failed: {e}")

        # Finalize tag set for database query, stripping non-discriminative tags
        active_tags = {t.lower() for t in active_tags} - NON_DISCRIMINATIVE_TAGS
        self.logger.info(f"Active retrieval tags: {active_tags}")

        # 3. CODEX RETRIEVAL (Rules, Lore, User Preferences)
        codex_kinds = [MemoryKind.RULE, MemoryKind.LORE, MemoryKind.USER_PREF]
        if kinds is not None:
             codex_kinds = [k for k in codex_kinds if k in kinds]

        result_dict: dict[MemoryKind, list[Any]] = {
            MemoryKind.RULE: [],
            MemoryKind.LORE: [],
            MemoryKind.USER_PREF: [],
            MemoryKind.SEMANTIC: [],
            MemoryKind.EPISODIC: []
        }

        # Determine budget per kind
        if limit is not None:
             budgets = {k: limit for k in codex_kinds}
             episodic_limit = limit
        else:
             budgets = {MemoryKind.RULE: 4, MemoryKind.LORE: 6, MemoryKind.SEMANTIC: 1, MemoryKind.USER_PREF: 1}
             episodic_limit = 3

        for k in codex_kinds:
            result_dict[k] = self._fetch_codex_kind(
                session.id, k, active_tags, keywords, sem_hits, fts_hits, exclude_ids, limit=budgets.get(k, 2)
            )

        # 4. CHRONICLE RETRIEVAL (Episodic)
        if kinds is None or MemoryKind.EPISODIC in kinds:
            candidates_ep: dict[int, Any] = {}

            hit_ids = {h["memory_id"] for h in sem_hits}
            for hid in hit_ids:
                mem = self.db.memories.get_by_id(hid)
                if mem and mem.kind == MemoryKind.EPISODIC:
                    candidates_ep[mem.id] = mem

            # Fetch natives from FTS Hits (Episodic)
            for data in fts_hits.values():
                mem = data["mem"]
                if mem and mem.kind == MemoryKind.EPISODIC:
                    candidates_ep[mem.id] = mem

            # Fetch candidate episodic memories
            episodic_mems = self.db.memories.query(session.id, kind=MemoryKind.EPISODIC, limit=DB_FETCH_LIMIT_EPISODIC)
            for m in episodic_mems:
                candidates_ep[m.id] = m

            hit_ids_ep = {m.id for m in candidates_ep.values() if m.id in hit_ids}
            fts_ids_ep = {m.id for m in candidates_ep.values() if m.id in fts_hits}

            # Create history fingerprint for deduplication
            history_mems = [m for m in history if m.content]
            history_content = " ".join(str(m.content) for m in history_mems[-10:] if m.content is not None)
            history_words = set(self.extract_keywords(history_content))

            scored_episodic = []
            for mem in candidates_ep.values():
                if exclude_ids and mem.id in exclude_ids:
                    continue
                score = 0
                if mem.id in hit_ids_ep:
                    score += SEMANTIC_HIT_BONUS

                if mem.id in fts_ids_ep:
                    score += FTS_HIT_BONUS + (fts_hits[mem.id]["score"] * FTS_MULTIPLIER)

                if mem.priority >= 4:
                    score += EPISODIC_PRIORITY_BONUS

                # Keyword overlap boost
                mem_words = set(self.extract_keywords(mem.content))
                if keywords:
                     overlap = len(set(keywords) & mem_words)
                     score += overlap * KEYWORD_RELEVANCE_BONUS

                # Recency inversion
                try:
                    created = datetime.fromisoformat(mem.created_at)
                    age_days = (datetime.now() - created).days
                    if age_days >= 1:
                        score += min(age_days * EPISODIC_RECENCY_MULTIPLIER, EPISODIC_RECENCY_MAX)
                except Exception:
                    pass

                # Deduplication: Penalize if already clearly in recent history
                overlap_ratio = len(mem_words & history_words) / max(len(mem_words), 1)
                if overlap_ratio > EPISODIC_DEDUP_THRESHOLD:
                    score -= EPISODIC_DEDUP_PENALTY

                if score > MIN_EPISODIC_SCORE_THRESHOLD:
                    scored_episodic.append((score, mem))

            scored_episodic.sort(key=lambda x: x[0], reverse=True)
            result_dict[MemoryKind.EPISODIC] = [m for s, m in scored_episodic[:episodic_limit]]

        # 5. ORGANIZE AND BUDGET
        # Final pass if limit was global (sum of all results)
        if limit is not None:
            all_mems = []
            for k in [MemoryKind.RULE, MemoryKind.LORE, MemoryKind.USER_PREF, MemoryKind.EPISODIC]:
                all_mems.extend(result_dict.get(k, []))

            if len(all_mems) > limit:
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
        self, categorized_memories: dict[str, list[Any]], title: str = "# KNOWLEDGE AND MEMORIES\n"
    ) -> str:
        if not categorized_memories:
            return ""

        lines = []
        if categorized_memories.get(MemoryKind.RULE) or categorized_memories.get(MemoryKind.USER_PREF):
            lines.append("## GAME RULES REMINDERS\n")
            for m in categorized_memories.get(MemoryKind.RULE, []):
                tags = f" [{', '.join(m.tags_list())}]" if m.tags_list() else ""
                lines.append(f"⚖️ {m.content}{tags}")
            for m in categorized_memories.get(MemoryKind.USER_PREF, []):
                lines.append(f"⚙️ {m.content}")
            lines.append("")

        if categorized_memories.get(MemoryKind.LORE):
            lines.append("## WORLD LORE SAMPLES\n")
            for m in categorized_memories.get(MemoryKind.LORE, []):
                tags = f" [{', '.join(m.tags_list())}]" if m.tags_list() else ""
                lines.append(f"📜 {m.content}{tags}")
            lines.append("")

        if categorized_memories.get(MemoryKind.EPISODIC):
            lines.append("## RECALLED PAST EVENTS\n")
            for m in categorized_memories.get(MemoryKind.EPISODIC, []):
                lines.append(f"📖 {m.content}")

        return "\n".join(lines).strip()

