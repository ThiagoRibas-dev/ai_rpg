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
    """Returns default Refined scaffolding."""
    ruleset = Ruleset(
        meta={"name": "Default System", "genre": "Generic"},
        physics=PhysicsConfig(
            dice_notation="1d20",
            roll_mechanic="Roll + Mod vs DC",
            success_condition="Result >= Target Number",
            crit_rules="Nat 20 = Critical Success",
        ),
        gameplay_procedures=GameLoopConfig(
            encounter={
                "Standard Combat": ProcedureDef(
                    description="Turn Based Combat",
                    steps=["Roll Initiative", "Take Turns", "Resolve Actions"],
                )
            },
            exploration={
                "Freeform": ProcedureDef(
                    description="General Exploration",
                    steps=["Describe Scene", "Player Action", "Result"],
                )
            },
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
    """Injects scaffolding using Refined Models."""
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
            logger.error(f"Manifest parse error: {e}. Using defaults.")

    if not ruleset_model or not st_model:
        ruleset_model, st_model = _get_default_scaffolding()

    ruleset_model.meta["name"] = (
        f"{ruleset_model.meta.get('name', 'Untitled')} (Session {session_id})"
    )

    try:
        rs_id = db_manager.rulesets.create(ruleset_model)
        st_id = db_manager.stat_templates.create(rs_id, st_model)

        try:
            from app.core.vector_store import VectorStore

            vs = VectorStore()
            rule_dicts = []
            # Updated to use 'rules' field instead of 'mechanics'
            for name, rule in ruleset_model.rules.items():
                d = rule.model_dump()
                d["name"] = name
                rule_dicts.append(d)
            vs.add_rules(rs_id, rule_dicts)
        except Exception as e:
            logger.error(f"Failed to index initial rules: {e}")

        manifest_mgr = SetupManifest(db_manager)
        manifest_mgr.update_manifest(
            session_id,
            {
                "ruleset_id": rs_id,
                "stat_template_id": st_id,
                "genre": ruleset_model.meta.get("genre", "Generic"),
                "tone": ruleset_model.meta.get("tone", "Neutral"),
            },
        )

        # Initialize Player Data
        fund_stats = {a.name: a.default for a in st_model.fundamental_stats.values()}

        vitals = {}
        for name, m in st_model.vital_resources.items():
            vitals[name] = {"current": 10, "max": 10}

        consumables = {}
        for name, m in st_model.consumable_resources.items():
            consumables[name] = {"current": 0, "max": 0}

        skills = {s: 0 for s in st_model.skills.keys()}
        features = {f: [] for f in st_model.features.keys()}

        player_data = {
            "name": "Player",
            "template_id": st_id,
            "identity": {},
            "fundamental_stats": fund_stats,
            "vital_resources": vitals,
            "consumable_resources": consumables,
            "skills": skills,
            "features": features,
            "equipment": {"inventory": [], "equipped": {}},
            "derived_stats": {},
        }

        db_manager.game_state.set_entity(session_id, "character", "player", player_data)

    except Exception as e:
        logger.error(f"Error during scaffolding injection: {e}", exc_info=True)
