import logging
from typing import Callable, Optional, Any
from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.prompts.templates import (
    ANALYZE_WORLD_INSTRUCTION,
    GENERATE_WORLD_INSTRUCTION,
    OPENING_CRAWL_PROMPT,
)
from app.setup.schemas import WorldExtraction

logger = logging.getLogger(__name__)


class WorldGenService:
    """ETL Pipeline for World Gen with CoT Analysis."""

    def __init__(
        self,
        llm_connector: LLMConnector,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.llm = llm_connector
        self.status_callback = status_callback

    def _update_status(self, msg: str):
        if self.status_callback:
            self.status_callback(msg)
        logger.info(f"[WorldGen] {msg}")

    def extract_world_data(self, desc: str) -> WorldExtraction:
        if not desc.strip():
            desc = "A generic fantasy tavern."

        # --- STEP 1: ANALYSIS ---
        self._update_status("Analyzing World Concept...")

        prompt_analysis = ANALYZE_WORLD_INSTRUCTION.format(description=desc)

        analysis_stream = self.llm.get_streaming_response(
            "You are a World Builder.", [Message(role="user", content=prompt_analysis)]
        )

        analysis_text = "".join(analysis_stream)

        # --- STEP 2: EXTRACTION ---
        self._update_status("Defining World Data...")

        try:
            return self.llm.get_structured_response(
                "You are a World Builder.",
                [
                    Message(role="user", content=prompt_analysis),
                    Message(role="assistant", content=analysis_text),
                    Message(role="user", content=GENERATE_WORLD_INSTRUCTION),
                ],
                WorldExtraction,
                0.5,
                0.9,
            )
        except Exception as e:
            logger.error(f"World extraction failed: {e}")
            raise

    def generate_opening_crawl(
        self, char: Any, world: WorldExtraction, guidance: str = ""
    ) -> str:
        self._update_status("Writing Opening Scene...")

        char_name = "Player"
        if hasattr(char, "name"):
            char_name = char.name
        elif isinstance(char, dict):
            char_name = char.get("name", "Player")

        try:
            # world.starting_location.name (was name_display)
            loc_name = world.starting_location.name

            prompt = OPENING_CRAWL_PROMPT.format(
                genre=world.genre,
                tone=world.tone,
                name=char_name,
                location=loc_name,
                guidance=guidance or "Start adventure.",
            )
            gen = self.llm.get_streaming_response(prompt, [])
            return "".join(gen)
        except Exception:
            return "You stand ready. What do you do?"
