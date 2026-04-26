import functools
import logging
import re
from datetime import datetime
from typing import Any

import nltk
from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.models.message import Message
from app.models.vocabulary import WORLD_GEN_TAG, MemoryKind

# Retrieval and Budget Limits
VS_FETCH_LIMIT = 50
VS_MIN_SIMILARITY_THRESHOLD = 0.45
DB_FETCH_LIMIT_TAGS = 50
DB_FETCH_LIMIT_PRIORITY = 10
DB_FETCH_LIMIT_EPISODIC = 50

# RRF and Reranking Constants
RRF_K = 60
RERANKER_TOP_N = 30
RERANKER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"

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

        # Initialize Cross-Encoder Reranker
        self.reranker: TextCrossEncoder | None = None
        try:
            self.reranker = TextCrossEncoder(model_name=RERANKER_MODEL)
            self.logger.info(f"Initialized Cross-Encoder with {RERANKER_MODEL}")
        except Exception as e:
            self.logger.warning(f"Could not load Cross-Encoder reranker: {e}. Falling back to RRF only.")

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

    def _rrf_fuse(
        self,
        candidate_ids: set[int],
        ranked_lists: dict[str, list[int]],
    ) -> list[tuple[int, float]]:
        """
        Reciprocal Rank Fusion across multiple ranked retrieval sources.
        """
        scores: dict[int, float] = {cid: 0.0 for cid in candidate_ids}
        for _source_name, ranked_ids in ranked_lists.items():
            for rank_position, mem_id in enumerate(ranked_ids):
                if mem_id in scores:
                    scores[mem_id] += 1.0 / (RRF_K + rank_position + 1)
        return sorted(scores.items(), key=lambda item: item[1], reverse=True)

    def _rerank_candidates(
        self,
        query: str,
        candidates: list[tuple[int, Any]],  # (mem_id, Memory)
        top_n: int = RERANKER_TOP_N,
    ) -> list[Any]:
        """
        Cross-encoder reranking of top-N candidates.
        """
        if not self.reranker or not query or not candidates:
            return [mem for _, mem in candidates]

        # Limit candidates for reranking
        to_rerank = candidates[:top_n]
        remaining = candidates[top_n:]

        try:
            doc_texts = [mem.content for _, mem in to_rerank]
            # fastembed rerank returns scores for the documents
            scores = list(self.reranker.rerank(query, doc_texts))

            # Sort by reranker score
            scored_mems = sorted(
                zip(scores, [mem for _, mem in to_rerank], strict=False),
                key=lambda x: x[0], reverse=True
            )
            reranked = [mem for _, mem in scored_mems]

            # Append non-reranked as fallback
            reranked.extend([mem for _, mem in remaining])
            return reranked
        except Exception as e:
            self.logger.warning(f"Reranking failed: {e}")
            return [mem for _, mem in candidates]

    def _fetch_codex_kind(
        self,
        session_id: int,
        kind: MemoryKind,
        active_tags: set[str],
        query_text: str,
        sem_hits: list[dict[str, Any]],
        fts_hits: dict[int, dict[str, Any]],
        exclude_ids: list[int] | None,
        limit: int,
    ) -> list[Any]:
        candidates: dict[int, Any] = {}

        # 1. Gather Candidates and Sources
        # Semantic Rank
        sem_ranked = []
        for h in sem_hits:
            mem_id = h["memory_id"]
            if mem_id in (exclude_ids or []):
                continue

            # We don't fetch every memory yet if we can help it,
            # but we need to check the 'kind'
            mem = self.db.memories.get_by_id(mem_id)
            if mem and mem.kind == kind:
                candidates[mem.id] = mem
                sem_ranked.append(mem.id)

        # FTS Rank
        fts_ranked = []
        for fts_mem_id, data in fts_hits.items():
            if fts_mem_id in (exclude_ids or []):
                continue
            mem = data["mem"]
            if mem and mem.kind == kind:
                candidates[mem.id] = mem
                fts_ranked.append(mem.id)

        # Tag Overlap & Priority Ranking
        # For these, we fetch from DB to get pool of potential matches
        tag_mems = []
        if active_tags:
            tag_mems = self.db.memories.query(session_id, kind=kind, tags=list(active_tags), limit=DB_FETCH_LIMIT_TAGS)
            for m in tag_mems:
                if exclude_ids and m.id in exclude_ids:
                    continue
                candidates[m.id] = m

        high_pri = self.db.memories.query(session_id, kind=kind, limit=DB_FETCH_LIMIT_PRIORITY)
        for m in high_pri:
            if exclude_ids and m.id in exclude_ids:
                continue
            candidates[m.id] = m

        if not candidates:
            return []

        # Build Ranked Lists for RRF
        # Tag overlaps list
        tag_ranked = sorted(
            candidates.keys(),
            key=lambda mid: len(active_tags & {t.lower() for t in candidates[mid].tags_list()}),
            reverse=True
        )
        # Priority list
        pri_ranked = sorted(
            candidates.keys(),
            key=lambda mid: candidates[mid].priority,
            reverse=True
        )

        ranked_lists = {
            "semantic": sem_ranked,
            "fts": fts_ranked,
            "tags": tag_ranked,
            "priority": pri_ranked
        }

        # FUSE
        fused = self._rrf_fuse(set(candidates.keys()), ranked_lists)

        # RERANK
        mem_candidates = [(mid, candidates[mid]) for mid, score in fused]
        return self._rerank_candidates(query_text, mem_candidates, top_n=limit * 2)[:limit]

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
                session.id, k, active_tags, fts_search_text, sem_hits, fts_hits, exclude_ids, limit=budgets.get(k, 2)
            )

        # 4. CHRONICLE RETRIEVAL (Episodic)
        if kinds is None or MemoryKind.EPISODIC in kinds:
            candidates_ep: dict[int, Any] = {}

            # Gather sources
            sem_ranked_ep = []
            hit_ids = {h["memory_id"] for h in sem_hits}
            for hid in hit_ids:
                mem = self.db.memories.get_by_id(hid)
                if mem and mem.kind == MemoryKind.EPISODIC:
                    candidates_ep[mem.id] = mem
                    sem_ranked_ep.append(mem.id)

            fts_ranked_ep = []
            for _fts_id, data in fts_hits.items():
                mem = data["mem"]
                if mem and mem.kind == MemoryKind.EPISODIC:
                    candidates_ep[mem.id] = mem
                    fts_ranked_ep.append(mem.id)

            episodic_mems = self.db.memories.query(session.id, kind=MemoryKind.EPISODIC, limit=DB_FETCH_LIMIT_EPISODIC)
            for m in episodic_mems:
                if exclude_ids and m.id in exclude_ids:
                    continue
                candidates_ep[m.id] = m

            if candidates_ep:
                # History fingerprint for deduplication
                history_mems = [m for m in history if m.content]
                history_content = " ".join(str(m.content) for m in history_mems[-10:] if m.content is not None)
                history_words = set(self.extract_keywords(history_content))

                # Ranked Lists for Episodic
                # Recency Rank
                def get_age(m):
                    try:
                        return (datetime.now() - datetime.fromisoformat(m.created_at)).total_seconds()
                    except (ValueError, TypeError):
                        return 999999

                recency_ranked = sorted(candidates_ep.keys(), key=lambda mid: get_age(candidates_ep[mid]))
                # Priority Rank
                pri_ranked_ep = sorted(candidates_ep.keys(), key=lambda mid: candidates_ep[mid].priority, reverse=True)

                ranked_lists_ep = {
                    "semantic": sem_ranked_ep,
                    "fts": fts_ranked_ep,
                    "recency": recency_ranked,
                    "priority": pri_ranked_ep
                }

                # FUSE
                fused_ep = self._rrf_fuse(set(candidates_ep.keys()), ranked_lists_ep)

                # Filter and Deduplicate
                final_candidates_ep = []
                for mid, _score in fused_ep:
                    mem = candidates_ep[mid]
                    mem_words = set(self.extract_keywords(mem.content))

                    # Deduplication check
                    overlap_ratio = len(mem_words & history_words) / max(len(mem_words), 1)
                    if overlap_ratio > 0.6: # EPISODIC_DEDUP_THRESHOLD was 0.6
                        continue

                    final_candidates_ep.append((mid, mem))

                # RERANK
                result_dict[MemoryKind.EPISODIC] = self._rerank_candidates(
                    fts_search_text, final_candidates_ep, top_n=episodic_limit * 2
                )[:episodic_limit]

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

