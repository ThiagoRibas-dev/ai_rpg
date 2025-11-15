import os
import chromadb
from chromadb.config import Settings
from fastembed import TextEmbedding
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

"""
Vector Store for Turn Metadata

Supported embedding models (configure via EMBEDDING_MODEL env var):

Fast & Light (Recommended):
- BAAI/bge-small-en-v1.5 (384 dims, ~50MB) [DEFAULT]
- sentence-transformers/all-MiniLM-L6-v2 (384 dims, ~80MB)
- BAAI/bge-small-en (384 dims, ~50MB)

Better Accuracy (Slower):
- BAAI/bge-base-en-v1.5 (768 dims, ~200MB)
- sentence-transformers/all-mpnet-base-v2 (768 dims, ~420MB)

Best Quality (Slowest):
- BAAI/bge-large-en-v1.5 (1024 dims, ~1GB)

Full list: https://qdrant.github.io/fastembed/examples/Supported_Models/
"""


class VectorStore:
    """Manages vector embeddings for turn metadata semantic search."""

    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(
            path=persist_directory, settings=Settings(anonymized_telemetry=False)
        )
        # Turn summaries collection
        self.collection = self.client.get_or_create_collection(
            name="turn_metadata", metadata={"hnsw:space": "cosine"}
        )

        # 🆕 Get model name from environment variable
        model_name = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

        try:
            self.embed_model = TextEmbedding(model_name=model_name)
            logger.info(f"VectorStore initialized with fastembed model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model '{model_name}': {e}")
            logger.info("Falling back to default model: BAAI/bge-small-en-v1.5")
            self.embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

        # New collections: per-memory embeddings and world info
        self.memories_col = self.client.get_or_create_collection(
            name="memories", metadata={"hnsw:space": "cosine"}
        )
        self.world_info_col = self.client.get_or_create_collection(
            name="world_info", metadata={"hnsw:space": "cosine"}
        )

    def add_turn(
        self,
        session_id: int,
        prompt_id: int,
        round_number: int,
        summary: str,
        tags: List[str],
        importance: int,
    ):
        """Add a turn's metadata to the vector store."""
        try:
            embedding = list(self.embed_model.embed([summary]))[0]

            doc_id = f"{session_id}_{round_number}"
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[
                    {
                        "session_id": session_id,
                        "prompt_id": prompt_id,  # 🆕 Track which prompt this session uses
                        "round_number": round_number,
                        "summary": summary,
                        "tags": ",".join(tags),
                        "importance": importance,
                    }
                ],
            )
            logger.debug(
                f"Added turn {round_number} to vector store (session={session_id}, prompt={prompt_id})"
            )
        except Exception as e:
            logger.error(f"Error adding turn to vector store: {e}", exc_info=True)

    def search_relevant_turns(
        self, session_id: int, query_text: str, top_k: int = 10, min_importance: int = 2
    ) -> List[Dict[str, Any]]:
        """Semantic search for relevant past turns."""
        # Generate query embedding
        query_embedding = list(self.embed_model.embed([query_text]))[0]

        # Search with filters
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={
                "$and": [
                    {"session_id": {"$eq": session_id}},
                    {"importance": {"$gte": min_importance}},
                ]
            },
        )

        # Format results
        if not results.get("ids") or not results["ids"] or not results["ids"][0]:
            return []

        formatted_results = []
        for i, metadata in enumerate(results["metadatas"][0]):
            formatted_results.append(
                {
                    "round_number": metadata["round_number"],
                    "summary": metadata["summary"],
                    "tags": metadata["tags"].split(",") if metadata["tags"] else [],
                    "importance": metadata["importance"],
                    "distance": results["distances"][0][i]
                    if "distances" in results
                    else None,
                }
            )

        return formatted_results

    def delete_session_turns(self, session_id: int):
        """Delete all turns for a session."""
        all_items = self.collection.get(where={"session_id": {"$eq": session_id}})

        if all_items["ids"]:
            self.collection.delete(ids=all_items["ids"])
            logger.info(
                f"Deleted {len(all_items['ids'])} turns from vector store for session {session_id}"
            )

    def delete_session_data(self, session_id: int):
        """Delete all turns and memories for a session from the vector store."""
        # Delete turns
        self.delete_session_turns(session_id)

        # Delete memories
        all_memories = self.memories_col.get(where={"session_id": {"$eq": session_id}})
        if all_memories["ids"]:
            self.memories_col.delete(ids=all_memories["ids"])
            logger.info(
                f"Deleted {len(all_memories['ids'])} memories from vector store for session {session_id}"
            )

    # ===== Memories embeddings =====
    def upsert_memory(
        self,
        session_id: int,
        memory_id: int,
        text: str,
        kind: str,
        tags: List[str],
        priority: int,
    ):
        try:
            emb = list(self.embed_model.embed([text]))[0]
            doc_id = f"{session_id}:{memory_id}"
            self.memories_col.upsert(
                ids=[doc_id],
                embeddings=[emb],
                metadatas=[
                    {
                        "session_id": session_id,
                        "memory_id": memory_id,
                        "kind": kind,
                        "tags": ",".join(tags or []),
                        "priority": int(priority),
                    }
                ],
            )
        except Exception as e:
            # ✅ FIX: Log the error
            logger.error(
                f"upsert_memory failed for memory {memory_id}: {e}", exc_info=True
            )
            raise  # Re-raise so caller knows it failed

    def delete_memory(self, session_id: int, memory_id: int):
        doc_id = f"{session_id}:{memory_id}"
        try:
            self.memories_col.delete(ids=[doc_id])
        except Exception as e:
            # ✅ FIX: Log the error
            logger.error(
                f"delete_memory failed for memory {memory_id}: {e}", exc_info=True
            )
            raise

    def search_memories(
        self, session_id: int, query_text: str, k: int = 8, min_priority: int = 1
    ) -> List[Dict[str, Any]]:
        if not query_text.strip():
            return []
        emb = list(self.embed_model.embed([query_text]))[0]
        res = self.memories_col.query(
            query_embeddings=[emb],
            n_results=k,
            where={
                "$and": [
                    {"session_id": {"$eq": session_id}},
                    {"priority": {"$gte": int(min_priority)}},
                ]
            },
        )
        if not res.get("ids") or not res["ids"] or not res["ids"][0]:
            return []
        out = []
        for i, md in enumerate(res["metadatas"][0]):
            out.append(
                {
                    "session_id": md["session_id"],
                    "memory_id": md["memory_id"],
                    "kind": md.get("kind"),
                    "tags": (md.get("tags") or "").split(",") if md.get("tags") else [],
                    "priority": md.get("priority", 3),
                    "distance": res["distances"][0][i] if "distances" in res else None,
                }
            )
        return out

    # ===== World info embeddings =====
    def upsert_world_info(
        self,
        prompt_id: int,
        world_info_id: int,
        text: str,
        tags: List[str] | None = None,
    ):
        try:
            emb = list(self.embed_model.embed([text]))[0]
            doc_id = f"{prompt_id}:{world_info_id}"
            self.world_info_col.upsert(
                ids=[doc_id],
                embeddings=[emb],
                metadatas=[
                    {
                        "prompt_id": prompt_id,
                        "world_info_id": world_info_id,
                        "tags": ",".join(tags or []),
                        "text": text[:4000],
                    }
                ],
            )
        except Exception as e:
            # ✅ FIX: Log the error
            logger.error(
                f"upsert_world_info failed for WI {world_info_id}: {e}", exc_info=True
            )
            raise

    def delete_world_info(self, prompt_id: int, world_info_id: int):
        doc_id = f"{prompt_id}:{world_info_id}"
        try:
            self.world_info_col.delete(ids=[doc_id])
        except Exception as e:
            # ✅ FIX: Log the error
            logger.error(
                f"delete_world_info failed for WI {world_info_id}: {e}", exc_info=True
            )
            raise

    def search_world_info(
        self, prompt_id: int, query_text: str, k: int = 4
    ) -> List[Dict[str, Any]]:
        if not query_text.strip():
            return []
        emb = list(self.embed_model.embed([query_text]))[0]
        res = self.world_info_col.query(
            query_embeddings=[emb], n_results=k, where={"prompt_id": {"$eq": prompt_id}}
        )
        if not res.get("ids") or not res["ids"] or not res["ids"][0]:
            return []
        out = []
        for i, md in enumerate(res["metadatas"][0]):
            out.append(
                {
                    "world_info_id": md["world_info_id"],
                    "text": md.get("text", ""),
                    "tags": (md.get("tags") or "").split(",") if md.get("tags") else [],
                    "distance": res["distances"][0][i] if "distances" in res else None,
                }
            )
        return out
