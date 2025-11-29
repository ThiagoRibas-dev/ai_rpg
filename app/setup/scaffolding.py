import json
import logging
from app.models.ruleset import Ruleset, PhysicsConfig, GameLoopConfig, ProcedureDef
from app.models.stat_block import (
    StatBlockTemplate,
    IdentityDef,
    FundamentalStatDef,
    VitalResourceDef,
    EquipmentConfig,
)
from app.setup.setup_manifest import SetupManifest

logger = logging.getLogger(__name__)


def _get_default_scaffolding():
    ruleset = Ruleset(
        meta={"name": "Default", "genre": "Generic"},
        physics=PhysicsConfig(
            dice_notation="1d20",
            roll_mechanic="Roll+Mod",
            success_condition=">=DC",
            crit_rules="Nat20",
        ),
        gameplay_loops=GameLoopConfig(
            combat=ProcedureDef(
                name="Combat", description="Turn Based", steps=["Action"]
            ),
            exploration=ProcedureDef(
                name="Exploration", description="Freeform", steps=["Act"]
            ),
        ),
    )

    template = StatBlockTemplate(
        template_name="Adventurer",
        identity_categories={"Class": IdentityDef(value_type="selection")},
        fundamental_stats={
            "Strength": FundamentalStatDef(default=10),
            "Agility": FundamentalStatDef(default=10),
        },
        vital_resources={
            "HP": VitalResourceDef(max_formula="10", on_zero="Unconscious")
        },
        equipment=EquipmentConfig(slots={"Main Hand": ["Weapon"], "Body": ["Armor"]}),
    )
    return ruleset, template


def inject_setup_scaffolding(session_id: int, prompt_manifest_json: str, db_manager):
    ruleset_model = None
    st_model = None

    if prompt_manifest_json and prompt_manifest_json != "{}":
        try:
            data = json.loads(prompt_manifest_json)
            if data.get("ruleset"):
                ruleset_model = Ruleset(**data["ruleset"])
            if data.get("stat_template"):
                st_model = StatBlockTemplate(**data["stat_template"])
        except Exception as e:
            logger.error(f"Manifest error: {e}")

    if not ruleset_model or not st_model:
        ruleset_model, st_model = _get_default_scaffolding()

    ruleset_model.meta["name"] = (
        f"{ruleset_model.meta.get('name', 'Untitled')} (Session {session_id})"
    )

    try:
        rs_id = db_manager.rulesets.create(ruleset_model)
        st_id = db_manager.stat_templates.create(rs_id, st_model)

        # Add rules to Vector Store (Convert dict to list for embedding)
        try:
            from app.core.vector_store import VectorStore

            vs = VectorStore()
            # Convert Map to List of Objects for embedding logic
            rule_dicts = []
            for name, rule in ruleset_model.mechanics.items():
                d = rule.model_dump()
                d["name"] = name  # Inject name back for vector store indexing
                rule_dicts.append(d)
            vs.add_rules(rs_id, rule_dicts)
        except Exception as e:
            logger.error(f"Vector store error: {e}")

        SetupManifest(db_manager).update_manifest(
            session_id,
            {
                "ruleset_id": rs_id,
                "stat_template_id": st_id,
                "genre": ruleset_model.meta.get("genre"),
                "tone": ruleset_model.meta.get("tone"),
            },
        )

        # Init Player
        player_data = {
            "name": "Player",
            "template_id": st_id,
            "identity": {},
            "fundamental_stats": {
                k: v.default for k, v in st_model.fundamental_stats.items()
            },
            "vital_resources": {
                k: {"current": 10, "max": 10} for k in st_model.vital_resources
            },
            "consumable_resources": {
                k: {"current": 0, "max": 0} for k in st_model.consumable_resources
            },
            "skills": {k: 0 for k in st_model.skills},
            "features": {k: [] for k in st_model.features},
            "equipment": {"inventory": [], "equipped": {}},
            "derived_stats": {},
        }
        db_manager.game_state.set_entity(session_id, "character", "player", player_data)

    except Exception as e:
        logger.error(f"Injection error: {e}", exc_info=True)
