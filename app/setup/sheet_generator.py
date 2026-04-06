from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.setup.schemas import LoreStream, WorldExtraction

from pydantic import BaseModel, create_model

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.vocabulary import CHARGEN_BRANCH_CATEGORIES, CategoryName, ChargenBranch, SetupTask, TaskState
from app.prefabs.manifest import SystemManifest
from app.prompts.templates import CHARACTER_CREATION_SYSTEM_PROMPT, EXTRACT_CHARACTER_BATCH_PROMPT
from app.setup.schema_builder import SchemaBuilder

if TYPE_CHECKING:
    from app.setup.schemas import LoreStream, WorldExtraction

logger = logging.getLogger(__name__)


# Dependency batches:
# Batch 1 (Foundations) runs first, building the core identity.
# Batch 2 runs next, splitting into Fluff (Narrative/Descriptive) and Crunch (Mechanics/Stats).

CHARGEN_BATCHES: list[dict[ChargenBranch, list[CategoryName]]] = [

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
    def __init__(self, llm: LLMConnector, task_callback: Callable[[str, str, TaskState], None] | None = None):
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
        world_data: WorldExtraction | None = None,
        stream: LoreStream | None = None,
        rules_text: str = "",
        executor=None,
    ) -> dict[str, Any]:
        """Synchronous wrapper for the async character sheet generation pipeline."""
        return asyncio.run(self.async_generate_from_manifest(
            manifest, character_sheet, world_data, stream, rules_text
        ))

    async def async_generate_from_manifest(
        self, manifest: SystemManifest, character_sheet: str,
        world_data: WorldExtraction | None = None,
        stream: LoreStream | None = None,
        rules_text: str = "",
    ) -> dict[str, Any]:
        """
        Generates character data strictly adhering to the SystemManifest using async calls.
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
        sys_prompt = CHARACTER_CREATION_SYSTEM_PROMPT.format(
            character_sheet=character_sheet,
            rules_section=rules_section,
            prefab_reference=prefab_ref
        )

        try:
            generated_context: dict[str, Any] = {}
            raw_combined: dict[str, Any] = {}

            # 5. First Pass: Register all potential batch tasks as PENDING
            for batch_dict in CHARGEN_BATCHES:
                for branch_name in batch_dict.keys():
                    if any(c in manifest_cats for c in batch_dict[branch_name]):
                        t_id, t_label = SetupTask.chargen(str(branch_name).lower())
                        self._track_task(t_id, t_label, TaskState.PENDING)
                    else:
                        t_id, t_label = SetupTask.chargen(str(branch_name).lower())
                        self._track_task(t_id, t_label, TaskState.DONE)

            batch_cats = set().union(*(set(cats) for cats in CHARGEN_BRANCH_CATEGORIES.values()))
            remaining_cats = manifest_cats - batch_cats
            for cat in remaining_cats:
                t_id, t_label = SetupTask.chargen(str(cat))
                self._track_task(t_id, t_label, TaskState.PENDING)

            for batch_dict in CHARGEN_BATCHES:
                active_branches = {}
                for branch_name, cats in batch_dict.items():
                    valid_cats = [c for c in cats if c in manifest_cats]
                    if valid_cats:
                        active_branches[branch_name] = valid_cats

                if not active_branches:
                    continue

                context_snapshot = json.dumps(generated_context, indent=2)

                tasks = []
                branch_info_list = [] # Store (branch_name, branch_cats) for processing results

                for branch_name, branch_cats in active_branches.items():
                    tasks.append(self._async_extract_branch(
                        branch_name, branch_cats, context_snapshot, sys_prompt, builder, stream
                    ))
                    branch_info_list.append((branch_name, branch_cats))

                # Fire parallel requests for this batch
                results = await asyncio.gather(*tasks)

                for idx, branch_data in enumerate(results):
                    branch_name, branch_cats = branch_info_list[idx]
                    data_dict = branch_data.model_dump()
                    for cat in branch_cats:
                        if cat in data_dict:
                            cat_raw = data_dict[cat]
                            raw_combined[cat] = cat_raw
                            generated_context[cat] = cat_raw

            # Handle any manifest categories not covered by the predefined batches
            remaining = manifest_cats - set(raw_combined.keys())
            remaining_tasks = []
            remaining_task_meta = [] # (task_id, cat)

            for cat in remaining:
                t_id, _ = SetupTask.chargen(str(cat))
                remaining_task_meta.append((t_id, cat))
                # Ensure we pass CategoryName to the internal method
                remaining_tasks.append(self._async_extract_remaining_cat(
                    cast(CategoryName, cat), generated_context, sys_prompt, builder
                ))

            if remaining_tasks:
                remaining_results = await asyncio.gather(*remaining_tasks)
                for idx, cat_data in enumerate(remaining_results):
                    t_id, cat = remaining_task_meta[idx]
                    cat_raw = cat_data.model_dump()
                    raw_combined[str(cat)] = cat_raw
                    generated_context[str(cat)] = cat_raw
                    t_id, label = SetupTask.chargen(str(cat))
                    self._track_task(t_id, label, TaskState.DONE)

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
            pass

    async def _async_extract_branch(
        self, branch_name: ChargenBranch, branch_cats: list[CategoryName],
        ctx_snap: str, sys_prompt: str, builder: SchemaBuilder, stream: LoreStream | None
    ) -> BaseModel:
        t_id, t_label = SetupTask.chargen(str(branch_name).lower())

        # --- ASYNC CONTEXT INJECTION (NPCs for Background) ---
        injected_npcs = None
        if branch_name == ChargenBranch.BACKGROUND:
            logger.info(f"Branch '{branch_name}' waiting for NPCs from LoreStream...")
            # stream.get_npcs() is documented as fulfilling once NPCs are available.
            # In a truly async world, this should be awaited if get_npcs() is async.
            # For now, we assume bridge logic or we keep it sync if it's a simple list.
            injected_npcs = await stream.get_npcs() if stream else []
            logger.info(f"Branch '{branch_name}' received {len(injected_npcs)} NPCs.")

        self._track_task(t_id, t_label, TaskState.RUNNING)

        # 1. Dynamically assemble unified Pydantic model
        fields: dict[str, Any] = {}
        for cat in branch_cats:
            cat_model = builder.build_creation_model_for_category(cat)
            fields[cat] = (cat_model, ...)

        unified_model = create_model(f"Unified{branch_name}", **fields) # type: ignore[arg-type]
        hints_batch = builder.get_creation_prompt_hints(branch_cats)

        prompt = EXTRACT_CHARACTER_BATCH_PROMPT.format(
            branch_name=str(branch_name),
            branch_cats_str=", ".join(branch_cats),
            ctx_snap=ctx_snap,
            hints=hints_batch
        )

        if injected_npcs:
            npc_list = "\n".join([f"- {n.name}: {n.visual_description}" for n in injected_npcs])
            prompt += f"\n\nList of NPCs extracted from the Lore document:\n{npc_list}"

        res = await self.llm.async_get_structured_response(
            system_prompt=sys_prompt,
            chat_history=[Message(role="user", content=prompt)],
            output_schema=cast(type[BaseModel], unified_model),
            temperature=0.7,
        )

        self._track_task(t_id, t_label, TaskState.DONE)
        return res

    async def _async_extract_remaining_cat(
        self, cat: CategoryName, generated_context: dict[str, Any], sys_prompt: str, builder: SchemaBuilder
    ) -> BaseModel:
        t_id, t_label = SetupTask.chargen(str(cat))
        self._track_task(t_id, t_label, TaskState.RUNNING)

        cat_model = builder.build_creation_model_for_category(cat)
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
        res = await self.llm.async_get_structured_response(
            system_prompt=sys_prompt,
            chat_history=[Message(role="user", content=prompt)],
            output_schema=cat_model,
            temperature=0.7,
        )
        return res

