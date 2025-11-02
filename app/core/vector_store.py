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
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="turn_metadata",
            metadata={"hnsw:space": "cosine"}
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
    
    def add_turn(self, session_id: int, prompt_id: int, round_number: int, 
             summary: str, tags: List[str], importance: int):
        """Add a turn's metadata to the vector store."""
        try:
            embedding = list(self.embed_model.embed([summary]))[0].tolist()
            
            doc_id = f"{session_id}_{round_number}"
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[{
                    "session_id": session_id,
                    "prompt_id": prompt_id,  # 🆕 Track which prompt this session uses
                    "round_number": round_number,
                    "summary": summary,
                    "tags": ",".join(tags),
                    "importance": importance
                }]
            )
            logger.debug(f"Added turn {round_number} to vector store (session={session_id}, prompt={prompt_id})")
        except Exception as e:
            logger.error(f"Error adding turn to vector store: {e}", exc_info=True)
    
    def search_relevant_turns(self, session_id: int, query_text: str, 
                             top_k: int = 10, min_importance: int = 2) -> List[Dict[str, Any]]:
        """Semantic search for relevant past turns."""
        # Generate query embedding
        query_embedding = list(self.embed_model.embed([query_text]))[0].tolist()
        
        # Search with filters
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={
                "$and": [
                    {"session_id": {"$eq": session_id}},
                    {"importance": {"$gte": min_importance}}
                ]
            }
        )
        
        # Format results
        if not results['ids'] or not results['ids'][0]:
            return []
        
        formatted_results = []
        for i, metadata in enumerate(results['metadatas'][0]):
            formatted_results.append({
                "round_number": metadata["round_number"],
                "summary": metadata["summary"],
                "tags": metadata["tags"].split(",") if metadata["tags"] else [],
                "importance": metadata["importance"],
                "distance": results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted_results
    
    def delete_session_turns(self, session_id: int):
        """Delete all turns for a session."""
        all_items = self.collection.get(
            where={"session_id": {"$eq": session_id}}
        )
        
        if all_items['ids']:
            self.collection.delete(ids=all_items['ids'])
            logger.info(f"Deleted {len(all_items['ids'])} turns from vector store for session {session_id}")