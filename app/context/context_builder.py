import logging
import math
from typing import List
from app.models.session import Session
from app.models.game_session import GameSession
from app.models.message import Message
from app.setup.setup_manifest import SetupManifest


class ContextBuilder:
    """
    Builds context using the Refined Schema.
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
        self.simulation_service = simulation_service
        self.logger = logger or logging.getLogger(__name__)

    def build_static_system_instruction(
        self,
        game_session: GameSession,
        ruleset_text: str = "",
    ) -> str:
        sections = []
        session_data = Session.from_json(game_session.session_data)
        user_game_prompt = session_data.get_system_prompt()
        sections.append(user_game_prompt)

        # Kernel (Physics)
        manifest = SetupManifest(self.db).get_manifest(game_session.id)
        ruleset_id = manifest.get("ruleset_id")

        if ruleset_id:
            ruleset = self.db.rulesets.get_by_id(ruleset_id)
            if ruleset:
                sections.append(self._render_physics(ruleset))

        if game_session.authors_note:
            sections.append("# AUTHOR'S NOTE")
            sections.append(game_session.authors_note)

        return "\n\n".join(sections)

    def build_dynamic_context(
        self,
        game_session: GameSession,
        chat_history: List[Message],
    ) -> str:
        sections = []
        last_user_msg = ""
        for msg in reversed(chat_history):
            if msg.role == "user":
                last_user_msg = msg.content
                break

        # 1. State
        state_text = self.state_builder.build(game_session.id)
        if state_text:
            sections.append(f"# CURRENT STATE #\n{state_text}")

        # 2. Active Procedure
        manifest = SetupManifest(self.db).get_manifest(game_session.id)
        ruleset_id = manifest.get("ruleset_id")
        current_mode = game_session.game_mode.lower()

        if ruleset_id:
            ruleset = self.db.rulesets.get_by_id(ruleset_id)
            if ruleset:
                proc_text = self._render_procedures(ruleset, current_mode)
                if proc_text:
                    sections.append(
                        f"# ACTIVE PROCEDURE: {current_mode.upper()}\n{proc_text}"
                    )

        # 3. RAG Rules
        if ruleset_id and last_user_msg:
            relevant_rules = self.vs.search_rules(ruleset_id, last_user_msg, k=3)
            if relevant_rules:
                rule_block = "\n".join([f"- {r['content']}" for r in relevant_rules])
                sections.append(f"# RELEVANT MECHANICS\n{rule_block}")

        # 4. Spatial
        spatial_context = self._build_spatial_context(game_session.id)
        if spatial_context:
            sections.append(spatial_context)

        # 5. Narrative Memory
        active_npc_keys = self._get_active_npc_keys(game_session.id)
        session = Session.from_json(game_session.session_data)
        session.id = game_session.id
        memories = self.mem_retriever.get_relevant(
            session, chat_history, active_npc_keys=active_npc_keys
        )
        mem_text = self.mem_retriever.format_for_prompt(memories)
        if mem_text:
            sections.append(mem_text)

        return "\n\n".join(sections)

    def _render_physics(self, ruleset) -> str:
        p = ruleset.physics
        lines = ["# CORE PHYSICS"]
        lines.append(f"- **Dice**: {p.dice_notation}")
        lines.append(f"- **Mechanic**: {p.roll_mechanic}")
        lines.append(f"- **Success**: {p.success_condition}")
        lines.append(f"- **Crit/Fail**: {p.crit_rules}")
        return "\n".join(lines)

    def _render_procedures(self, ruleset, mode: str) -> str:
        loops = ruleset.gameplay_procedures
        target_dict = {}

        if mode == "combat" or mode == "encounter":
            target_dict = loops.encounter
        elif mode == "exploration":
            target_dict = loops.exploration
        elif mode == "social":
            target_dict = loops.social
        elif mode == "downtime":
            target_dict = loops.downtime
        else:
            # Fallback to misc if mode is weird, or just return empty
            return ""

        if not target_dict:
            return ""

        lines = []
        for name, proc in target_dict.items():
            lines.append(f"**{name} ({proc.description})**")
            for step in proc.steps:
                lines.append(f"  {step}")
            lines.append("")  # Spacer between procedures

        return "\n".join(lines)

    def _build_spatial_context(self, session_id: int) -> str:
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene:
                return ""
            lines = []
            loc_key = scene.get("location_key")
            if loc_key:
                location = self.db.game_state.get_entity(
                    session_id, "location", loc_key
                )
                if location:
                    lines.append(f"# LOCATION: {location.get('name', 'Unknown')} #")
                    lines.append(location.get("description_visual", ""))
                    conns = location.get("connections", {})
                    if conns:
                        exits = [
                            f"{d.upper()} -> {data.get('display_name')}"
                            for d, data in conns.items()
                        ]
                        lines.append("Exits: " + ", ".join(exits))

            tmap = scene.get("tactical_map", {})
            positions = tmap.get("positions", {})
            if positions:
                lines.append("\n# TACTICAL OVERVIEW #")
                player_pos = self._parse_coord(positions.get("player", "A1"))
                for key, coord_str in positions.items():
                    if key == "player":
                        continue
                    name = key.split(":")[-1].title()
                    npc_pos = self._parse_coord(coord_str)
                    dist = math.dist(player_pos, npc_pos) * 5

                    if dist <= 5:
                        tag = "Melee Range"
                    elif dist <= 15:
                        tag = "Near"
                    elif dist <= 30:
                        tag = "Short Range"
                    else:
                        tag = "Far"
                    lines.append(f"- {name}: {int(dist)}ft away [{tag}]")
            return "\n".join(lines)
        except Exception:
            self.logger.warning("Error building spatial context", exc_info=True)
            return ""

    def _parse_coord(self, coord: str) -> tuple[int, int]:
        if not coord or len(coord) < 2:
            return (0, 0)
        try:
            col = ord(coord[0].upper()) - 65
            row = int(coord[1:]) - 1
            return (col, row)
        except Exception as e:
            self.logger.warning(f"Error parsing coord: {e}")
            return (0, 0)

    def _get_active_npc_keys(self, session_id: int) -> List[str]:
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene:
                return []
            return [
                m.split(":", 1)[1]
                for m in scene.get("members", [])
                if m.startswith("character:") and "player" not in m
            ]
        except Exception as e:
            self.logger.warning(f"Error getting active NPC keys: {e}")
            return []

    def get_truncated_history(
        self, session: Session, max_messages: int
    ) -> List[Message]:
        history = session.get_history()
        return history[-max_messages:] if len(history) > max_messages else history
