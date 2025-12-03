import json
import logging
from app.models.ruleset import Ruleset, PhysicsConfig
from app.models.sheet_schema import CharacterSheetSpec, SheetField, FieldDisplay
from app.setup.setup_manifest import SetupManifest

logger = logging.getLogger(__name__)


def _get_default_scaffolding():
    """Returns a default Ruleset and CharacterSheetSpec (New Schema)."""

    ruleset = Ruleset(
        meta={"name": "Simple RPG", "genre": "Fantasy"},
        physics=PhysicsConfig(
            dice_notation="1d20",
            roll_mechanic="Roll+Mod",
            success_condition=">=10",
            crit_rules="Nat 20",
        ),
    )

    # Define the Sheet Structure
    spec = CharacterSheetSpec()

    # Attributes
    spec.attributes.fields = {
        "str": SheetField(
            key="str",
            container_type="atom",
            data_type="number",
            default=10,
            display=FieldDisplay(widget="number", label="Strength"),
        ),
        "dex": SheetField(
            key="dex",
            container_type="atom",
            data_type="number",
            default=10,
            display=FieldDisplay(widget="number", label="Dexterity"),
        ),
    }

    # Resources (HP)
    spec.resources.fields = {
        "hp": SheetField(
            key="hp",
            container_type="molecule",
            display=FieldDisplay(widget="pool", label="Hit Points"),
            components={
                "current": SheetField(
                    key="current",
                    container_type="atom",
                    data_type="number",
                    default=10,
                    display=FieldDisplay(widget="number", label="Cur"),
                ),
                "max": SheetField(
                    key="max",
                    container_type="atom",
                    data_type="derived",
                    default=10,
                    formula="10 + ((str - 10) // 2)",
                    display=FieldDisplay(widget="number", label="Max"),
                ),
            },
        )
    }

    # Derived (AC)
    spec.attributes.fields["ac"] = SheetField(
        key="ac",
        container_type="atom",
        data_type="derived",
        default=10,
        formula="10 + ((dex - 10) // 2)",
        display=FieldDisplay(widget="number", label="Armor Class"),
    )

    # Inventory
    spec.inventory.fields = {
        "backpack": SheetField(
            key="backpack",
            container_type="list",
            display=FieldDisplay(widget="repeater", label="Backpack"),
            item_schema={
                "name": SheetField(
                    key="name",
                    container_type="atom",
                    data_type="string",
                    display=FieldDisplay(widget="text", label="Item"),
                ),
                "qty": SheetField(
                    key="qty",
                    container_type="atom",
                    data_type="number",
                    default=1,
                    display=FieldDisplay(widget="number", label="Qty"),
                ),
            },
        )
    }

    return ruleset, spec


# ... (Rest of file is mostly unchanged, just ensure imports match)
def inject_setup_scaffolding(session_id: int, prompt_manifest_json: str, db_manager):
    ruleset_model, st_model = _get_default_scaffolding()

    if prompt_manifest_json and prompt_manifest_json != "{}":
        try:
            data = json.loads(prompt_manifest_json)
            if data.get("ruleset"):
                ruleset_model = Ruleset(**data["ruleset"])
        except Exception:
            pass

    ruleset_model.meta["name"] = (
        f"{ruleset_model.meta.get('name', 'Untitled')} (Session {session_id})"
    )
    rs_id = db_manager.rulesets.create(ruleset_model)
    st_id = db_manager.stat_templates.create(rs_id, st_model)

    entity_data = {
        "name": "Player",
        "template_id": st_id,
        "attributes": {"str": 10, "dex": 10, "ac": 10},
        "resources": {"hp": {"current": 10, "max": 10}},
        "inventory": {"backpack": []},
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
