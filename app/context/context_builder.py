import logging
from typing import List
from app.models.session import Session
from app.models.game_session import GameSession
from app.models.message import Message
from app.models.npc_profile import NpcProfile

# Imports for the new Just-in-Time simulation logic
from app.core.simulation_service import SimulationService
import re


# --- Helper for time calculation ---
def _calculate_time_difference_in_hours(time1: str, time2: str) -> int:
    """
    A simple, non-robust helper to estimate time difference in hours.
    This is a placeholder and should be replaced with a proper time parsing library
    if the game's time format becomes more complex.
    It currently only looks for 'Day X' and assumes 24 hours per day change.
    """
    try:
        match1 = re.search(r"Day (\d+)", time1)
        match2 = re.search(r"Day (\d+)", time2)

        if match1 and match2:
            day1 = int(match1.group(1))
            day2 = int(match2.group(1))
            return (day2 - day1) * 24
        return 0
    except (AttributeError, ValueError):
        return 0  # Cannot parse, assume no significant time has passed.


class ContextBuilder:
    """Builds static and dynamic prompt components for caching optimization."""

    def __init__(
        self,
        db_manager,
        vector_store,
        state_builder,
        mem_retriever,
        simulation_service: SimulationService,  # Added dependency
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
        game_session: GameSession,  # tool_schemas removed
        ruleset_text: str = "",
    ) -> str:
        """
        Build the cacheable system instruction.
        Call this when:
        - Session starts
        - Session is loaded
        - Author's note is edited
        - Tool availability changes (this is now handled by the tool calling API, so the full schemas are not needed here)
        """
        sections = []

        # 1. User's game prompt (from Session.system_prompt, NOT history)
        session_data = Session.from_json(game_session.session_data)
        user_game_prompt = session_data.get_system_prompt()
        sections.append(user_game_prompt)

        # 2. Ruleset Reference (The Physics)
        if ruleset_text:
            sections.append("# GAME RULES & MECHANICS")
            sections.append(ruleset_text)
            sections.append("Use schema.query or state.query for detailed values.")

        # 4. Author's note (if exists)
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
        Build dynamic context that changes every turn.
        This gets injected via assistant prefill.
        """
        sections = []

        # Current state
        state_text = self.state_builder.build(game_session.id)
        if state_text:
            sections.append(f"# CURRENT STATE #\n{state_text}")

        # --- NEW: Navigation HUD ---
        nav_hud = self._build_navigation_hud(game_session.id)
        if nav_hud:
            sections.append(nav_hud)

        # --- NEW: Narrative History (Phase 4) ---
        # Inject summaries of previous scenes
        scene_history = self._build_scene_history(game_session.id)
        if scene_history:
            sections.append(scene_history)

        # --- NEW: Run Just-in-Time NPC Simulation ---
        # This happens BEFORE memories are retrieved, so any new memories from the
        # simulation can be included in the context for this turn.
        self._run_jit_simulation(game_session)
        # Determine active NPCs in the scene for contextual retrieval
        active_npc_keys = self._get_active_npc_keys(game_session.id)
        
        # Collect knowledge tags from these NPCs
        knowledge_tags = self._collect_npc_knowledge_tags(game_session.id, active_npc_keys)
 
        # Retrieved memories
        session = Session.from_json(game_session.session_data)
        session.id = game_session.id
 
        # Pass active NPCs to the retriever for contextual prioritization
        memories = self.mem_retriever.get_relevant(
            session, chat_history, 
            active_npc_keys=active_npc_keys,
            extra_tags=knowledge_tags # Pass the knowledge tags
        )
        mem_text = self.mem_retriever.format_for_prompt(memories)
        if mem_text:
            sections.append(mem_text)

        # NPC context
        npc_context_text = self._build_npc_context_string(game_session.id)
        if npc_context_text:
            sections.append(npc_context_text)

        return "\n\n".join(sections)

    def _get_active_scene_members(self, session_id: int) -> List[str]:
        """Helper to get a list of character keys from the active scene."""
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene or "members" not in scene:
                return []

            members = scene.get("members", [])
            # Parse 'character:key' format
            char_keys = [
                member.split(":", 1)[1]
                for member in members
                if member.startswith("character:")
            ]
            return char_keys
        except Exception as e:
            self.logger.debug(
                f"Could not retrieve active scene members: {e}", exc_info=True
            )
            return []

    def _build_navigation_hud(self, session_id: int) -> str:
        """
        Builds the spatial context: Current Location + Exits.
        This grounds the AI to prevent teleportation.
        """
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene:
                return ""

            loc_key = scene.get("location_key")
            if not loc_key:
                return ""

            location = self.db.game_state.get_entity(session_id, "location", loc_key)
            if not location:
                return ""

            name = location.get("name", "Unknown Location")
            vis_desc = location.get("description_visual", "")
            connections = location.get("connections", {})

            lines = [f"# CURRENT LOCATION: {name} #", vis_desc, "", "## EXITS ##"]

            if not connections:
                lines.append(" - No known exits.")
            else:
                for direction, data in connections.items():
                    target_name = data.get("display_name", "Exit")
                    target_key = data.get("target_key")

                    flags = []
                    if data.get("is_hidden"):
                        flags.append("[HIDDEN]")
                    if data.get("is_locked"):
                        flags.append("[LOCKED]")
                    flag_str = " " + " ".join(flags) if flags else ""

                    lines.append(
                        f" - {direction.title()} -> {target_name} ({target_key}){flag_str}"
                    )

            return "\n".join(lines)
        except Exception as e:
            self.logger.error(f"Error building navigation HUD: {e}")
            return ""

    def _build_scene_history(self, session_id: int) -> str:
        """
        Fetches recent scene summaries to provide narrative continuity.
        """
        try:
            scenes = self.db.turn_metadata.get_recent_scenes(session_id, limit=3)
            if not scenes:
                return ""

            lines = ["# PREVIOUSLY ON... #"]
            for scene in scenes:
                lines.append(f"[{scene['location']}]\n{scene['summary']}")

            return "\n\n".join(lines)
        except Exception as e:
            self.logger.error(f"Error building scene history: {e}")
            return ""

    def _get_active_npc_keys(self, session_id: int) -> List[str]:
        """Finds the entity keys of NPCs in the active scene."""
        all_members = self._get_active_scene_members(session_id)
        return [key for key in all_members if key != "player"]

    def _build_npc_context_string(self, session_id: int) -> str:
        """
        Finds NPCs in the active scene and formats their profiles for context.
        """
        active_npc_keys = self._get_active_npc_keys(session_id)
        if not active_npc_keys:
            return ""

        lines = ["# NPC CONTEXT #"]
        for key in active_npc_keys:
            try:
                char = self.db.game_state.get_entity(session_id, "character", key)
                profile_data = self.db.game_state.get_entity(
                    session_id, "npc_profile", key
                )
                if char and profile_data:
                    profile = NpcProfile(**profile_data)
                    rel = profile.relationships.get("player")
                    rel_str = (
                        f" | Rel(Player): Trust({rel.trust}), Attract({rel.attraction}), Fear({rel.fear})"
                        if rel
                        else ""
                    )
                    lines.append(
                        f" - {char.get('name', key)}: Motives({', '.join(profile.motivations)}){rel_str}"
                    )
            except Exception as e:
                self.logger.debug(
                    f"Failed to build context for NPC '{key}': {e}", exc_info=True
                )
                continue

        return "\n".join(lines) if len(lines) > 1 else ""
        
    def _collect_npc_knowledge_tags(self, session_id: int, npc_keys: List[str]) -> List[str]:
        """Aggregate knowledge tags from all active NPCs."""
        tags = set()
        for key in npc_keys:
            try:
                profile_data = self.db.game_state.get_entity(session_id, "npc_profile", key)
                if profile_data:
                    tags.update(profile_data.get("knowledge_tags", []))
            except Exception:
                continue
        return list(tags)

    def _run_jit_simulation(self, game_session: GameSession):
        """
        Checks active NPCs and runs on-demand simulation for any whose state is stale.
        """
        SIMULATION_THRESHOLD_HOURS = 6  # Simulate if more than 6 hours have passed

        active_npc_keys = self._get_active_npc_keys(game_session.id)
        if not active_npc_keys:
            return

        current_time = game_session.game_time

        for npc_key in active_npc_keys:
            try:
                profile_data = self.db.game_state.get_entity(
                    game_session.id, "npc_profile", npc_key
                )
                if not profile_data:
                    continue

                profile = NpcProfile(**profile_data)

                time_diff = _calculate_time_difference_in_hours(
                    profile.last_updated_time, current_time
                )

                if time_diff > SIMULATION_THRESHOLD_HOURS:
                    self.logger.info(
                        f"NPC '{npc_key}' is stale ({time_diff}h). Running JIT simulation."
                    )

                    char_data = self.db.game_state.get_entity(
                        game_session.id, "character", npc_key
                    )
                    npc_name = char_data.get("name", npc_key)

                    outcome = self.simulation_service.simulate_npc_downtime(
                        npc_name=npc_name, profile=profile, current_time=current_time
                    )

                    if not outcome:
                        continue

                    # Apply simulation results
                    if outcome.proposed_patches:
                        # Phase 1 Refactor: JIT Patches disabled until specific NPC mutation tools exist.
                        # The simulation service generates patches, but we can't apply them safely via generic patcher.
                        self.logger.warning(
                            f"JIT Simulation proposed patches for {npc_key}, but application is disabled."
                        )

                    if outcome.is_significant:
                        self.db.memories.create(
                            session_id=game_session.id,
                            kind="episodic",
                            content=outcome.outcome_summary,
                            priority=2,
                            tags=["world_event", "simulation", npc_key],
                            fictional_time=current_time,
                        )

                    # CRITICAL: Update the timestamp to prevent re-simulation
                    profile.last_updated_time = current_time
                    self.db.game_state.set_entity(
                        game_session.id, "npc_profile", npc_key, profile.model_dump()
                    )
            except Exception as e:
                self.logger.error(
                    f"Error during JIT simulation for NPC '{npc_key}': {e}",
                    exc_info=True,
                )

    def get_truncated_history(
        self,
        session: Session,
        max_messages: int,
    ) -> List[Message]:
        """Get truncated chat history (user/assistant only, no system messages)."""
        history = session.get_history()  # ✅ Already filtered, no system messages
        if len(history) <= max_messages:
            return history

        # Keep most recent messages
        return history[-max_messages:]
