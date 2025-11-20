# File: D:\Projects\Game Dev\ai-rpg\app\setup\world_gen_service.py
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
    """
    Orchestrates the pre-game extraction pipeline (ETL).
    Converts raw user text into structured Character and World data.
    """

    def __init__(self, llm_connector: LLMConnector):
        self.llm = llm_connector

    def _build_dynamic_stats_model(
        self, template: StatBlockTemplate
    ) -> Type[BaseModel]:
        """
        Constructs a Pydantic model class at runtime based on the StatBlockTemplate.
        This forces the LLM to output exactly the fields defined in the ruleset.
        """
        field_definitions = {}

        # 1. Add Abilities (e.g., Strength: int, Agility: str)
        for ability in template.abilities:
            field_type = int
            desc = f"The character's {ability.name} score."

            if ability.data_type == "die_code" or ability.data_type == "string":
                field_type = str
                desc += " (e.g. 'd6', 'd8')"
            elif ability.data_type == "float":
                field_type = float

            # Create the Pydantic field definition
            field_definitions[ability.name] = (field_type, Field(..., description=desc))

        # 2. Add Vitals (We usually just want the starting/current value)
        for vital in template.vitals:
            # We treat extracted vitals as the 'current' value or 'base' value
            field_definitions[vital.name] = (
                int,
                Field(..., description=f"Starting {vital.name} value."),
            )

        # 3. Add Tracks (Starting values)
        for track in template.tracks:
            field_definitions[track.name] = (
                int,
                Field(0, description=f"Starting {track.name} (default 0)."),
            )

        # Create the 'Stats' sub-model
        StatsModel = create_model("DynamicStats", **field_definitions)

        # Create the Root model inheriting from CharacterExtractionBase
        # This effectively replaces 'suggested_stats: Dict' with 'stats: StatsModel'
        DynamicRoot = create_model(
            "DynamicCharacterExtraction",
            stats=(
                StatsModel,
                Field(
                    ...,
                    description="The character's statistical profile according to game rules.",
                ),
            ),
            __base__=CharacterExtractionBase,
        )

        return DynamicRoot

    def extract_character_data(
        self, char_description: str, stat_template: StatBlockTemplate
    ) -> CharacterExtraction:
        """
        Extracts character stats and bio from description, enforcing the schema
        defined in the stat_template.
        """
        logger.info("Extracting character data with dynamic schema enforcement...")

        if not char_description.strip():
            char_description = "A standard adventurer."

        # 1. Build the Dynamic Pydantic Model
        try:
            DynamicModel = self._build_dynamic_stats_model(stat_template)
            logger.debug(
                f"Generated dynamic schema with fields: {DynamicModel.model_fields['stats'].annotation.model_fields.keys()}"
            )
        except Exception as e:
            logger.error(
                f"Failed to build dynamic model: {e}. Falling back to generic extraction."
            )
            # Fallback logic could go here, but usually better to fail or use generic
            DynamicModel = CharacterExtraction

        # 2. Prepare Prompt (Context is still useful for semantic understanding)
        # We keep the JSON summary so the LLM understands *what* "Strength" means in this context,
        # even though the schema enforces the output structure.
        template_summary = {
            "abilities": [
                f"{a.name} ({a.data_type}): {a.description or ''}"
                for a in stat_template.abilities
            ],
            "vitals": [v.name for v in stat_template.vitals],
        }
        template_json = json.dumps(template_summary, indent=2)

        try:
            prompt = CHARACTER_EXTRACTION_PROMPT.format(
                description=char_description, template=template_json
            )

            # 3. Call LLM with the DYNAMIC Schema
            raw_result = self.llm.get_structured_response(
                system_prompt=prompt,
                chat_history=[],
                output_schema=DynamicModel,
                temperature=0.1,
                top_p=0.1,
            )

            # 4. Convert Dynamic Model -> Standard CharacterExtraction
            # The rest of the app expects 'suggested_stats' as a flat dict.
            # We map the strictly typed 'stats' object back to that dict.
            stats_dict = {}
            if hasattr(raw_result, "stats"):
                # Convert the nested Pydantic model to a dict
                stats_dict = raw_result.stats.model_dump()
            elif hasattr(raw_result, "suggested_stats"):
                # Fallback if we used the generic model
                stats_dict = raw_result.suggested_stats

            # Construct the standard object expected by SessionManager
            final_result = CharacterExtraction(
                name=raw_result.name,
                visual_description=raw_result.visual_description,
                bio=raw_result.bio,
                inventory=raw_result.inventory,
                companions=raw_result.companions,
                suggested_stats=stats_dict,  # Flattened strict stats
            )

            return final_result

        except Exception as e:
            logger.error(f"Character extraction failed: {e}", exc_info=True)
            raise

    def extract_world_data(self, world_description: str) -> WorldExtraction:
        """
        Extracts location and lore from the user's world description.
        """
        logger.info("Extracting world data...")

        if not world_description.strip():
            world_description = (
                "A generic fantasy adventure setting starting in a tavern."
            )

        try:
            prompt = WORLD_EXTRACTION_PROMPT.format(description=world_description)

            result = self.llm.get_structured_response(
                system_prompt=prompt,
                chat_history=[],
                output_schema=WorldExtraction,
                temperature=0.1,
                top_p=0.1,
            )
            return result
        except Exception as e:
            logger.error(f"World extraction failed: {e}", exc_info=True)
            raise

    def generate_opening_crawl(
        self, char_data: CharacterExtraction, world_data: WorldExtraction
    ) -> str:
        """
        Generates the creative opening scene text.
        """
        logger.info("Generating opening crawl...")

        try:
            prompt = OPENING_CRAWL_PROMPT.format(
                name=char_data.name,
                visual_desc=char_data.visual_description,
                location=world_data.starting_location.name_display,
                loc_desc=world_data.starting_location.description_visual,
                bio=char_data.bio,
            )

            generator = self.llm.get_streaming_response(
                system_prompt=prompt, chat_history=[]
            )

            full_text = "".join([chunk for chunk in generator])
            return full_text

        except Exception as e:
            logger.error(f"Opening generation failed: {e}", exc_info=True)
            return "You stand at the precipice of adventure. What do you do?"
