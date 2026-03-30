from unittest.mock import MagicMock
from app.setup.manifest_extractor import ManifestExtractor
from app.setup.schemas import ExtractedField, MechanicsExtraction
from app.models.vocabulary import CategoryName, PrefabID

def test_stable_id():
    extractor = ManifestExtractor(MagicMock())
    assert extractor._derive_system_id("Dungeons & Dragons 3.5e") == "dnd_3_5e"
    assert extractor._derive_system_id("My Awesome RPG") == "my_awesome_rpg"
    assert extractor._derive_system_id("Pathfinder 2e!") == "pathfinder_2e"

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
