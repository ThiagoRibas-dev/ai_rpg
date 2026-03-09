import logging
import json
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.prefabs.manifest import SystemManifest
from app.setup.schema_builder import SchemaBuilder
from app.models.vocabulary import CategoryName, TaskState, SetupTask
from app.prompts.templates import CHARACTER_CREATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Dependency batches: categories within a batch run in parallel,
# batches execute sequentially so later batches see prior results.
CHARGEN_BATCHES: List[List[str]] = [
    [CategoryName.META, CategoryName.IDENTITY, CategoryName.PROGRESSION],
    [CategoryName.ATTRIBUTES, CategoryName.SKILLS, CategoryName.RESOURCES],
    [CategoryName.INVENTORY, CategoryName.FEATURES, CategoryName.COMBAT,
     CategoryName.CONNECTIONS, CategoryName.NARRATIVE],
]


class SheetGenerator:
    def __init__(self, llm: LLMConnector, task_callback: Optional[Callable[[str, str, TaskState], None]] = None):
        self.llm = llm
        self.task_callback = task_callback

    def _track_task(self, key: str, label: str, state: TaskState):
        if self.task_callback:
            self.task_callback(key, label, state)
        logger.info(f"[SheetGenerator] {label} -> {state}")

    # -------------------------------------------------------------------------
    # STRATEGY 2: MANIFEST-AWARE (Prefabs)
    # -------------------------------------------------------------------------
    def generate_from_manifest(
        self, manifest: SystemManifest, character_concept: str, rules_text: str = "",
        executor=None,
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

        rules_section = ""
        if creation_proc:
            rules_section = f"\n**Character Creation Procedure:**\n{creation_proc}\n"
        if rules_text:
            rules_section += f"\n**Additional Rules Context ({manifest.name}):**\n{rules_text}\n"

        # System prompt is STATIC across all categories (KV cache friendly).
        # Character concept, rules, and field hints are baked in here.
        sys_prompt = CHARACTER_CREATION_SYSTEM_PROMPT.format(
            character_concept=character_concept,
            rules_section=rules_section,
            hints=hints,
            prefab_reference=prefab_ref
        )

        # 4. Determine which categories to extract (filtered by manifest)
        manifest_cats = set(f.category for f in manifest.fields)
        manifest_cats.add(CategoryName.IDENTITY)  # Always extract identity

        # Register all category tasks as PENDING
        for cat in manifest_cats:
            t_id, t_label = SetupTask.chargen(cat)
            self._track_task(t_id, t_label, TaskState.PENDING)

        own_executor = False
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=2)
            own_executor = True

        try:
            # 5. Execute in dependency batches
            generated_context: Dict[str, Any] = {}
            raw_combined: Dict[str, Any] = {}

            for batch in CHARGEN_BATCHES:
                batch_cats = [c for c in batch if c in manifest_cats]
                if not batch_cats:
                    continue

                # Snapshot the context for this batch (all categories share the same prior context)
                context_snapshot = json.dumps(generated_context, indent=2)

                def extract_category(cat: str, ctx_snap: str = context_snapshot):
                    t_id, t_label = SetupTask.chargen(cat)
                    self._track_task(t_id, t_label, TaskState.RUNNING)
                    CatModel = builder.build_creation_model_for_category(cat)
                    prompt = f"""
### TASK: POPULATE CATEGORY: {cat.upper()}
You are populating the `{cat}` section of the character sheet.

**Progress of the character sheet generation so far:**
```json
{ctx_snap}
```

**Instructions:**
- Fill in values for the `{cat}` category that fit the concept and rules, and make logical sense given the previously generated data.
- Output ONLY the `{cat}` category data.
"""
                    res = self.llm.get_structured_response(
                        system_prompt=sys_prompt,
                        chat_history=[Message(role="user", content=prompt)],
                        output_schema=CatModel,
                        temperature=0.7,
                    )
                    self._track_task(t_id, t_label, TaskState.DONE)
                    return cat, res

                futures = {}
                for cat in batch_cats:
                    futures[cat] = executor.submit(extract_category, cat)

                for cat in batch_cats:
                    try:
                        _, cat_data = futures[cat].result()
                        cat_raw = cat_data.model_dump()
                        raw_combined[cat] = cat_raw
                        generated_context[cat] = cat_raw
                    except Exception as e:
                        logger.error(f"Failed to generate category '{cat}': {e}", exc_info=True)
                        t_id, t_label = SetupTask.chargen(cat)
                        self._track_task(t_id, t_label, TaskState.DONE)

            # Handle any manifest categories not covered by the predefined batches
            remaining = manifest_cats - set(raw_combined.keys())
            for cat in remaining:
                try:
                    t_id, t_label = SetupTask.chargen(cat)
                    self._track_task(t_id, t_label, TaskState.RUNNING)
                    CatModel = builder.build_creation_model_for_category(cat)
                    prompt = f"""
### TASK: POPULATE CATEGORY: {cat.upper()}
You are populating the `{cat}` section of the character sheet.

**Progress of the character sheet generation so far:**
```json
{json.dumps(generated_context, indent=2)}
```

**Instructions:**
- Fill in values for the `{cat}` category that fit the concept and rules, and make logical sense given the previously generated data.
- Output ONLY the `{cat}` category data.
"""
                    cat_data = self.llm.get_structured_response(
                        system_prompt=sys_prompt,
                        chat_history=[Message(role="user", content=prompt)],
                        output_schema=CatModel,
                        temperature=0.7,
                    )
                    self._track_task(t_id, t_label, TaskState.DONE)
                    
                    cat_raw = cat_data.model_dump()
                    raw_combined[cat] = cat_raw
                    generated_context[cat] = cat_raw
                except Exception as e:
                    logger.error(f"Failed to generate category '{cat}': {e}", exc_info=True)
                    t_id, t_label = SetupTask.chargen(cat)
                    self._track_task(t_id, t_label, TaskState.DONE)

            # Adds the empty Status category
            raw_combined[CategoryName.STATUS] = {}
            
            # 6. Expand to Full Data using manifest/prefabs
            try:
                full_values = builder.convert_simplified_to_full(raw_combined)
                return full_values

            except Exception as e:
                logger.error(f"Manifest-based generation failed: {e}", exc_info=True)
                raise
        finally:
            if own_executor:
                executor.shutdown()
