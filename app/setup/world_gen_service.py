import json
import logging
from typing import Type, Callable, Optional
from pydantic import BaseModel, Field, create_model
from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.stat_block import StatBlockTemplate
from app.prompts.templates import (
    ANALYZE_CHARACTER_INSTRUCTION,
    GENERATE_CHARACTER_INSTRUCTION,
    ANALYZE_WORLD_INSTRUCTION,
    GENERATE_WORLD_INSTRUCTION,
    OPENING_CRAWL_PROMPT,
)
from app.setup.schemas import (
    CharacterExtraction,
    CharacterExtractionBase,
    WorldExtraction,
)

logger = logging.getLogger(__name__)


class WorldGenService:
    """ETL Pipeline for Character/World Gen with CoT Analysis."""

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

    def _build_dynamic_stats_model(
        self, template: StatBlockTemplate
    ) -> Type[BaseModel]:
        """
        Dynamically creates a Pydantic model representing the specific RPG system's stats.
        """
        fields = {}

        # 1. Fundamentals (Inputs)
        for key, val_def in template.fundamentals.items():
            t = str
            if val_def.data_type == "integer":
                t = int
            elif val_def.data_type == "boolean":
                t = bool
            elif val_def.data_type == "float":
                t = float

            # We make these optional in the extraction model to prevent validation errors
            # if the LLM misses one, though we instruct it to fill them.
            fields[key] = (Optional[t], Field(default=None, description=val_def.label))

        # 2. Gauges (Start values)
        for key, gauge_def in template.gauges.items():
            if "formula" in gauge_def.max_formula:
                continue
            fields[key] = (
                Optional[int],
                Field(default=None, description=f"Starting {gauge_def.label}"),
            )

        StatsModel = create_model("DynamicStats", **fields)

        return create_model(
            "DynamicCharacterExtraction",
            stats=(StatsModel, Field(..., description="Stats matching the template")),
            __base__=CharacterExtractionBase,
        )

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
                0.5,  # Balance creativity with structure
                0.9,
            )
        except Exception as e:
            logger.error(f"World extraction failed: {e}")
            raise

    def extract_character_data(
        self, char_description: str, stat_template: StatBlockTemplate
    ) -> CharacterExtraction:
        if not char_description.strip():
            char_description = "A standard adventurer."

        # Build Dynamic Model
        try:
            DynamicModel = self._build_dynamic_stats_model(stat_template)
        except Exception as e:
            logger.error(f"Model creation failed: {e}")
            DynamicModel = CharacterExtraction

        # Prepare Context
        summary = {
            "fundamentals": [
                f"{v.id} ({v.label})" for v in stat_template.fundamentals.values()
            ],
            "gauges": [f"{g.id} ({g.label})" for g in stat_template.gauges.values()],
        }

        # --- STEP 1: ANALYSIS ---
        self._update_status("Analyzing Character Concept...")

        prompt_analysis = ANALYZE_CHARACTER_INSTRUCTION.format(
            description=char_description, template_context=json.dumps(summary, indent=2)
        )

        analysis_stream = self.llm.get_streaming_response(
            "You are a Character Designer.",
            [Message(role="user", content=prompt_analysis)],
        )

        analysis_text = "".join(analysis_stream)

        # --- STEP 2: EXTRACTION ---
        self._update_status("Allocating Stats & Gear...")

        try:
            raw = self.llm.get_structured_response(
                "You are a Character Designer.",
                [
                    Message(role="user", content=prompt_analysis),
                    Message(role="assistant", content=analysis_text),
                    Message(role="user", content=GENERATE_CHARACTER_INSTRUCTION),
                ],
                DynamicModel,
                0.2,  # Lower temp for stat precision
                0.9,
            )

            # Normalize stats output
            stats_dict = {}
            if hasattr(raw, "stats") and raw.stats:
                # Filter out None values
                stats_dict = {
                    k: v for k, v in raw.stats.model_dump().items() if v is not None
                }
            elif hasattr(raw, "suggested_stats"):
                stats_dict = raw.suggested_stats

            return CharacterExtraction(
                name=raw.name,
                visual_description=raw.visual_description,
                bio=raw.bio,
                inventory=raw.inventory,
                companions=raw.companions,
                suggested_stats=stats_dict,
            )
        except Exception as e:
            logger.error(f"Character extraction failed: {e}")
            raise

    def generate_opening_crawl(
        self, char: CharacterExtraction, world: WorldExtraction, guidance: str = ""
    ) -> str:
        self._update_status("Writing Opening Scene...")
        try:
            prompt = OPENING_CRAWL_PROMPT.format(
                genre=world.genre,
                tone=world.tone,
                name=char.name,
                location=world.starting_location.name_display,
                guidance=guidance or "Start adventure.",
            )
            gen = self.llm.get_streaming_response(prompt, [])
            return "".join(gen)
        except Exception:
            return "You stand ready. What do you do?"
