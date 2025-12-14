import os
from pathlib import Path

# =============================================================================
# CONTENT TO APPEND: Factory Functions
# =============================================================================

FACTORY_FUNCTIONS_CONTENT = """

# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_dnd_like_vocabulary(system_name: str = "D&D 5e") -> GameVocabulary:
    \"\"\"
    Create a vocabulary for D&D-like systems.
    
    Useful for testing or as a fallback when extraction fails.
    \"\"\"
    vocab = GameVocabulary(
        system_name=system_name,
        system_id=system_name.lower().replace(" ", "_"),
        genre="fantasy",
        dice_notation="d20",
        resolution_mechanic="d20 + modifier vs DC",
    )
    
    # Core traits (ability scores)
    for key, label in [
        ("strength", "Strength"),
        ("dexterity", "Dexterity"),
        ("constitution", "Constitution"),
        ("intelligence", "Intelligence"),
        ("wisdom", "Wisdom"),
        ("charisma", "Charisma"),
    ]:
        vocab.add_field(FieldDefinition(
            key=key,
            label=label,
            semantic_role=SemanticRole.CORE_TRAIT,
            field_type=FieldType.NUMBER,
            default_value=10,
            min_value=1,
            max_value=30,
        ))
    
    # Resources
    vocab.add_field(FieldDefinition(
        key="hp",
        label="Hit Points",
        semantic_role=SemanticRole.RESOURCE,
        field_type=FieldType.POOL,
        can_go_negative=True,
        min_value=-10,
    ))
    
    # Progression
    vocab.add_field(FieldDefinition(
        key="level",
        label="Level",
        semantic_role=SemanticRole.PROGRESSION,
        field_type=FieldType.NUMBER,
        default_value=1,
        min_value=1,
        max_value=20,
    ))
    
    vocab.add_field(FieldDefinition(
        key="xp",
        label="Experience Points",
        semantic_role=SemanticRole.PROGRESSION,
        field_type=FieldType.NUMBER,
        default_value=0,
        min_value=0,
    ))
    
    return vocab


def create_fate_like_vocabulary(system_name: str = "Fate Core") -> GameVocabulary:
    \"\"\"
    Create a vocabulary for Fate-like systems.
    
    Demonstrates non-D&D field types (ladders, tracks, tags).
    \"\"\"
    vocab = GameVocabulary(
        system_name=system_name,
        system_id=system_name.lower().replace(" ", "_"),
        genre="universal",
        dice_notation="4dF",
        resolution_mechanic="4dF + skill vs opposition",
        terminology={
            "damage": "stress",
            "health": "stress track",
            "critical": "boost",
        },
    )
    
    # Ladder labels for Fate
    fate_ladder = {
        -2: "Terrible",
        -1: "Poor",
        0: "Mediocre",
        1: "Average",
        2: "Fair",
        3: "Good",
        4: "Great",
        5: "Superb",
        6: "Fantastic",
    }
    
    # Approaches (FAE style)
    for key, label in [
        ("careful", "Careful"),
        ("clever", "Clever"),
        ("flashy", "Flashy"),
        ("forceful", "Forceful"),
        ("quick", "Quick"),
        ("sneaky", "Sneaky"),
    ]:
        vocab.add_field(FieldDefinition(
            key=key,
            label=label,
            semantic_role=SemanticRole.CORE_TRAIT,
            field_type=FieldType.LADDER,
            default_value=1,
            min_value=-1,
            max_value=6,
            ladder_labels=fate_ladder,
        ))
    
    # Stress tracks
    vocab.add_field(FieldDefinition(
        key="physical_stress",
        label="Physical Stress",
        semantic_role=SemanticRole.RESOURCE,
        field_type=FieldType.TRACK,
        track_length=3,
    ))
    
    vocab.add_field(FieldDefinition(
        key="mental_stress",
        label="Mental Stress",
        semantic_role=SemanticRole.RESOURCE,
        field_type=FieldType.TRACK,
        track_length=3,
    ))
    
    # Fate points
    vocab.add_field(FieldDefinition(
        key="fate_points",
        label="Fate Points",
        semantic_role=SemanticRole.RESOURCE,
        field_type=FieldType.NUMBER,
        default_value=3,
        min_value=0,
    ))
    
    # Aspects
    vocab.add_field(FieldDefinition(
        key="high_concept",
        label="High Concept",
        semantic_role=SemanticRole.ASPECT,
        field_type=FieldType.TAG,
    ))
    
    vocab.add_field(FieldDefinition(
        key="trouble",
        label="Trouble",
        semantic_role=SemanticRole.ASPECT,
        field_type=FieldType.TAG,
    ))
    
    # Consequences
    for severity in ["mild", "moderate", "severe"]:
        vocab.add_field(FieldDefinition(
            key=f"{severity}_consequence",
            label=f"{severity.title()} Consequence",
            semantic_role=SemanticRole.STATUS,
            field_type=FieldType.TAG,
        ))
    
    return vocab
"""


def apply_fix():
    base_dir = Path(__file__).parent
    vocab_path = base_dir / "app" / "models" / "vocabulary.py"

    if not vocab_path.exists():
        print(f"Error: {vocab_path} not found.")
        return

    # Check if factories are already present to avoid double append
    with open(vocab_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "def create_dnd_like_vocabulary" in content:
        print("Factory functions already exist. Skipping.")
        return

    print(f"Appending factory functions to {vocab_path}...")
    with open(vocab_path, "a", encoding="utf-8") as f:
        f.write(FACTORY_FUNCTIONS_CONTENT)

    print("Fix applied successfully.")


if __name__ == "__main__":
    apply_fix()
