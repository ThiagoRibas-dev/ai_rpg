import logging
from typing import List, Optional
from app.models.session import Session
from app.models.game_session import GameSession
from app.models.message import Message
from app.prefabs.manifest import SystemManifest
from app.setup.setup_manifest import SetupManifest

class ContextBuilder:
    """
    Constructs the System Prompt and Dynamic Context for the LLM.
    Manifest-Aware Implementation (Lego Protocol).
    """
    def __init__(
        self,
        db_manager,
        vector_store,
        state_builder,
        mem_retriever,
        simulation_service,
        logger: logging.Logger | None = None,
        manifest: Optional[SystemManifest] = None
    ):
        self.db = db_manager
        self.vs = vector_store
        self.state_builder = state_builder
        self.mem_retriever = mem_retriever
        self.simulation_service = simulation_service
        self.logger = logger or logging.getLogger(__name__)
        self.manifest = manifest

    def build_static_system_instruction(self, game_session: GameSession) -> str:
        """
        Builds the permanent system instruction (Rules, Engine, Vocabulary).
        """
        sections = []
        
        # 1. Core Persona
        session_data = Session.from_json(game_session.session_data)
        user_game_prompt = session_data.get_system_prompt()
        sections.append(user_game_prompt)

        # 2. Game System Rules (from Manifest)
        if self.manifest:
            sections.append(self._build_manifest_context())
        else:
            # Fallback for legacy/setup
            sections.append(self._build_legacy_rules(game_session))

        # 3. Tool Examples (Critical for atomic tools)
        sections.append(self._build_tool_examples())

        # 4. Author's Note
        if game_session.authors_note:
            sections.append(f"# AUTHOR'S NOTE\n{game_session.authors_note}")

        return "\n\n".join(sections)

    def build_dynamic_context(
        self,
        game_session: GameSession,
        chat_history: List[Message],
    ) -> str:
        """
        Builds the context that changes every turn (State, Narrative, Procedure).
        """
        sections = []

        # 1. Current State (Character Sheet, Location, Inventory)
        state_text = self.state_builder.build(game_session.id, self.manifest)
        if state_text:
            sections.append(f"# CURRENT STATE #\n{state_text}")

        # 2. Active Procedure (Combat/Exploration)
        if self.manifest:
            current_mode = game_session.game_mode.lower()
            proc_text = self.manifest.get_procedure(current_mode)
            if proc_text:
                sections.append(f"# ACTIVE PROCEDURE: {current_mode.upper()}\n{proc_text}")

        # 3. Narrative Context (RAG)
        session = Session.from_json(game_session.session_data)
        session.id = game_session.id
        
        narrative_mems = self.mem_retriever.get_relevant(
            session, chat_history, kinds=["episodic", "lore", "semantic"], limit=8
        )
        if narrative_mems:
            sections.append(
                self.mem_retriever.format_for_prompt(narrative_mems, "STORY CONTEXT")
            )

        # 4. Spatial Context
        spatial_context = self._build_spatial_context(game_session.id)
        if spatial_context:
            sections.append(spatial_context)

        return "\n\n".join(sections)

    def _build_manifest_context(self) -> str:
        """Generates the cheat sheet for the active game system."""
        lines = [f"# GAME SYSTEM: {self.manifest.name}"]
        
        # Engine (Dice, Success, Crit)
        lines.append(self.manifest.get_engine_text())
        
        # Valid Paths (The Vocabulary)
        lines.append(self.manifest.get_path_hints())
        
        return "\n".join(lines)

    def _build_tool_examples(self) -> str:
        """Examples of how to use the 6 Atomic Tools."""
        return """# TOOL USAGE EXAMPLES

1. **Modify Stats/HP (adjust):**
   `{"name": "adjust", "path": "resources.hp.current", "delta": -5, "reason": "Goblin ambush"}`

2. **Set Specific Values (set):**
   `{"name": "set", "path": "status.is_hiding", "value": true}`
   `{"name": "set", "path": "inventory.weapon", "value": "Longsword"}`

3. **Roll Dice (roll):**
   `{"name": "roll", "formula": "1d20+5", "reason": "Attack vs AC 15"}`

4. **Mark Tracks/Conditions (mark):**
   `{"name": "mark", "path": "resources.stress", "count": 1}` (Fill 1 box)
   `{"name": "mark", "path": "resources.ammo", "count": -1}` (Clear 1 box)

5. **Move Location (move):**
   `{"name": "move", "destination": "loc_tavern"}`

6. **Record Memory (note):**
   `{"name": "note", "content": "The Baron is secretly a vampire.", "kind": "fact"}`
"""

    def _build_legacy_rules(self, game_session) -> str:
        """Fallback for setup phase or missing manifest."""
        manifest_data = SetupManifest(self.db).get_manifest(game_session.id)
        ruleset_id = manifest_data.get("ruleset_id")
        if ruleset_id:
            ruleset = self.db.rulesets.get_by_id(ruleset_id)
            if ruleset:
                e = ruleset.engine
                return f"# ENGINE CONFIG\n- Dice: {e.dice_notation}\n- Mechanic: {e.roll_mechanic}"
        return ""

    def _build_spatial_context(self, session_id: int) -> str:
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene:
                return ""
            lines = []
            loc_key = scene.get("location_key")
            if loc_key:
                location = self.db.game_state.get_entity(session_id, "location", loc_key)
                if location:
                    lines.append(f"# LOCATION: {location.get('name', 'Unknown')} ({loc_key}) #")
                    lines.append(location.get("description_visual", ""))
                    conns = location.get("connections", {})
                    if conns:
                        exits = [f"{d.upper()} -> {data.get('display_name')}" for d, data in conns.items()]
                        lines.append("Exits: " + ", ".join(exits))
            return "\n".join(lines)
        except Exception:
            return ""

    def get_truncated_history(self, session: Session, max_messages: int) -> List[Message]:
        history = session.get_history()
        return history[-max_messages:] if len(history) > max_messages else history
