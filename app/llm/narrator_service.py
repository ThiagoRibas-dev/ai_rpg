import logging
from typing import List
from app.models.message import Message
from app.llm.schemas import ResponseStep
from app.llm.llm_connector import LLMConnector

logger = logging.getLogger(__name__)


class NarratorService:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def write_step(
        self,
        system_instruction: str,
        phase_template: str,
        dynamic_context: str,
        plan_thought: str,  # ✅ Prior phase context
        tool_results: str,  # ✅ Prior phase context
        chat_history: List[Message],
    ) -> ResponseStep | None:
        """
        Generates narrative with full context from planning phase.

        Args:
            system_instruction: Static system prompt (cached)
            phase_template: Narrative-specific instructions
            dynamic_context: Current state, memories, world info
            plan_thought: The planner's thought process (prior phase)
            tool_results: Results from tool execution (prior phase)
            chat_history: Conversation history
        """

        # ✅ Build prefill with prior phase context
        prefill = f"""
{plan_thought}
{phase_template}
{tool_results.replace("[]", "")}
{dynamic_context}

My Response:
"""

        # Inject prefill as final assistant message
        prefilled_history = chat_history + [Message(role="assistant", content=prefill)]
        try:
            return self.llm.get_structured_response(
                system_prompt=system_instruction,
                chat_history=prefilled_history,
                output_schema=ResponseStep,
            )
        except Exception as e:
            logger.error(f"Error in NarratorService.plan: {e}", exc_info=True)
            return None
