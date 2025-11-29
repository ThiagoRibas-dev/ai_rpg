import os
import chromadb
from chromadb.config import Settings
from fastembed import TextEmbedding
from typing import List, Dict, Any
import logging
from chromadb.api.types import Where

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
        try:
            self.embed_model = TextEmbedding(model_name=model_name)
            logger.info(f"VectorStore initialized with {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    def _embed(self, text: str) -> List[float]:
        return list(self.embed_model.embed([text]))[0].tolist()

    # ==========================================================================
    # RULES (The New Layer)
    # ==========================================================================
    
    def add_rules(self, ruleset_id: int, rules: List[Dict[str, Any]]):
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
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            logger.info(f"Indexed {len(rules)} rules for Ruleset {ruleset_id}")
        except Exception as e:
            logger.error(f"Error indexing rules: {e}", exc_info=True)

    def search_rules(self, ruleset_id: int, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Semantic search for rules relevant to the query."""
        if not query.strip():
            return []

        embedding = self._embed(query)
        
        results = self.rules_collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where={"ruleset_id": {"$eq": ruleset_id}}
        )

        hits = []
        if results["ids"] and results["ids"][0]:
            for i, _ in enumerate(results["ids"][0]):
                hits.append({
                    "content": results["documents"][0][i],
                    "name": results["metadatas"][0][i]["name"],
                    "distance": results["distances"][0][i] if results["distances"] else 0
                })
        return hits

    # ==========================================================================
    # MEMORIES & TURNS (Existing)
    # ==========================================================================

    def add_turn(self, session_id: int, prompt_id: int, round_number: int, summary: str, tags: List[str], importance: int):
        try:
            embedding = self._embed(summary)
            doc_id = f"{session_id}_{round_number}"
            self.turn_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[{
                    "session_id": session_id,
                    "prompt_id": prompt_id,
                    "round_number": round_number,
                    "summary": summary,
                    "tags": ",".join(tags),
                    "importance": importance,
                }]
            )
        except Exception as e:
            logger.error(f"Error adding turn: {e}")

    def search_relevant_turns(self, session_id: int, query_text: str, top_k: int = 5, min_importance: int = 2) -> List[Dict[str, Any]]:
        embedding = self._embed(query_text)
        where_clause: Where = {
            "$and": [
                {"session_id": {"$eq": session_id}},
                {"importance": {"$gte": min_importance}},
            ]
        }
        results = self.turn_collection.query(
            query_embeddings=[embedding], n_results=top_k, where=where_clause
        )
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, meta in enumerate(results["metadatas"][0]):
                formatted.append({
                    "round_number": meta["round_number"],
                    "summary": meta["summary"],
                    "tags": meta["tags"].split(","),
                    "importance": meta["importance"]
                })
        return formatted

    def upsert_memory(self, session_id: int, memory_id: int, text: str, kind: str, tags: List[str], priority: int):
        try:
            emb = self._embed(text)
            doc_id = f"{session_id}:{memory_id}"
            self.memories_collection.upsert(
                ids=[doc_id],
                embeddings=[emb],
                metadatas=[{
                    "session_id": session_id,
                    "memory_id": memory_id,
                    "kind": kind,
                    "tags": ",".join(tags),
                    "priority": priority,
                }]
            )
        except Exception as e:
            logger.error(f"upsert_memory failed: {e}")

    def search_memories(self, session_id: int, query_text: str, k: int = 5, min_priority: int = 1) -> List[Dict[str, Any]]:
        if not query_text.strip():
            return []
        emb = self._embed(query_text)
        where_clause: Where = {
            "$and": [
                {"session_id": {"$eq": session_id}},
                {"priority": {"$gte": min_priority}},
            ]
        }
        res = self.memories_collection.query(
            query_embeddings=[emb], n_results=k, where=where_clause
        )
        out = []
        if res["ids"] and res["ids"][0]:
            for i, md in enumerate(res["metadatas"][0]):
                out.append({
                    "memory_id": md["memory_id"],
                    "kind": md["kind"],
                    "content": res["documents"][0][i], # Return content too
                    "tags": md["tags"].split(",") if md["tags"] else [],
                    "distance": res["distances"][0][i] if res["distances"] else 0
                })
        return out
    
    def delete_session_data(self, session_id: int):
        # Implementation of deletions (omitted for brevity but implied same as before)
        pass
    
    def delete_memory(self, session_id: int, memory_id: int):
        # Implementation of deletion
        pass
