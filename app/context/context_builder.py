import logging
import math
from typing import List
from app.models.session import Session
from app.models.game_session import GameSession
from app.models.message import Message


class ContextBuilder:
    """
    Builds static and dynamic prompt components.
    Phase 3 Optimized:
    - Semantic Spatial Awareness (Python calculates distance)
    - Removed "Every Turn" JIT Simulation (Moved to Tools)
    - Lighter Context
    """

    def __init__(
        self,
        db_manager,
        vector_store,
        state_builder,
        mem_retriever,
        simulation_service,
        logger: logging.Logger | None = None,
    ):
        self.db = db_manager
        self.vs = vector_store
        self.state_builder = state_builder
        self.mem_retriever = mem_retriever
        self.simulation_service = (
            simulation_service  # Kept for dependency, but not used in loop
        )
        self.logger = logger or logging.getLogger(__name__)

    def build_static_system_instruction(
        self,
        game_session: GameSession,
        ruleset_text: str = "",
    ) -> str:
        """Build the cacheable system instruction."""
        sections = []

        # 1. User's game prompt
        session_data = Session.from_json(game_session.session_data)
        user_game_prompt = session_data.get_system_prompt()
        sections.append(user_game_prompt)

        # 2. Ruleset Reference
        if ruleset_text:
            sections.append("# GAME RULES & MECHANICS")
            sections.append(ruleset_text)

        # 3. Author's note
        if game_session.authors_note:
            sections.append("# NOTE")
            sections.append(game_session.authors_note)

        return "\n\n".join(sections)

    def build_dynamic_context(
        self,
        game_session: GameSession,
        chat_history: List[Message],
    ) -> str:
        """
        Build dynamic context for the ReAct loop.
        """
        sections = []

        # 1. Current State (Vitals/Stats)
        state_text = self.state_builder.build(game_session.id)
        if state_text:
            sections.append(f"# CURRENT STATE #\n{state_text}")

        # 2. Navigation & Spatial Awareness (Calculated in Python)
        # Replaces raw coordinate dumps
        spatial_context = self._build_spatial_context(game_session.id)
        if spatial_context:
            sections.append(spatial_context)

        # 3. Active NPCs (Contextual)
        active_npc_keys = self._get_active_npc_keys(game_session.id)

        # 4. Relevant Memories
        # We pass active NPCs to boost memory relevance
        session = Session.from_json(game_session.session_data)
        session.id = game_session.id

        memories = self.mem_retriever.get_relevant(
            session, chat_history, active_npc_keys=active_npc_keys
        )
        mem_text = self.mem_retriever.format_for_prompt(memories)
        if mem_text:
            sections.append(mem_text)

        return "\n\n".join(sections)

    def _build_spatial_context(self, session_id: int) -> str:
        """
        Generates a semantic description of the scene layout.
        Calculates distances relative to the player.
        """
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene:
                return ""

            lines = []

            # A. Location Info
            loc_key = scene.get("location_key")
            if loc_key:
                location = self.db.game_state.get_entity(
                    session_id, "location", loc_key
                )
                if location:
                    lines.append(f"# LOCATION: {location.get('name', 'Unknown')} #")
                    lines.append(location.get("description_visual", ""))

                    # Exits
                    conns = location.get("connections", {})
                    if conns:
                        exits = []
                        for direction, data in conns.items():
                            exits.append(
                                f"{direction.upper()} -> {data.get('display_name')}"
                            )
                        lines.append("Exits: " + ", ".join(exits))

            # B. Tactical Positions (The "Visuals over Text" logic)
            tmap = scene.get("tactical_map", {})
            positions = tmap.get("positions", {})  # {key: "A1"}

            if positions:
                lines.append("\n# TACTICAL OVERVIEW #")

                # Get Player Pos
                player_pos = self._parse_coord(positions.get("player", "A1"))

                # Calculate relative distances
                for key, coord_str in positions.items():
                    if key == "player":
                        continue

                    # Get Name
                    name = key.split(":")[-1].title()
                    entity = self.db.game_state.get_entity(session_id, "character", key)
                    if entity:
                        name = entity.get("name", name)

                    # Math
                    npc_pos = self._parse_coord(coord_str)
                    dist = math.dist(player_pos, npc_pos) * 5  # Assuming 5ft squares

                    # Semantic Tag
                    if dist <= 5:
                        tag = "Melee Range (Adjacent)"
                    elif dist <= 15:
                        tag = "Near (1 move)"
                    elif dist <= 30:
                        tag = "Short Range"
                    elif dist <= 60:
                        tag = "Long Range"
                    else:
                        tag = "Very Far"

                    lines.append(f"- {name}: {int(dist)}ft away [{tag}]")

            return "\n".join(lines)
        except Exception as e:
            self.logger.error(f"Error building spatial context: {e}", exc_info=True)
            return ""

    def _parse_coord(self, coord: str) -> tuple[int, int]:
        """Converts 'A1' to (0, 0), 'B2' to (1, 1)."""
        if not coord or len(coord) < 2:
            return (0, 0)
        try:
            col_str = coord[0].upper()
            row_str = coord[1:]
            col = ord(col_str) - 65  # A=0, B=1
            row = int(row_str) - 1  # 1=0, 2=1
            return (col, row)
        except Exception as e:
            self.logger.error(
                f"Error parsing coordinate: {e}. Returnin 0,0", exc_info=True
            )
            return (0, 0)

    def _get_active_npc_keys(self, session_id: int) -> List[str]:
        """Finds the entity keys of NPCs in the active scene."""
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene or "members" not in scene:
                return []
            return [
                m.split(":", 1)[1]
                for m in scene["members"]
                if m.startswith("character:") and "player" not in m
            ]
        except Exception:
            self.logger.error(
                "Error getting active NPC keys. Returning empty", exc_info=True
            )
            return []

    def get_truncated_history(
        self, session: Session, max_messages: int
    ) -> List[Message]:
        history = session.get_history()
        if len(history) <= max_messages:
            return history
        return history[-max_messages:]
