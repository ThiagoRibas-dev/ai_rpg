import logging
from typing import Any, Dict

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
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
    ) -> Dict[str, Any]:
        """
        Generates character data strictly adhering to the SystemManifest.

        1. Builds a Pydantic model from the Manifest.
        2. Prompts LLM to fill it based on Concept + Rules.
        3. Expands simplified LLM output to full Prefab structures.
        Returns a plain entity dict; validation happens outside this method.
        """
        logger.info(f"Generating sheet from Manifest: {manifest.name}")

        # 1. Build Builder
        builder = SchemaBuilder(manifest)

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

            # 5. Normalize dotted keys into nested structure
            raw = simplified_data.model_dump()

            # Example keys we want to normalize:
            # "identity.race" -> raw["identity"]["race"]
            # "attributes.str" -> raw["attributes"]["str"]
            # "resources.hp.current" -> raw["resources"]["hp"]["current"]
            dotted_keys = [k for k in raw.keys() if "." in k]
            for key in dotted_keys:
                value = raw.pop(key)
                parts = key.split(".")

                # Start at top-level category
                node = raw.setdefault(parts[0], {})
                if not isinstance(node, dict):
                    # If the category was a scalar, we can't sensibly merge; skip
                    continue

                cur = node
                for p in parts[1:-1]:
                    if not isinstance(cur.get(p), dict):
                        cur[p] = {}
                    cur = cur[p]
                cur[parts[-1]] = value

            # 6. Expand to Full Data using manifest/prefabs
            full_values = builder.convert_simplified_to_full(raw)

            return full_values

        except Exception as e:
            logger.error(f"Manifest-based generation failed: {e}", exc_info=True)
            return {}
