from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any, cast

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.vocabulary import SetupTask, TaskState, WorldCategory
from app.prompts.templates import (
    EXTRACT_WORLD_DETAILS_PROMPT,
    EXTRACT_WORLD_GENRE_TONE_PROMPT,
    EXTRACT_WORLD_INDEX_PROMPT,
    OPENING_CRAWL_PROMPT,
    WORLD_DATA_EXTRACTION_SYSTEM_PROMPT,
)
from app.setup.schemas import (
    GenreToneExtraction,
    LocationData,
    LocationListExtraction,
    LoreListExtraction,
    LoreStream,
    NpcListExtraction,
    WorldExtraction,
    WorldIndexExtraction,
)

logger = logging.getLogger(__name__)


class WorldGenService:
    """ETL Pipeline for World Gen with CoT Analysis."""

    def __init__(
        self,
        llm_connector: LLMConnector,
        task_callback: Callable[[str, str, TaskState], None] | None = None,
    ):
        self.llm = llm_connector
        self.task_callback = task_callback

    def _track_task(self, key: str, label: str, state: TaskState):
        if self.task_callback:
            self.task_callback(key, label, state)
        logger.info(f"[WorldGen] {label} -> {state}")

    def extract_world_data(
        self, world_info: str, stream: LoreStream | None = None
    ) -> WorldExtraction:
        """Synchronous wrapper for the async world extraction pipeline."""
        return asyncio.run(self.async_extract_world_data(world_info, stream))

    async def async_extract_world_data(
        self, world_info: str, stream: LoreStream | None = None
    ) -> WorldExtraction:
        if not world_info.strip():
            world_info = "A generic fantasy tavern."

        try:
            # Register initial tasks - we show all potential World Gen tasks upfront
            for t in SetupTask:
                if t.name.startswith("WORLDGEN_") or t == SetupTask.OPENING_CRAWL:
                    self._track_task(t.id, t.label, TaskState.PENDING)

            # --- LAYER 0: THE LENS (Genre & Tone) ---
            self._track_task(SetupTask.WORLDGEN_GENRE.id, SetupTask.WORLDGEN_GENRE.label, TaskState.RUNNING)
            genre_res = cast(GenreToneExtraction, await self.llm.async_get_structured_response(
                WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(
                    description=world_info,
                    format=GenreToneExtraction.model_json_schema()
                ),
                [Message(role="user", content=EXTRACT_WORLD_GENRE_TONE_PROMPT)],
                GenreToneExtraction,
            ))
            self._track_task(SetupTask.WORLDGEN_GENRE.id, SetupTask.WORLDGEN_GENRE.label, TaskState.DONE)

            # --- LAYER 1: THE MASTER INDEX ---
            self._track_task(SetupTask.WORLDGEN_INDEX.id, SetupTask.WORLDGEN_INDEX.label, TaskState.RUNNING)
            index_res = cast(WorldIndexExtraction, await self.llm.async_get_structured_response(
                WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(
                    description=world_info,
                    format=WorldIndexExtraction.model_json_schema()
                ),
                [Message(role="user", content=EXTRACT_WORLD_INDEX_PROMPT)],
                WorldIndexExtraction,
            ))
            self._track_task(SetupTask.WORLDGEN_INDEX.id, SetupTask.WORLDGEN_INDEX.label, TaskState.DONE)

            # --- LAYER 2: PARALLEL BATCH EXTRACTION ---
            # Group items by type for batching
            batches = defaultdict(list)
            for item in index_res.items:
                batches[item.type].append(item.name)

            # Mapping for all possible lore categories to their SetupTasks (for UI)
            # IMPORTANT: Reordered to put NPC first so it dispatches immediately for LoreStream fulfillment
            type_to_task = {
                WorldCategory.NPC:      SetupTask.WORLDGEN_DRAMATIS,
                WorldCategory.LOCATION: SetupTask.WORLDGEN_ATLAS,
                WorldCategory.SYSTEMS:  SetupTask.WORLDGEN_CODEX,
                WorldCategory.RACES:    SetupTask.WORLDGEN_PEOPLES,
                WorldCategory.FACTIONS: SetupTask.WORLDGEN_POWER,
                WorldCategory.HISTORY:  SetupTask.WORLDGEN_CHRONICLE,
                WorldCategory.CULTURE:  SetupTask.WORLDGEN_CULTURE,
                WorldCategory.STATUS:   SetupTask.WORLDGEN_STATUS,
                WorldCategory.MISC:     SetupTask.WORLDGEN_REMNANTS
            }

            tasks = []
            task_ids = []

            # Dispatch all batches to asyncio.gather or mark as Skipped
            for cat_type, task in type_to_task.items():
                if cat_type in batches:
                    names = batches[cat_type]
                    tasks.append(self.async_extract_batch(world_info, names, cat_type))
                    task_ids.append(task.id)
                    self._track_task(task.id, task.label, TaskState.RUNNING)
                else:
                    # Category found empty in Deep Scan - mark as DONE so it clears from PENDING
                    self._track_task(task.id, "Skipped", TaskState.DONE)

                    # Fulfill the LoreStream if this was the NPC category to prevent deadlocks
                    if cat_type == WorldCategory.NPC and stream:
                        stream.set_npcs([])

            # --- WAIT & COLLECT ---
            # Fire all parallel requests at once using TaskGroup for fail-fast cancellation.
            # If one task fails, all others are immediately cancelled.
            tg_tasks = []
            async with asyncio.TaskGroup() as tg:
                for t in tasks:
                    tg_tasks.append(tg.create_task(t))
            
            # Map results back from tasks
            results = [t.result() for t in tg_tasks]

            all_locations = []
            all_npcs = []
            all_lore = []

            for idx, res in enumerate(results):
                task_id = task_ids[idx]
                if isinstance(res, LocationListExtraction):
                    all_locations.extend(res.locations)
                elif isinstance(res, NpcListExtraction):
                    all_npcs.extend(res.npcs)
                    if stream:
                        stream.set_npcs(res.npcs) # Fulfill NPCs as soon as they finish!
                elif isinstance(res, LoreListExtraction):
                    all_lore.extend(res.lore)

                # Update UI for this specific task
                self._track_task(task_id, "Completed", TaskState.DONE)

            # --- ASSEMBLY ---
            start_loc = all_locations[0] if all_locations else LocationData(
                key="loc_start", name="Starting Location",
                description_visual="A blank slate.", description_sensory="Silence.", type="void"
            )
            adj_locs = all_locations[1:] if len(all_locations) > 1 else []

            return WorldExtraction(
                genre=genre_res.genre,
                tone=genre_res.tone,
                starting_location=start_loc,
                adjacent_locations=adj_locs,
                lore=all_lore,
                initial_npcs=all_npcs,
            )

        except Exception as e:
            if stream:
                stream.set_error(e)
            logger.error(f"World Extraction Pipeline Failed: {e}", exc_info=True)
            raise

    async def async_extract_batch(self, world_info: str, names: list[str], type: str) -> Any:
        """Universal batch extractor for Locations, NPCs, or Lore."""
        schema_map = {
            "location": LocationListExtraction,
            "npc": NpcListExtraction
        }
        # Fallback for all lore types
        target_schema = schema_map.get(type, LoreListExtraction)

        prompt = EXTRACT_WORLD_DETAILS_PROMPT.format(
            type=type.upper(),
            names=", ".join(names)
        )

        res = await self.llm.async_get_structured_response(
            WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(
                description=world_info,
                format=target_schema.model_json_schema()
            ),
            [Message(role="user", content=prompt)],
            target_schema,
        )

        # --- Programmatic Tag Injection ---
        # Ensure 'type' is the first tag for all extracted entities
        entities: list[Any] = []
        if isinstance(res, LocationListExtraction):
            entities = res.locations
        elif isinstance(res, NpcListExtraction):
            entities = res.npcs
        elif isinstance(res, LoreListExtraction):
            entities = res.lore

        for entity in entities:
            if hasattr(entity, "tags"):
                # Normalize tags to lowercase and ensure 'type' is at index 0
                tag_to_add = type.lower()
                if tag_to_add in entity.tags:
                    entity.tags.remove(tag_to_add)
                entity.tags.insert(0, tag_to_add)

        return res

    async def async_generate_opening_crawl(
        self, char: Any, world: WorldExtraction, guidance: str = ""
    ) -> str:
        self._track_task(SetupTask.OPENING_CRAWL.id, SetupTask.OPENING_CRAWL.label, TaskState.PENDING)
        self._track_task(SetupTask.OPENING_CRAWL.id, SetupTask.OPENING_CRAWL.label, TaskState.RUNNING)

        char_name = "Player"
        if hasattr(char, "name"):
            char_name = char.name
        elif isinstance(char, dict):
            char_name = char.get("name", "Player")

        try:
            loc_name = world.starting_location.name

            prompt = OPENING_CRAWL_PROMPT.format(
                genre=world.genre,
                tone=world.tone,
                name=char_name,
                location=loc_name,
                guidance=guidance,
            )
            sys_prompt = "You are an expert Game Master beginning a new adventure."

            # Use async streaming directly
            gen = self.llm.async_get_streaming_response(sys_prompt, [Message(role="user", content=prompt)])
            full_text = []
            async for chunk in gen:
                full_text.append(chunk)

            res = "".join(full_text)
            self._track_task(SetupTask.OPENING_CRAWL.id, SetupTask.OPENING_CRAWL.label, TaskState.DONE)
            return res
        except Exception:
            self._track_task(SetupTask.OPENING_CRAWL.id, SetupTask.OPENING_CRAWL.label, TaskState.DONE)
            return "You stand ready. What do you do?"

