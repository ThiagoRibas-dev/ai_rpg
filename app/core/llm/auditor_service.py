import logging
from typing import List, Dict, Any
from app.models.message import Message
from app.llm.llm_connector import LLMConnector
from app.io.schemas import AuditResult
from app.tools.schemas import StateApplyPatch, Patch
from app.tools.schemas import MemoryUpsert

AUDIT_PROMPT = "You are a consistency auditor. In <=3 bullets, list contradictions between planned tool results and likely world state; else say OK. If patches are needed, propose minimal JSON patches."

class AuditorService:
    def __init__(self, llm: LLMConnector, tool_registry, db_manager, vector_store, logger: logging.Logger | None = None):
        self.llm = llm
        self.tools = tool_registry
        self.db = db_manager
        self.vs = vector_store
        self.logger = logger or logging.getLogger(__name__)

    def audit(self, chat_history: List[Message], tool_results: List[Dict[str, Any]]) -> AuditResult | None:
        try:
            msgs = chat_history + [Message(role="system", content=str(tool_results))]
            audit_dict = self.llm.get_structured_response(
                system_prompt=AUDIT_PROMPT,
                chat_history=msgs,
                output_schema=AuditResult
            )
            return AuditResult.model_validate(audit_dict) if audit_dict is not None else None
        except Exception as e:
            self.logger.debug(f"Audit skipped: {e}")
            return None

    def apply_remediations(self, audit: AuditResult, session):
        if not audit or audit.ok:
            return
        # Apply patches
        for patch in audit.proposed_patches or []:
            try:
                patch_call = StateApplyPatch(
                    entity_type=patch.entity_type,
                    key=patch.key,
                    patch=[Patch(**op.model_dump()) for op in patch.ops]
                )
                _ = self.tools.execute(
                    patch_call, 
                    context={"session_id": session.id, "db_manager": self.db}
                )
            except Exception as e:
                self.logger.error(f"Patch error during audit: {e}")
        # Memory updates
        for mem in audit.memory_updates or []:
            try:
                mem_call = MemoryUpsert(
                    kind=mem.kind,
                    content=mem.content,
                    priority=mem.priority if mem.priority is not None else 3,
                    tags=mem.tags
                )
                _ = self.tools.execute(
                    mem_call,
                    context={"session_id": session.id, "db_manager": self.db, "vector_store": self.vs}
                )
            except Exception as e:
                self.logger.error(f"Memory upsert error during audit: {e}")
