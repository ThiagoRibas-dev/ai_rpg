import logging
from typing import Any, Dict, Tuple

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.sheet_schema import CharacterSheetSpec
from app.prefabs.manifest import SystemManifest
from app.setup.schema_builder import SchemaBuilder

logger = logging.getLogger(__name__)

class SheetGenerator:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    # -------------------------------------------------------------------------
    # STRATEGY 2: MANIFEST-AWARE (The Lego Protocol)
    # -------------------------------------------------------------------------
    def generate_from_manifest(
        self, manifest: SystemManifest, character_concept: str, rules_text: str = ""
    ) -> Tuple[CharacterSheetSpec, Dict[str, Any]]:
        """
        Generates character data strictly adhering to the SystemManifest.
        
        1. Builds a Pydantic model from the Manifest.
        2. Prompts LLM to fill it based on Concept + Rules.
        3. Expands simplified LLM output to full Prefab structures.
        """
        logger.info(f"Generating sheet from Manifest: {manifest.name}")

        # 1. Build Builder
        builder = SchemaBuilder(manifest)
        spec = CharacterSheetSpec() 

        # 2. Get the 'Simplified' model for LLM
        CreationModel = builder.build_creation_prompt_model()
        hints = builder.get_creation_prompt_hints()

        # 3. Build Prompt
        prompt = f"""
### TASK: CREATE CHARACTER DATA
You are populating a character sheet for the system: {manifest.name}.

**Rules Context:**
{rules_text[:3000] if rules_text else "Refer to system knowledge."}

**Character Concept:**
{character_concept}

**Field Constraints & Types:**
{hints}

**Instructions:**
- Fill in values that fit the concept and rules.
- Respect the type hints (e.g., if range 1-20, don't put 25).
- For Lists, provide 3-5 items.
"""

        # 4. Call LLM
        try:
            simplified_data = self.llm.get_structured_response(
                system_prompt="You are an expert TTRPG character creator.",
                chat_history=[Message(role="user", content=prompt)],
                output_schema=CreationModel,
                temperature=0.7,
            )

            # 5. Expand to Full Data
            full_values = builder.convert_simplified_to_full(
                simplified_data.model_dump()
            )

            return spec, full_values

        except Exception as e:
            logger.error(f"Manifest-based generation failed: {e}", exc_info=True)
            return spec, {}
