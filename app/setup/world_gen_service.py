import logging
from typing import Callable, Optional, Any
from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.prompts.templates import (
    EXTRACT_WORLD_GENRE_TONE_PROMPT,
    EXTRACT_WORLD_LORE_PROMPT,
    EXTRACT_WORLD_LOCATIONS_PROMPT,
    EXTRACT_WORLD_NPCS_PROMPT,
    OPENING_CRAWL_PROMPT,
    WORLD_DATA_EXTRACTION_SYSTEM_PROMPT,
)
from app.setup.schemas import (
    WorldExtraction,
    GenreToneExtraction,
    LoreListExtraction,
    LocationListExtraction,
    NpcListExtraction,
    LocationData,
)
from app.models.vocabulary import TaskState, SetupTask
logger = logging.getLogger(__name__)


class WorldGenService:
    """ETL Pipeline for World Gen with CoT Analysis."""

    def __init__(
        self,
        llm_connector: LLMConnector,
        task_callback: Optional[Callable[[str, str, TaskState], None]] = None,
    ):
        self.llm = llm_connector
        self.task_callback = task_callback

    def _track_task(self, key: str, label: str, state: TaskState):
        if self.task_callback:
            self.task_callback(key, label, state)
        logger.info(f"[WorldGen] {label} -> {state}")

    def extract_world_data(self, world_info: str, executor=None) -> WorldExtraction:
        if not world_info.strip():
            world_info = "A generic fantasy tavern."

        from concurrent.futures import ThreadPoolExecutor

        own_executor = False
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=2)
            own_executor = True

        try:
            # Register tasks
            self._track_task(SetupTask.WORLDGEN_GENRE.id, SetupTask.WORLDGEN_GENRE.label, TaskState.PENDING)
            self._track_task(SetupTask.WORLDGEN_LOCATIONS.id, SetupTask.WORLDGEN_LOCATIONS.label, TaskState.PENDING)
            self._track_task(SetupTask.WORLDGEN_NPCS.id, SetupTask.WORLDGEN_NPCS.label, TaskState.PENDING)
            self._track_task(SetupTask.WORLDGEN_LORE.id, SetupTask.WORLDGEN_LORE.label, TaskState.PENDING)

            # --- STAGE 1: PARALLEL (Genre, Locations, NPCs) ---
            # These three extraction tasks operate independently on the user's prompt.
            # The system prompt includes the user's description as static text near the top
            # so backends like llama.cpp can cache the shared prefix.

            def extract_genre():
                self._track_task(SetupTask.WORLDGEN_GENRE.id, SetupTask.WORLDGEN_GENRE.label, TaskState.RUNNING)
                res = self.llm.get_structured_response(
                    WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(
                        description=world_info,
                        format=GenreToneExtraction.model_json_schema()
                    ),
                    [Message(role="user", content=EXTRACT_WORLD_GENRE_TONE_PROMPT)],
                    GenreToneExtraction,
                )
                self._track_task(SetupTask.WORLDGEN_GENRE.id, SetupTask.WORLDGEN_GENRE.label, TaskState.DONE)
                return res

            def extract_locations():
                self._track_task(SetupTask.WORLDGEN_LOCATIONS.id, SetupTask.WORLDGEN_LOCATIONS.label, TaskState.RUNNING)
                res = self.llm.get_structured_response(
                    WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(
                        description=world_info,
                        format=LocationListExtraction.model_json_schema()
                    ),
                    [Message(role="user", content=EXTRACT_WORLD_LOCATIONS_PROMPT)],
                    LocationListExtraction,
                )
                self._track_task(SetupTask.WORLDGEN_LOCATIONS.id, SetupTask.WORLDGEN_LOCATIONS.label, TaskState.DONE)
                return res

            def extract_npcs():
                self._track_task(SetupTask.WORLDGEN_NPCS.id, SetupTask.WORLDGEN_NPCS.label, TaskState.RUNNING)
                res = self.llm.get_structured_response(
                    WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(
                        description=world_info,
                        format=NpcListExtraction.model_json_schema()
                    ),
                    [Message(role="user", content=EXTRACT_WORLD_NPCS_PROMPT)],
                    NpcListExtraction,
                )
                self._track_task(SetupTask.WORLDGEN_NPCS.id, SetupTask.WORLDGEN_NPCS.label, TaskState.DONE)
                return res

            future_genre = executor.submit(extract_genre)
            future_locs = executor.submit(extract_locations)
            future_npcs = executor.submit(extract_npcs)

            genre_tone = future_genre.result()
            loc_data = future_locs.result()
            npc_data = future_npcs.result()
        finally:
            if own_executor:
                executor.shutdown()

        # --- STAGE 2: SEQUENTIAL LORE (with prior context) ---
        # Lore extraction receives the already-extracted locations and NPCs
        # so it focuses on history, factions, and concepts without duplication.
        prior_lines = []
        if loc_data.locations:
            prior_lines.append("**Locations already extracted:** " +
                ", ".join(loc.name for loc in loc_data.locations))
        if npc_data.npcs:
            prior_lines.append("**NPCs already extracted:** " +
                ", ".join(npc.name for npc in npc_data.npcs))
        prior_context = "\n".join(prior_lines) if prior_lines else "(none)"

        self._track_task(SetupTask.WORLDGEN_LORE.id, SetupTask.WORLDGEN_LORE.label, TaskState.RUNNING)
        lore_data = self.llm.get_structured_response(
            WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(
                description=world_info,
                format=LoreListExtraction.model_json_schema()
            ),
            [Message(role="user", content=EXTRACT_WORLD_LORE_PROMPT.format(prior_context=prior_context))],
            LoreListExtraction,
        )
        self._track_task(SetupTask.WORLDGEN_LORE.id, SetupTask.WORLDGEN_LORE.label, TaskState.DONE)

        # --- ASSEMBLY ---
        start_loc = loc_data.locations[0] if loc_data.locations else None
        adj_locs = loc_data.locations[1:] if len(loc_data.locations) > 1 else []

        if not start_loc:
            start_loc = LocationData(
                key="loc_start",
                name="Starting Location",
                description_visual="A blank slate.",
                description_sensory="Silence.",
                type="void"
            )

        return WorldExtraction(
            genre=genre_tone.genre,
            tone=genre_tone.tone,
            starting_location=start_loc,
            adjacent_locations=adj_locs,
            lore=lore_data.lore,
            initial_npcs=npc_data.npcs
        )

    def generate_opening_crawl(
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
            gen = self.llm.get_streaming_response(sys_prompt, [Message(role="user", content=prompt)])
            res = "".join(gen)
            self._track_task(SetupTask.OPENING_CRAWL.id, SetupTask.OPENING_CRAWL.label, TaskState.DONE)
            return res
        except Exception:
            self._track_task(SetupTask.OPENING_CRAWL.id, SetupTask.OPENING_CRAWL.label, TaskState.DONE)
            return "You stand ready. What do you do?"
