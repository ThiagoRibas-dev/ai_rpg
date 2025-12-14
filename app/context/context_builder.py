import logging
from typing import List
from app.models.session import Session
from app.models.game_session import GameSession
from app.models.message import Message
from app.setup.setup_manifest import SetupManifest
from app.services.state_service import get_entity
from app.models.vocabulary import ROLE_TO_CATEGORY, SemanticRole


class ContextBuilder:
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

        # Base Engine Rules (Static)
        manifest = SetupManifest(self.db).get_manifest(game_session.id)
        ruleset_id = manifest.get("ruleset_id")

        if ruleset_id:
            ruleset = self.db.rulesets.get_by_id(ruleset_id)
            if ruleset:
                sections.append(self._render_engine_config(ruleset))

        # Vocabulary Hints (Valid Paths)
        vocab_hints = self._build_vocabulary_hints(manifest)
        if vocab_hints:
            sections.append(vocab_hints)

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

        # 1. State
        state_text = self.state_builder.build(game_session.id)
        if state_text:
            sections.append(f"# CURRENT STATE #\n{state_text}")

        # 2. Procedures (Mode-Specific)
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

        # 3. Narrative Context (Episodic + Lore)
        session = Session.from_json(game_session.session_data)
        session.id = game_session.id

        narrative_mems = self.mem_retriever.get_relevant(
            session, chat_history, kinds=["episodic", "lore", "semantic"], limit=8
        )
        if narrative_mems:
            sections.append(
                self.mem_retriever.format_for_prompt(narrative_mems, "STORY CONTEXT")
            )

        # 4. Rules Context (RAG: Semantic + Tag-Based)
        # A. Gather Tags from Player State
        active_tags = []
        player = get_entity(game_session.id, self.db, "character", "player")
        if player:
            # Look in 'features', 'conditions' (if exists), or 'attributes'
            for cat in ["features", "conditions"]:
                data = player.get(cat, {})
                if isinstance(data, list):
                    active_tags.extend([str(i) for i in data])
                elif isinstance(data, dict):
                    active_tags.extend(data.keys())

        # B. Retrieve Rules
        rule_mems = self.mem_retriever.get_relevant(
            session,
            chat_history,
            kinds=["rule"],
            limit=5,
            extra_tags=active_tags,  # Pass active tags to boost relevant rules
        )

        if rule_mems:
            sections.append(
                self.mem_retriever.format_for_prompt(
                    rule_mems, "RELEVANT RULES & MECHANICS"
                )
            )

        # 5. Spatial
        spatial_context = self._build_spatial_context(game_session.id)
        if spatial_context:
            sections.append(spatial_context)

        return "\n\n".join(sections)

    def _render_engine_config(self, ruleset) -> str:
        e = ruleset.engine
        lines = ["# ENGINE CONFIG"]
        lines.append(f"- **Dice**: {e.dice_notation}")
        lines.append(f"- **Resolution**: {e.roll_mechanic}")
        lines.append(f"- **Success**: {e.success_condition}")
        lines.append(f"- **Crit**: {e.crit_rules}")
        return "\n".join(lines)

    def _render_procedures(self, ruleset, mode: str) -> str:
        target_dict = {}
        if mode in ["combat", "encounter"]:
            target_dict = ruleset.combat_procedures
        elif mode in ["exploration", "travel"]:
            target_dict = ruleset.exploration_procedures
        elif mode == "social":
            target_dict = ruleset.social_procedures
        elif mode == "downtime":
            target_dict = ruleset.downtime_procedures

        if not target_dict:
            return ""

        lines = []
        for name, proc in target_dict.items():
            lines.append(f"**{name} ({proc.description})**")
            for step in proc.steps:
                lines.append(f"  {step}")
            lines.append("")
        return "\n".join(lines)

    def _build_vocabulary_hints(self, manifest: dict) -> str:
        """
        Build vocabulary hints for the LLM context.
        Updated to use canonical paths from ROLE_TO_CATEGORY.
        """
        vocab_data = manifest.get("vocabulary")
        if not vocab_data:
            return ""

        try:
            from app.models.vocabulary import GameVocabulary

            vocab = GameVocabulary(**vocab_data)

            lines = ["# VALID UPDATE PATHS #"]

            # Group by semantic role
            for role in SemanticRole:
                # Map role (e.g. core_trait) to category (e.g. attributes)
                category = ROLE_TO_CATEGORY.get(role, role.value)

                # Filter paths that start with this category
                # valid_paths are now like "attributes.str", "resources.hp"
                role_paths = [
                    p for p in vocab.valid_paths if p.startswith(f"{category}.")
                ]

                if role_paths:
                    lines.append(
                        f"**{category.replace('_', ' ').title()}**: {', '.join(role_paths[:6])}"
                    )
                    if len(role_paths) > 6:
                        lines.append(f"  ... and {len(role_paths) - 6} more")

            return "\n".join(lines)
        except Exception as e:
            self.logger.debug(f"Failed to build vocabulary hints: {e}")
            return ""

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
            return "\n".join(lines)
        except Exception as e:
            self.logger.debug(f"Failed to build spatial context: {e}")
            return ""

    def get_truncated_history(
        self, session: Session, max_messages: int
    ) -> List[Message]:
        history = session.get_history()
        return history[-max_messages:] if len(history) > max_messages else history
