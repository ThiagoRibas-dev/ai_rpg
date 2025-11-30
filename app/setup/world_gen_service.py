import json
import logging
from typing import Type
from pydantic import BaseModel, Field, create_model
from app.llm.llm_connector import LLMConnector
from app.models.stat_block import StatBlockTemplate
from app.prompts.templates import (
    CHARACTER_EXTRACTION_PROMPT,
    OPENING_CRAWL_PROMPT,
    WORLD_EXTRACTION_PROMPT,
)
from app.setup.schemas import (
    CharacterExtraction,
    CharacterExtractionBase,
    WorldExtraction,
)

logger = logging.getLogger(__name__)


class WorldGenService:
    """ETL Pipeline for Character/World Gen."""

    def __init__(self, llm_connector: LLMConnector):
        self.llm = llm_connector

    def _build_dynamic_stats_model(
        self, template: StatBlockTemplate
    ) -> Type[BaseModel]:
        """
        Dynamically creates a Pydantic model representing the specific RPG system's stats.
        Iterates over the new 'values' and 'gauges' dicts.
        """
        fields = {}

        # 1. Values (Attributes, Skills, etc)
        for key, val_def in template.values.items():
            if val_def.calculation:
                continue  # Skip derived stats

            t = str  # Default
            if val_def.data_type == "integer":
                t = int
            elif val_def.data_type == "boolean":
                t = bool
            elif val_def.data_type == "float":
                t = float

            fields[key] = (t, Field(..., description=val_def.label))

        # 2. Gauges (Start values)
        for key, gauge_def in template.gauges.items():
            if "formula" in gauge_def.max_formula:
                continue  # Skip derived max
            # We usually ask for the current/starting value
            fields[key] = (int, Field(..., description=f"Starting {gauge_def.label}"))

        StatsModel = create_model("DynamicStats", **fields)

        return create_model(
            "DynamicCharacterExtraction",
            stats=(StatsModel, Field(..., description="Stats")),
            __base__=CharacterExtractionBase,
        )

    def extract_character_data(
        self, char_description: str, stat_template: StatBlockTemplate
    ) -> CharacterExtraction:
        if not char_description.strip():
            char_description = "A standard adventurer."

        try:
            DynamicModel = self._build_dynamic_stats_model(stat_template)
        except Exception as e:
            logger.error(f"Model creation failed: {e}")
            DynamicModel = CharacterExtraction

        # Summary for LLM context
        summary = {
            "fields": [
                v.label for v in stat_template.values.values() if not v.calculation
            ],
            "resources": [g.label for g in stat_template.gauges.values()],
        }

        try:
            prompt = CHARACTER_EXTRACTION_PROMPT.format(
                description=char_description, template=json.dumps(summary)
            )
            raw = self.llm.get_structured_response(prompt, [], DynamicModel, 0.1, 0.1)

            stats_dict = {}
            if hasattr(raw, "stats"):
                stats_dict = raw.stats.model_dump()
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
            logger.error(f"Extraction failed: {e}")
            raise

    def extract_world_data(self, desc: str) -> WorldExtraction:
        if not desc.strip():
            desc = "A generic fantasy tavern."
        try:
            return self.llm.get_structured_response(
                WORLD_EXTRACTION_PROMPT.format(description=desc),
                [],
                WorldExtraction,
                0.1,
                0.1,
            )
        except Exception as e:
            logger.error(f"World extraction failed: {e}")
            raise

    def generate_opening_crawl(
        self, char: CharacterExtraction, world: WorldExtraction, guidance: str = ""
    ) -> str:
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
