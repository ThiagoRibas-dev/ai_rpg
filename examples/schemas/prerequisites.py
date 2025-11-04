from pydantic import Field
from typing import Union
from .base import SchemaModel

class Prerequisite(SchemaModel):
    """Base model for a prerequisite."""
    type: str = Field(..., description="The type of the prerequisite.")

class AbilityPrerequisite(Prerequisite):
    """Prerequisite based on a minimum ability score."""
    type: str = Field("ability")
    ability: str = Field(..., description="The ability score required (e.g., 'strength', 'dexterity').")
    minimum_value: int = Field(..., description="The minimum score required.")

class SkillPrerequisite(Prerequisite):
    """Prerequisite based on a minimum number of ranks in a skill."""
    type: str = Field("skill")
    skill: str = Field(..., description="The skill required (e.g., 'spellcraft', 'knowledge_arcana').")
    minimum_ranks: int = Field(..., description="The minimum number of ranks required.")

class BABPrerequisite(Prerequisite):
    """Prerequisite based on a minimum Base Attack Bonus."""
    type: str = Field("bab")
    minimum_value: int = Field(..., description="The minimum Base Attack Bonus required.")

class FeatPrerequisite(Prerequisite):
    """Prerequisite based on possessing a specific feat."""
    type: str = Field("feat")
    feat_id: str = Field(..., description="The ID of the required feat.")

class ClassLevelPrerequisite(Prerequisite):
    """Prerequisite based on a minimum level in a specific class."""
    type: str = Field("class_level")
    class_id: str = Field(..., description="The ID of the required class.")
    minimum_level: int = Field(..., description="The minimum level required in the class.")

class SpellcastingPrerequisite(Prerequisite):
    """Prerequisite based on the ability to cast spells of a certain level."""
    type: str = Field("spellcasting")
    minimum_spell_level: int = Field(..., description="The minimum spell level the character must be able to cast.")
    spellcasting_type: str = Field("any", description="The type of spellcasting required (e.g., 'arcane', 'divine', 'any').")

class SpecialPrerequisite(Prerequisite):
    """A special or descriptive prerequisite that doesn't fit other categories."""
    type: str = Field("special")
    description: str = Field(..., description="A textual description of the prerequisite.")

PrerequisiteType = Union[
    AbilityPrerequisite,
    SkillPrerequisite,
    BABPrerequisite,
    FeatPrerequisite,
    ClassLevelPrerequisite,
    SpellcastingPrerequisite,
    SpecialPrerequisite,
]