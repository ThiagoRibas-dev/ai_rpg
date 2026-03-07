import logging
import json
from typing import Any, Dict, Optional, Callable

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.prefabs.manifest import SystemManifest
from app.setup.schema_builder import SchemaBuilder
from app.models.vocabulary import CategoryName
from app.prompts.templates import CHARACTER_CREATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class SheetGenerator:
    def __init__(self, llm: LLMConnector, status_callback: Optional[Callable[[str], None]] = None):
        self.llm = llm
        self.status_callback = status_callback

    def _update_status(self, msg: str):
        if self.status_callback:
            self.status_callback(msg)
        logger.info(f"[SheetGenerator] {msg}")

    # -------------------------------------------------------------------------
    # STRATEGY 2: MANIFEST-AWARE (Prefabs)
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

        # 2. Extract context hints and prefab schema reference
        prefab_ref = builder.build_prefab_schema_reference()
        hints = builder.get_creation_prompt_hints()

        # 3. Build Prompt (Rules context)
        try:
            creation_proc = manifest.get_procedure("character_creation")
        except Exception:
            creation_proc = None

        if creation_proc:
            rules_section = f"**Character Creation Procedure:**\n{creation_proc}"
            if rules_text:
                rules_section += f"\n\n**Additional Rules Context:**\n{rules_text}"
        else:
            rules_section = rules_text if rules_text else ""

        sys_prompt = CHARACTER_CREATION_SYSTEM_PROMPT.format(
            character_concept=character_concept,
            rules_section=rules_section,
            hints=hints,
            prefab_reference=prefab_ref
        )

        # 4. Determine optimal extraction order
        extraction_order = [
            CategoryName.META,
            CategoryName.NARRATIVE,
            CategoryName.CONNECTIONS,
            CategoryName.PROGRESSION,
            CategoryName.INVENTORY,
            CategoryName.IDENTITY,
            CategoryName.ATTRIBUTES,
            CategoryName.SKILLS,
            CategoryName.FEATURES,
            CategoryName.COMBAT,
            CategoryName.RESOURCES,
            # CategoryName.STATUS, // used during the game, not during character creation
        ]
        
        manifest_cats = set(f.category for f in manifest.fields)
        manifest_cats.add(CategoryName.IDENTITY)  # Always extract identity
        
        cats_to_extract = [c for c in extraction_order if c in manifest_cats]
        total = len(cats_to_extract)

        # 5. Extract category by category
        generated_context: Dict[str, Any] = {}
        raw_combined: Dict[str, Any] = {}

        for i, cat in enumerate(cats_to_extract, 1):
            self._update_status(f"Generating {cat.title()} ({i}/{total})...")
            
            CatModel = builder.build_creation_model_for_category(cat)
            
            prompt = f"""
### TASK: POPULATE CATEGORY: {cat.upper()}
You are populating the `{cat}` section of the character sheet.

**Previously Generated Character Data (Context):**
```json
{json.dumps(generated_context, indent=2)}
```

**Instructions:**
- Fill in values for the `{cat}` category that fit the concept and rules, and make logical sense given the previously generated data.
- Output ONLY the `{cat}` category data.
"""

            try:
                cat_data = self.llm.get_structured_response(
                    system_prompt=sys_prompt,
                    chat_history=[Message(role="user", content=prompt)],
                    output_schema=CatModel,
                    temperature=0.7,
                )
                
                cat_raw = cat_data.model_dump()
                raw_combined[cat] = cat_raw
                generated_context[cat] = cat_raw
                
            except Exception as e:
                logger.error(f"Failed to generate category '{cat}': {e}", exc_info=True)
                self._update_status(f"Error generating {cat.title()}, skipping...")

        # Adds the empty Status category
        raw_combined[CategoryName.STATUS] = {}
        
        # 6. Expand to Full Data using manifest/prefabs
        try:
            full_values = builder.convert_simplified_to_full(raw_combined)
            return full_values

        except Exception as e:
            logger.error(f"Manifest-based generation failed: {e}", exc_info=True)
            raise
