import logging
import json
from app.llm.llm_connector import LLMConnector
from app.models.stat_block import StatBlockTemplate
from app.setup.schemas import CharacterExtraction, WorldExtraction
from app.prompts.templates import (
    CHARACTER_EXTRACTION_PROMPT,
    WORLD_EXTRACTION_PROMPT,
    OPENING_CRAWL_PROMPT
)

logger = logging.getLogger(__name__)

class WorldGenService:
    """
    Orchestrates the pre-game extraction pipeline (ETL).
    Converts raw user text into structured Character and World data.
    """

    def __init__(self, llm_connector: LLMConnector):
        self.llm = llm_connector

    def extract_world_data(self, world_description: str) -> WorldExtraction:
        """
        Extracts location and lore from the user's world description.
        Uses greedy sampling (temp=0) for strict schema adherence.
        """
        logger.info("Extracting world data...")
        
        # If input is empty, provide a default prompt to the LLM to hallucinate something cool
        if not world_description.strip():
            world_description = "A generic fantasy adventure setting starting in a tavern."

        try:
            prompt = WORLD_EXTRACTION_PROMPT.format(description=world_description)
            
            result = self.llm.get_structured_response(
                system_prompt=prompt,
                chat_history=[],
                output_schema=WorldExtraction,
                temperature=0.1, # Deterministic
                top_p=0.1
            )
            return result
        except Exception as e:
            logger.error(f"World extraction failed: {e}", exc_info=True)
            raise

    def extract_character_data(
        self, 
        char_description: str, 
        stat_template: StatBlockTemplate
    ) -> CharacterExtraction:
        """
        Extracts character stats and bio from description, mapping to the provided template.
        Uses greedy sampling (temp=0).
        """
        logger.info("Extracting character data...")

        if not char_description.strip():
            char_description = "A standard adventurer."

        # Serialize template to JSON so LLM knows what stats exist
        # We strip out complex logic fields to keep tokens down, just need names and types
        template_summary = {
            "abilities": [f"{a.name} ({a.data_type})" for a in stat_template.abilities],
            "vitals": [v.name for v in stat_template.vitals],
            "skills_or_tracks": [t.name for t in stat_template.tracks]
        }
        template_json = json.dumps(template_summary, indent=2)

        try:
            prompt = CHARACTER_EXTRACTION_PROMPT.format(
                description=char_description,
                template=template_json
            )

            result = self.llm.get_structured_response(
                system_prompt=prompt,
                chat_history=[],
                output_schema=CharacterExtraction,
                temperature=0.1, # Deterministic
                top_p=0.1
            )
            return result
        except Exception as e:
            logger.error(f"Character extraction failed: {e}", exc_info=True)
            raise

    def generate_opening_crawl(
        self, 
        char_data: CharacterExtraction, 
        world_data: WorldExtraction
    ) -> str:
        """
        Generates the creative opening scene text.
        Uses creative sampling (temp=0.8).
        """
        logger.info("Generating opening crawl...")

        try:
            prompt = OPENING_CRAWL_PROMPT.format(
                name=char_data.name,
                visual_desc=char_data.visual_description,
                location=world_data.starting_location.name_display,
                loc_desc=world_data.starting_location.description_visual,
                bio=char_data.bio
            )
            
            # We use a streaming call here to get raw text, as we don't need JSON
            # But get_structured_response is easier if we define a simple wrapper,
            # or we can just consume the stream.
            # Let's consume the stream for simplicity.
            
            generator = self.llm.get_streaming_response(
                system_prompt=prompt,
                chat_history=[]
            )
            
            full_text = "".join([chunk for chunk in generator])
            return full_text

        except Exception as e:
            logger.error(f"Opening generation failed: {e}", exc_info=True)
            return "You stand at the precipice of adventure. What do you do?"
