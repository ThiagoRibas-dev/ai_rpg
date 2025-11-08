import logging
from typing import List
from app.models.message import Message
from app.io.schemas import ActionChoices
from app.llm.llm_connector import LLMConnector

logger = logging.getLogger(__name__)


class ChoicesService:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def generate(
        self,
        system_instruction: str,  # Static (cached)
        phase_template: str,  # Dynamic (choice instructions)
        narrative_text: str,  # ✅ Prior phase context
        chat_history: List[Message],
    ) -> ActionChoices | None:
        """
        Generates action choices with context from narrative phase.

        Args:
            system_instruction: Static system prompt (cached)
            phase_template: Choice-specific instructions
            narrative_text: The narrative just written (prior phase)
            chat_history: Conversation history
        """

        # ✅ Build prefill with prior phase context
        prefill = f"""[Narrative Phase - What I Just Wrote]
        {narrative_text}

        {phase_template}

        Here are the action choices:
        """

        prefilled_history = chat_history + [Message(role="assistant", content=prefill)]

        try:
            return self.llm.get_structured_response(
                system_prompt=system_instruction,
                chat_history=prefilled_history,
                output_schema=ActionChoices,
            )
        except Exception as e:
            logger.error(f"Error in ChoicesService.plan: {e}", exc_info=True)
            return None
