import logging
import os
import sys
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.models.vocabulary import CategoryName, PrefabID
from app.setup.manifest_extractor import ManifestExtractor
from app.setup.schemas import ExtractedField, MechanicsExtraction

logging.basicConfig(level=logging.INFO)

def test_stable_id():
    extractor = ManifestExtractor(MagicMock())
    assert extractor._derive_system_id("Dungeons & Dragons 3.5e") == "dnd_3_5e"
    assert extractor._derive_system_id("My Awesome RPG") == "my_awesome_rpg"
    assert extractor._derive_system_id("Pathfinder 2e!") == "pathfinder_2e"
    print("✅ Stable ID test passed.")

def test_alias_normalization():
    extractor = ManifestExtractor(MagicMock())

    fields = [
        ExtractedField(path="attributes.str", label="STR", prefab=PrefabID.VAL_COMPOUND, category=CategoryName.ATTRIBUTES, usage_hint="..."),
        ExtractedField(path="attributes.dex", label="DEX", prefab=PrefabID.VAL_COMPOUND, category=CategoryName.ATTRIBUTES, usage_hint="..."),
        ExtractedField(path="skills.climb", label="Climb", prefab=PrefabID.VAL_INT, category=CategoryName.SKILLS, usage_hint="..."),
    ]

    aliases = {
        "str_mod": "(attributes.str - 10) / 2",
        "dex_mod": "floor((attributes.dex - 10) / 2)",
        "ac": "10 + dex_mod",
    }

    normalized = extractor._normalize_aliases(aliases, fields)

    assert normalized["str_mod"] == "(attributes.str.score - 10) / 2"
    assert normalized["dex_mod"] == "floor((attributes.dex.score - 10) / 2)"
    assert normalized["ac"] == "10 + dex_mod" # Should not change because 'dex_mod' is not in compound_paths
    print("✅ Alias normalization test passed.")

def test_assemble_with_new_logic():
    extractor = ManifestExtractor(MagicMock())
    mech = MechanicsExtraction(
        system_name="Dungeons & Dragons 3.5e",
        dice_notation="1d20",
        resolution_mechanic="d20 + mod",
        success_condition=">= DC",
        crit_rules="Nat 20",
        fumble_rules="Nat 1",
        aliases={"mod": "attributes.str"}
    )
    fields = [
        ExtractedField(path="attributes.str", label="STR", prefab=PrefabID.VAL_COMPOUND, category=CategoryName.ATTRIBUTES, usage_hint="...")
    ]

    manifest = extractor._assemble(mech, fields, {}, [])

    assert manifest.id == "dnd_3_5e"
    assert manifest.name == "Dungeons & Dragons 3.5e"
    assert manifest.aliases["mod"] == "attributes.str.score"
    print("✅ Assembly logic test passed.")

if __name__ == "__main__":
    try:
        test_stable_id()
        test_alias_normalization()
        test_assemble_with_new_logic()
        print("\nAll logical verifications passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)
