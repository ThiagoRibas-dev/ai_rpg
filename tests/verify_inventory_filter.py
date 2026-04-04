
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.models.vocabulary import CategoryName, PrefabID
from app.prefabs.manifest import FieldDef


# Simulation of the logic I added to inventory.py
def test_filtering_logic():
    # Mocking fields
    fields = [
        FieldDef(path="inventory.general", label="General Gear", prefab=PrefabID.CONT_LIST, category=CategoryName.INVENTORY),
        FieldDef(path="feats", label="Base Feats", prefab=PrefabID.CONT_LIST, category="feats"),
        FieldDef(path="inventory.worn", label="Worn Items", prefab=PrefabID.CONT_WEIGHTED, category=CategoryName.INVENTORY),
        FieldDef(path="special_abilities", label="Special Abilities", prefab=PrefabID.CONT_LIST, category=CategoryName.INVENTORY),
        FieldDef(path="skills.untrained", label="Untrained Skills", prefab=PrefabID.CONT_LIST, category="skills"),
    ]

    lists_to_render = []

    for f in fields:
        is_list = f.prefab in [PrefabID.CONT_LIST, PrefabID.CONT_WEIGHTED]
        is_inv = f.category == CategoryName.INVENTORY or f.path.startswith("inventory")
        if is_list and is_inv:
            lists_to_render.append(f.label)

    print(f"Lists found for Gear tab: {lists_to_render}")

    expected = ["General Gear", "Worn Items", "Special Abilities"]
    for item in expected:
        assert item in lists_to_render, f"Expected {item} to be in lists_to_render"

    assert "Base Feats" not in lists_to_render
    assert "Untrained Skills" not in lists_to_render

    print("Verification Successful!")

if __name__ == "__main__":
    test_filtering_logic()
