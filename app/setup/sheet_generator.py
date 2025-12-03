import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.sheet_schema import CharacterSheetSpec
from app.prompts.architect_templates import (
    ARCHITECT_SYSTEM_PROMPT,
    ARCHITECT_USER_TEMPLATE,
    POPULATE_SYSTEM_PROMPT,
    POPULATE_USER_TEMPLATE
)

logger = logging.getLogger(__name__)

class SheetDataWrapper(BaseModel):
    """Generic wrapper for the dynamic character data output."""
    data: Dict[str, Any] = Field(..., description="The populated character data organized by category keys (e.g. 'attributes', 'resources').")

class SheetGenerator:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def generate_structure(self, rules_text: str, character_concept: str) -> CharacterSheetSpec:
        """
        Pass 1: Architecting the Sheet.
        Determines the JSON Schema (fields, widgets, categories) based on rules + concept.
        """
        logger.info("Architecting sheet structure...")
        user_prompt = ARCHITECT_USER_TEMPLATE.format(
            rules_text=rules_text or "Generic RPG Rules",
            character_concept=character_concept
        )
        
        try:
            return self.llm.get_structured_response(
                system_prompt=ARCHITECT_SYSTEM_PROMPT,
                chat_history=[Message(role="user", content=user_prompt)],
                output_schema=CharacterSheetSpec,
                temperature=0.7 
            )
        except Exception as e:
            logger.error(f"Structure generation failed: {e}")
            # Return empty spec to prevent crash, allowing manual editing later
            return CharacterSheetSpec()

    def populate_sheet(self, spec: CharacterSheetSpec, character_concept: str) -> Dict[str, Any]:
        """
        Pass 2: Populating Data.
        Fills the defined fields with values based on the concept.
        """
        logger.info("Populating sheet data...")
        schema_json = spec.model_dump_json(indent=2, exclude_none=True)
        user_prompt = POPULATE_USER_TEMPLATE.format(
            schema_json=schema_json,
            character_concept=character_concept
        )

        try:
            # We use a wrapper because the output structure is dynamic keys
            result = self.llm.get_structured_response(
                system_prompt=POPULATE_SYSTEM_PROMPT,
                chat_history=[Message(role="user", content=user_prompt)],
                output_schema=SheetDataWrapper,
                temperature=0.7
            )
            return result.data
        except Exception as e:
            logger.error(f"Data population failed: {e}")
            return {}
