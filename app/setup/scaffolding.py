import logging
from app.models.ruleset import Ruleset
from app.models.sheet_schema import CharacterSheetSpec, SheetField, FieldDisplay

logger = logging.getLogger(__name__)

def get_default_scaffolding():
    """
    Returns a default Ruleset and CharacterSheetSpec (New Schema).
    Used as a fallback when LLM generation fails or for quick-start.
    """
    ruleset = Ruleset(
        meta={"name": "Simple RPG", "genre": "Fantasy"},
        engine={
            "dice_notation": "1d20",
            "roll_mechanic": "Roll + Stat",
            "success_condition": ">= 10",
            "crit_rules": "Nat 20"
        }
    )

    # Define the Sheet Structure using the Unified Schema
    spec = CharacterSheetSpec()

    # 1. Attributes (Atoms)
    spec.attributes.fields = {
        "str": SheetField(
            key="str", 
            container_type="atom", 
            data_type="number", 
            default=10, 
            display=FieldDisplay(widget="number", label="Strength")
        ),
        "dex": SheetField(
            key="dex", 
            container_type="atom", 
            data_type="number", 
            default=10, 
            display=FieldDisplay(widget="number", label="Dexterity")
        ),
        "ac": SheetField(
            key="ac",
            container_type="atom",
            data_type="derived",
            default=10,
            formula="10 + ((dex - 10) // 2)",
            display=FieldDisplay(widget="number", label="Armor Class")
        )
    }

    # 2. Resources (Molecules)
    spec.resources.fields = {
        "hp": SheetField(
            key="hp",
            container_type="molecule",
            display=FieldDisplay(widget="pool", label="Hit Points"),
            components={
                "current": SheetField(
                    key="current", container_type="atom", data_type="number", default=10,
                    display=FieldDisplay(widget="number", label="Cur")
                ),
                "max": SheetField(
                    key="max", container_type="atom", data_type="derived", default=10,
                    formula="10 + ((str - 10) // 2)",
                    display=FieldDisplay(widget="number", label="Max")
                )
            }
        )
    }

    # 3. Inventory (List)
    spec.inventory.fields = {
        "backpack": SheetField(
            key="backpack",
            container_type="list",
            display=FieldDisplay(widget="repeater", label="Backpack"),
            item_schema={
                "name": SheetField(key="name", display=FieldDisplay(label="Item")),
                "qty": SheetField(key="qty", data_type="number", default=1, display=FieldDisplay(label="Qty"))
            }
        )
    }

    return ruleset, spec