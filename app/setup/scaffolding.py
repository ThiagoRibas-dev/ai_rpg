import json
import logging
from app.models.ruleset import Ruleset, PhysicsConfig
from app.models.stat_block import (
    StatBlockTemplate,
    StatValue,
    StatGauge,
    StatCollection,
    CollectionItemField,
)
from app.setup.setup_manifest import SetupManifest

logger = logging.getLogger(__name__)


def _get_default_scaffolding():
    """Returns default scaffolding with Flattened Layout."""
    ruleset = Ruleset(
        meta={"name": "Simple RPG", "genre": "Fantasy"},
        physics=PhysicsConfig(
            dice_notation="1d20",
            roll_mechanic="Roll + Mod >= 10",
            success_condition=">= 10",
            crit_rules="Nat 20",
        ),
    )

    values = {
        "str": StatValue(
            id="str",
            label="Strength",
            widget="number",
            panel="sidebar",
            group="Attributes",
            default=10,
        ),
        "dex": StatValue(
            id="dex",
            label="Dexterity",
            widget="number",
            panel="sidebar",
            group="Attributes",
            default=10,
        ),
        "ac": StatValue(
            id="ac",
            label="Armor Class",
            widget="number",
            panel="main",
            group="Combat",
            default=10,
            calculation="10 + ((dex - 10) // 2)",
        ),
        "class": StatValue(
            id="class",
            label="Class",
            data_type="string",
            widget="text_line",
            panel="header",
            group="Identity",
            default="Adventurer",
        ),
    }

    gauges = {
        "hp": StatGauge(
            id="hp",
            label="Hit Points",
            widget="bar",
            panel="header",
            group="Vitals",
            min_val=0,
            max_formula="10 + ((str - 10) // 2)",
        )
    }

    collections = {
        "inventory": StatCollection(
            id="inventory",
            label="Backpack",
            panel="equipment",
            group="Gear",
            item_schema=[
                CollectionItemField(key="name", label="Item", data_type="string"),
                CollectionItemField(
                    key="qty", label="Qty", data_type="integer", widget="number"
                ),
            ],
        )
    }

    template = StatBlockTemplate(
        template_name="Adventurer",
        values=values,
        gauges=gauges,
        collections=collections,
    )

    return ruleset, template


def inject_setup_scaffolding(session_id: int, prompt_manifest_json: str, db_manager):
    """Injects scaffolding into DB."""
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

        entity_data = {
            "name": "Player",
            "template_id": st_id,
            "values": {k: v.default for k, v in st_model.values.items()},
            "gauges": {
                k: {"current": 10, "max": 10} for k, v in st_model.gauges.items()
            },
            "collections": {k: [] for k, v in st_model.collections.items()},
        }

        db_manager.game_state.set_entity(session_id, "character", "player", entity_data)

        SetupManifest(db_manager).update_manifest(
            session_id,
            {
                "ruleset_id": rs_id,
                "stat_template_id": st_id,
                "genre": ruleset_model.meta.get("genre", "Generic"),
                "tone": ruleset_model.meta.get("tone", "Neutral"),
            },
        )

    except Exception as e:
        logger.error(f"Error during scaffolding injection: {e}", exc_info=True)
