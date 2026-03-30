import logging
import json
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from pydantic import create_model

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.prefabs.manifest import SystemManifest
from app.setup.schema_builder import SchemaBuilder
from app.models.vocabulary import CategoryName, TaskState, SetupTask, ChargenBranch, CHARGEN_BRANCH_CATEGORIES
from app.prompts.templates import CHARACTER_CREATION_SYSTEM_PROMPT, EXTRACT_CHARACTER_BATCH_PROMPT
from app.setup.schemas import WorldExtraction, LoreStream

logger = logging.getLogger(__name__)


# Dependency batches:
# Batch 1 (Foundations) runs first, building the core identity.
# Batch 2 runs next, splitting into Fluff (Narrative/Descriptive) and Crunch (Mechanics/Stats).

CHARGEN_BATCHES: List[Dict[str, List[str]]] = [
    {
        ChargenBranch.BASE: CHARGEN_BRANCH_CATEGORIES[ChargenBranch.BASE],
    },
    {
        ChargenBranch.MECHANICS: CHARGEN_BRANCH_CATEGORIES[ChargenBranch.MECHANICS],
    },
    {
        ChargenBranch.DERIVED: CHARGEN_BRANCH_CATEGORIES[ChargenBranch.DERIVED],
        ChargenBranch.BACKGROUND: CHARGEN_BRANCH_CATEGORIES[ChargenBranch.BACKGROUND],
    }
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
        self, manifest: SystemManifest, character_sheet: str, 
        world_data: Optional[WorldExtraction] = None, 
        stream: Optional[LoreStream] = None,
        rules_text: str = "",
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

        # 2. Extract prefab schema reference
        prefab_ref = builder.build_prefab_schema_reference()

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

        # 4. Determine which categories to extract (filtered by manifest)
        manifest_cats = set(f.category for f in manifest.fields)
        manifest_cats.add(CategoryName.IDENTITY)  # Always extract identity
        manifest_cats.discard(CategoryName.STATUS)  # Status is always empty at generation

        # 6. Build System Prompt (STRICTLY STATIC)
        # This prompt is the same for all parallel branches in this generation run.
        sys_prompt = CHARACTER_CREATION_SYSTEM_PROMPT.format(
            character_sheet=character_sheet,
            rules_section=rules_section,
            prefab_reference=prefab_ref
        )

        own_executor = False
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=2)
            own_executor = True

        try:
            generated_context: Dict[str, Any] = {}
            raw_combined: Dict[str, Any] = {}

            # 5. First Pass: Register all potential batch tasks as PENDING
            for batch_dict in CHARGEN_BATCHES:
                for branch_name in batch_dict.keys():
                    # Only register if at least one category in the branch is in the manifest
                    if any(c in manifest_cats for c in batch_dict[branch_name]):
                        t_id, t_label = SetupTask.chargen(branch_name.lower())
                        self._track_task(t_id, t_label, TaskState.PENDING)
                    else:
                        # Branch not in this manifest - skip it upfront
                        t_id, t_label = SetupTask.chargen(branch_name.lower())
                        self._track_task(t_id, t_label, TaskState.DONE)

            # Register any remaining categories not covered by main batches
            batch_cats = set().union(*(set(cats) for cats in CHARGEN_BRANCH_CATEGORIES.values()))
            remaining_cats = manifest_cats - batch_cats
            for cat in remaining_cats:
                t_id, t_label = SetupTask.chargen(cat)
                self._track_task(t_id, t_label, TaskState.PENDING)

            for batch_dict in CHARGEN_BATCHES:
                # Filter categories present in the manifest
                active_branches = {}
                for branch_name, cats in batch_dict.items():
                    valid_cats = [c for c in cats if c in manifest_cats]
                    if valid_cats:
                        active_branches[branch_name] = valid_cats
                    else:
                        # Already marked as DONE/Skipped above
                        continue

                if not active_branches:
                    continue

                # Snapshot the context for this batch
                context_snapshot = json.dumps(generated_context, indent=2)

                def extract_branch(branch_name: str, branch_cats: List[str], ctx_snap: str = context_snapshot):
                    t_id, t_label = SetupTask.chargen(branch_name.lower())
                    
                    # --- ASYNC CONTEXT INJECTION (NPCs for Background) ---
                    injected_npcs = None
                    if branch_name == ChargenBranch.BACKGROUND:
                        logger.info(f"Branch '{branch_name}' waiting for NPCs from LoreStream...")
                        injected_npcs = stream.get_npcs() if stream else []
                        logger.info(f"Branch '{branch_name}' received {len(injected_npcs)} NPCs.")

                    self._track_task(t_id, t_label, TaskState.RUNNING)
                    
                    # 1. Dynamically assemble a unified Pydantic model for this branch
                    fields = {}
                    for cat in branch_cats:
                        CatModel = builder.build_creation_model_for_category(cat)
                        fields[cat] = (CatModel, ...)
                        
                    UnifiedModel = create_model(f"Unified{branch_name}", **fields)

                    # 1. Get filtered hints for these specific categories
                    hints_batch = builder.get_creation_prompt_hints(branch_cats)
                    
                    # 2. Build User Prompt (DYNAMIC)
                    prompt = EXTRACT_CHARACTER_BATCH_PROMPT.format(
                        branch_name=str(branch_name),
                        branch_cats_str=", ".join(branch_cats),
                        ctx_snap=ctx_snap,
                        hints=hints_batch
                    )

                    if injected_npcs:
                        npc_list = "\n".join([f"- {n.name}: {n.visual_description}" for n in injected_npcs])
                        prompt += f"\n\nList of NPCs extracted from the Lore document:\n{npc_list}"

                    res = self.llm.get_structured_response(
                        system_prompt=sys_prompt,
                        chat_history=[Message(role="user", content=prompt)],
                        output_schema=UnifiedModel,
                        temperature=0.7,
                    )
                    self._track_task(t_id, t_label, TaskState.DONE)
                    return branch_name, branch_cats, res

                futures = {}
                # Dispatch all branches immediately - blocking now happens inside specific threads!
                for branch_name, branch_cats in active_branches.items():
                    futures[branch_name] = executor.submit(extract_branch, branch_name, branch_cats)

                for branch_name, branch_cats in active_branches.items():
                    _, _, branch_data = futures[branch_name].result()
                    # Unpack the unified response back into individual categories
                    data_dict = branch_data.model_dump()
                    for cat in branch_cats:
                        if cat in data_dict:
                            cat_raw = data_dict[cat]
                            raw_combined[cat] = cat_raw
                            generated_context[cat] = cat_raw

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
                    def extract_remaining_cat():
                        return self.llm.get_structured_response(
                            system_prompt=sys_prompt,
                            chat_history=[Message(role="user", content=prompt)],
                            output_schema=CatModel,
                            temperature=0.7,
                        )
                    future_cat = executor.submit(extract_remaining_cat)
                    cat_data = future_cat.result()
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
