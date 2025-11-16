class TurnMetadataService:
    """Persists and retrieves turn metadata; also writes to vector store."""

    def __init__(self, db_manager, vector_store):
        self.db = db_manager
        self.vs = vector_store

    def persist(
        self,
        session_id: int,
        prompt_id: int,
        round_number: int,
        summary: str,
        tags: list[str],
        importance: int,
    ):
        try:
            self.db.turn_metadata.create(
                session_id, prompt_id, round_number, summary, tags, importance
            )
        except Exception:
            pass
        try:
            self.vs.add_turn(
                session_id, prompt_id, round_number, summary, tags, importance
            )
        except Exception:
            pass

    def search_relevant_turns(
        self, session_id: int, query_text: str, top_k: int = 5, min_importance: int = 3
    ):
        try:
            return self.vs.search_relevant_turns(
                session_id, query_text, top_k=top_k, min_importance=min_importance
            )
        except Exception:
            return []
