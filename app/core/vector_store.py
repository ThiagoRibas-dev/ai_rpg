from __future__ import annotations

import logging
import os
from typing import Any, cast

import chromadb
from chromadb.config import Settings
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Manages vector embeddings for:
    1. Turn Metadata (History Search)
    2. Memories (Lore/Facts)
    3. Rules (RAG Rulebook)
    """

    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(
            path=persist_directory, settings=Settings(anonymized_telemetry=False)
        )

        # Initialize Collections
        self.turn_collection = self.client.get_or_create_collection(
            name="turn_metadata", metadata={"hnsw:space": "cosine"}
        )
        self.memories_collection = self.client.get_or_create_collection(
            name="memories", metadata={"hnsw:space": "cosine"}
        )
        # NEW: Rules Collection
        self.rules_collection = self.client.get_or_create_collection(
            name="rules", metadata={"hnsw:space": "cosine"}
        )

        # Embed Model
        model_name = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

        # Setup local cache dir for the embedding model to avoid redundant network downloads
        cache_dir = os.path.join(persist_directory, "models")
        os.makedirs(cache_dir, exist_ok=True)

        try:
            # Try loading from local cache first to avoid HF pings (offline-first)
            self.embed_model = TextEmbedding(
                model_name=model_name,
                cache_dir=cache_dir,
                local_files_only=True
            )
            logger.info(f"VectorStore loaded {model_name} from local cache: {cache_dir}")
        except Exception:
            # Fallback to online loading if local files are missing or update is needed
            logger.info(f"Model {model_name} not found locally or error occurred. Attempting to download...")
            try:
                self.embed_model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
                logger.info(f"VectorStore initialized with {model_name} (downloaded/updated in {cache_dir})")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                # Last resort fallback to default model
                self.embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", cache_dir=cache_dir)

    def _embed(self, text: str) -> list[float]:
        embeddings = list(self.embed_model.embed([text]))
        return [float(x) for x in embeddings[0].tolist()]

    # ==========================================================================
    # RULES (The New Layer)
    # ==========================================================================

    def add_rules(self, ruleset_id: int, rules: list[dict[str, Any]]):
        """
        Batch add rules to the vector store.
        rules: List of {'name': str, 'text': str, 'tags': List[str]}
        """
        if not rules:
            return

        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for i, rule in enumerate(rules):
            # Unique ID: ruleset_id + name hash or index
            doc_id = f"rule_{ruleset_id}_{i}_{hash(rule['name'])}"
            content = f"{rule['name']}: {rule['text']}"

            ids.append(doc_id)
            documents.append(content)
            embeddings.append(self._embed(content))
            metadatas.append({
                "ruleset_id": ruleset_id,
                "name": rule['name'],
                "tags": ",".join(rule.get('tags', []))
            })

        try:
            self.rules_collection.upsert(
                ids=ids,
                embeddings=embeddings,  # type: ignore[arg-type]
                metadatas=metadatas,  # type: ignore[arg-type]
                documents=documents
            )
            logger.info(f"Indexed {len(rules)} rules for Ruleset {ruleset_id}")
        except Exception as e:
            logger.error(f"Error indexing rules: {e}", exc_info=True)

    def search_rules(self, ruleset_id: int, query: str, k: int = 3) -> list[dict[str, Any]]:
        """Semantic search for rules relevant to the query."""
        if not query.strip():
            return []

        embedding = self._embed(query)

        results = self.rules_collection.query(
            query_embeddings=[embedding],  # type: ignore[arg-type]
            n_results=k,
            where={"ruleset_id": {"$eq": ruleset_id}}  # type: ignore[dict-item]
        )

        hits = []
        res_ids = results.get("ids")
        res_docs = results.get("documents")
        res_metas = results.get("metadatas")
        res_dists = results.get("distances")

        if res_ids and res_ids[0] and res_docs and res_docs[0] and res_metas and res_metas[0]:
            for i, _ in enumerate(res_ids[0]):
                hits.append({
                    "content": res_docs[0][i],
                    "name": res_metas[0][i].get("name", "Unknown") if isinstance(res_metas[0][i], dict) else "Unknown",
                    "distance": res_dists[0][i] if res_dists and res_dists[0] else 0
                })
        return hits

    # ==========================================================================
    # MEMORIES & TURNS (Existing)
    # ==========================================================================

    def add_turn(self, session_id: int, prompt_id: int, round_number: int, summary: str, tags: list[str], importance: int):
        try:
            embedding = self._embed(summary)
            doc_id = f"{session_id}_{round_number}"
            self.turn_collection.add(
                ids=[doc_id],
                embeddings=[embedding],  # type: ignore[arg-type]
                metadatas=[{
                    "session_id": session_id,
                    "prompt_id": prompt_id,
                    "round_number": round_number,
                    "summary": summary,
                    "tags": ",".join(tags),
                    "importance": importance,
                }]  # type: ignore[list-item]
            )
        except Exception as e:
            logger.error(f"Error adding turn: {e}")

    def search_relevant_turns(self, session_id: int, query_text: str, top_k: int = 5, min_importance: int = 2) -> list[dict[str, Any]]:
        embedding = self._embed(query_text)
        where_clause = cast(Any, {
            "$and": [
                {"session_id": {"$eq": session_id}},
                {"importance": {"$gte": min_importance}},
            ]
        })
        results = self.turn_collection.query(
            query_embeddings=[embedding], n_results=top_k, where=where_clause  # type: ignore[arg-type]
        )
        formatted = []
        res_ids = results.get("ids")
        res_metas = results.get("metadatas")

        if res_ids and res_ids[0] and res_metas and res_metas[0]:
            for _i, meta in enumerate(res_metas[0]):
                if not isinstance(meta, dict):
                    continue
                formatted.append({
                    "round_number": meta.get("round_number", 0),
                    "summary": meta.get("summary", ""),
                    "tags": str(meta.get("tags", "")).split(","),
                    "importance": meta.get("importance", 0)
                })
        return formatted

    def upsert_memory(self, session_id: int, memory_id: int, text: str, kind: str, tags: list[str], priority: int):
        try:
            emb = self._embed(text)
            doc_id = f"{session_id}:{memory_id}"
            self.memories_collection.upsert(
                ids=[doc_id],
                embeddings=[emb],  # type: ignore[arg-type]
                metadatas=[{
                    "session_id": session_id,
                    "memory_id": memory_id,
                    "kind": kind,
                    "tags": ",".join(tags),
                    "priority": priority,
                }]  # type: ignore[list-item]
            )
        except Exception as e:
            logger.error(f"upsert_memory failed: {e}")

    def search_memories(self, session_id: int, query_text: str, k: int = 5, min_priority: int = 1) -> list[dict[str, Any]]:
        if not query_text.strip():
            return []
        emb = self._embed(query_text)
        where_clause = {
            "$and": [
                {"session_id": {"$eq": session_id}},
                {"priority": {"$gte": min_priority}},
                {"kind": {"$ne": "turn_metadata"}},
            ]
        }
        res = cast(Any, self.memories_collection).query(
            query_embeddings=[emb], n_results=k, where=cast(Any, where_clause)
        )
        out = []
        res_ids = res.get("ids")
        res_metas = res.get("metadatas")
        res_docs = res.get("documents")
        res_dists = res.get("distances")

        if res_ids and res_ids[0] and res_metas and res_metas[0] and res_docs and res_docs[0]:
            for i, md in enumerate(res_metas[0]):
                if not isinstance(md, dict):
                    continue
                out.append({
                    "memory_id": md.get("memory_id"),
                    "kind": md.get("kind"),
                    "content": res_docs[0][i], # Return content too
                    "tags": str(md.get("tags", "")).split(",") if md.get("tags") else [],
                    "distance": res_dists[0][i] if res_dists and res_dists[0] else 0
                })
        return out

    def delete_session_data(self, session_id: int):
        """Removes all turns and memories for the given session."""
        try:
            self.turn_collection.delete(where=cast(Any, {"session_id": {"$eq": session_id}}))
            self.memories_collection.delete(where=cast(Any, {"session_id": {"$eq": session_id}}))
            logger.info(f"Deleted all vector data for Session {session_id}")
        except Exception as e:
            logger.error(f"delete_session_data failed: {e}")

    def delete_memory(self, session_id: int, memory_id: int):
        """Removes a specific memory by its generated ID."""
        try:
            doc_id = f"{session_id}:{memory_id}"
            self.memories_collection.delete(ids=[doc_id])
            logger.debug(f"Deleted vector memory {doc_id}")
        except Exception as e:
            logger.error(f"delete_memory failed: {e}")
