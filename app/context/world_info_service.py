import logging
from typing import List
from app.models.message import Message


class WorldInfoService:
    """Manages lazy indexing and retrieval of World Info entries."""

    def __init__(self, db_manager, vector_store, logger: logging.Logger | None = None):
        self.db = db_manager
        self.vs = vector_store
        self.logger = logger or logging.getLogger(__name__)
        self._indexed_prompt_ids: set[int] = set()

    def ensure_indexed(self, prompt_id: int | None):
        if not prompt_id:
            return
        if prompt_id in self._indexed_prompt_ids:
            return
        try:
            for wi in self.db.get_world_info_by_prompt(prompt_id):
                self.vs.upsert_world_info(prompt_id, wi.id, wi.content)
            self._indexed_prompt_ids.add(prompt_id)
        except Exception as e:
            self.logger.warning(
                f"World Info indexing failed for prompt {prompt_id}: {e}"
            )

    def search_for_history(
        self, prompt_id: int | None, recent_messages: List[Message], k: int = 4
    ) -> list[str]:
        if not prompt_id:
            return []
        try:
            recent_text = (
                " ".join([m.content for m in recent_messages[-5:]])
                if recent_messages
                else ""
            )
            hits = self.vs.search_world_info(prompt_id, recent_text, k=k)
            return [h["text"] for h in hits] if hits else []
        except Exception as e:
            self.logger.warning(
                f"World Info retrieval failed for prompt {prompt_id}: {e}"
            )
            return []
