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

logger = logging.getLogger(__name__)


class WorldGenService:
    """ETL Pipeline for World Gen with CoT Analysis."""

    def __init__(
        self,
        llm_connector: LLMConnector,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.llm = llm_connector
        self.status_callback = status_callback

    def _update_status(self, msg: str):
        if self.status_callback:
            self.status_callback(msg)
        logger.info(f"[WorldGen] {msg}")

    def extract_world_data(self, world_info: str) -> WorldExtraction:
        if not world_info.strip():
            world_info = "A generic fantasy tavern."

        # --- STEP 1: GENRE & TONE ---
        self._update_status("Determining Genre & Tone...")
        genre_tone = self.llm.get_structured_response(
            WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(format=GenreToneExtraction.model_json_schema()),
            [Message(role="user", content=EXTRACT_WORLD_GENRE_TONE_PROMPT.format(description=world_info))],
            GenreToneExtraction,
        )

        # --- STEP 2: EXHAUSTIVE LORE ---
        self._update_status("Extracting World Lore...")
        lore_data = self.llm.get_structured_response(
            WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(format=LoreListExtraction.model_json_schema()),
            [Message(role="user", content=EXTRACT_WORLD_LORE_PROMPT.format(description=world_info))],
            LoreListExtraction,
        )

        # --- STEP 3: EXHAUSTIVE LOCATIONS ---
        self._update_status("Identifying Locations...")
        loc_data = self.llm.get_structured_response(
            WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(format=LocationListExtraction.model_json_schema()),
            [Message(role="user", content=EXTRACT_WORLD_LOCATIONS_PROMPT.format(description=world_info))],
            LocationListExtraction,
        )

        # --- STEP 4: EXHAUSTIVE NPCs ---
        self._update_status("Finding NPCs...")
        npc_data = self.llm.get_structured_response(
            WORLD_DATA_EXTRACTION_SYSTEM_PROMPT.format(format=NpcListExtraction.model_json_schema()),
            [Message(role="user", content=EXTRACT_WORLD_NPCS_PROMPT.format(description=world_info))],
            NpcListExtraction,
        )

        # --- ASSEMBLY ---
        # Identify starting vs adjacent locations
        # Traditionally we assume the first location returned is the starting one
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
        self._update_status("Writing Opening Scene...")

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
            return "".join(gen)
        except Exception:
            return "You stand ready. What do you do?"
