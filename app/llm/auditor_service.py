import logging
from typing import List, Dict, Any
from app.models.message import Message
from app.llm.llm_connector import LLMConnector
from app.llm.schemas import AuditResult
from app.tools.schemas import MemoryUpsert

AUDIT_PROMPT = """
You are a Game Engine Auditor. Your job is to ensure the Game State matches the Narrative.

Review the last turn's Narrative and the Tools that were executed.

1. **MOVEMENT CHECK**: Did the narrative describe the party entering a new location (room, building, region)? 
   - If YES, was `scene.move_to` called? 
   - If NO, you MUST add `scene.move_to` to `suggested_tool_calls`.

2. **COMBAT/HEALTH CHECK**: Did the narrative describe a character taking damage, being hit, or healing?
   - If YES, check if `character.apply_damage` or `character.restore_vital` was called.
   - If NO, you MUST add the appropriate tool to `suggested_tool_calls`.

3. **CONSISTENCY**: Are there logical errors? (e.g. Using an item they don't have).

If the state is desynchronized from the text, fix it using `suggested_tool_calls`.
"""


class AuditorService:
    def __init__(
        self,
        llm: LLMConnector,
        tool_registry,
        db_manager,
        vector_store,
        logger: logging.Logger | None = None,
    ):
        self.llm = llm
        self.tools = tool_registry
        self.db = db_manager
        self.vs = vector_store
        self.logger = logger or logging.getLogger(__name__)

    def audit(
        self, chat_history: List[Message], tool_results: List[Dict[str, Any]]
    ) -> AuditResult | None:
        try:
            msgs = chat_history + [Message(role="system", content=str(tool_results))]
            audit_dict = self.llm.get_structured_response(
                system_prompt=AUDIT_PROMPT, chat_history=msgs, output_schema=AuditResult
            )
            return (
                AuditResult.model_validate(audit_dict)
                if audit_dict is not None
                else None
            )
        except Exception as e:
            self.logger.debug(f"Audit skipped: {e}")
            return None

    def apply_remediations(self, audit: AuditResult, session):
        if not audit or audit.ok:
            return
        
        # Phase 1 Refactor: Audit patching disabled.

        # --- AUTO-FIX: Execute Missed Tools ---
        if audit.suggested_tool_calls:
            # We need to map the generic ToolCall (name, args) back to the Pydantic model
            # so the Registry can validate and execute it.
            name_to_type = {
                t.model_fields["name"].default: t 
                for t in self.tools.get_all_tool_types()
            }
            
            for tool_call in audit.suggested_tool_calls:
                tool_name = tool_call.name
                if tool_name in name_to_type:
                    try:
                        self.logger.info(f"Auditor applying fix: Executing {tool_name}")
                        model_class = name_to_type[tool_name]
                        # Instantiate and Validate
                        tool_instance = model_class(**tool_call.arguments)
                        
                        # Execute
                        context = {
                            "session_id": session.id,
                            "db_manager": self.db,
                            "vector_store": self.vs
                        }
                        self.tools.execute(tool_instance, context=context)
                    except Exception as e:
                        self.logger.error(f"Failed to execute auditor suggestion '{tool_name}': {e}", exc_info=True)
        
        # Memory updates
        for mem in audit.memory_updates or []:
            try:
                mem_call = MemoryUpsert(
                    kind=mem.kind,
                    content=mem.content,
                    priority=mem.priority if mem.priority is not None else 3,
                    tags=mem.tags,
                )
                _ = self.tools.execute(
                    mem_call,
                    context={
                        "session_id": session.id,
                        "db_manager": self.db,
                        "vector_store": self.vs,
                    },
                )
            except Exception as e:
                self.logger.error(f"Memory upsert error during audit: {e}", exc_info=True)
