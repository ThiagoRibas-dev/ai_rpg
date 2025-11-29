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
        fields = {}
        # Iterate Dicts now
        for name, fund in template.fundamental_stats.items():
            t = (
                float
                if fund.data_type == "float"
                else (str if fund.data_type in ["string", "die_code"] else int)
            )
            fields[name] = (t, Field(..., description=f"{name}"))

        for name, vital in template.vital_resources.items():
            fields[name] = (int, Field(..., description=f"Starting {name}"))

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
            "abilities": list(stat_template.fundamental_stats.keys()),
            "vitals": list(stat_template.vital_resources.keys()),
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
