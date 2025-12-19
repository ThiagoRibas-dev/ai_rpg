from typing import Literal, Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator

# Define valid prefabs strictly matching app.prefabs.registry
ValidPrefabType = Literal[
    "VAL_INT", "VAL_COMPOUND", "VAL_STEP_DIE", "VAL_LADDER", "VAL_BOOL", "VAL_TEXT",
    "RES_POOL", "RES_COUNTER", "RES_TRACK",
    "CONT_LIST", "CONT_TAGS", "CONT_WEIGHTED"
]

CategoryType = Literal[
    "attributes", "resources", "skills", "inventory", "features",
    "progression", "combat", "status", "meta", "identity", "narrative"
]

class ExtractedField(BaseModel):
    label: str
    path: str = Field(..., description="snake_case.path")
    prefab: ValidPrefabType
    category: CategoryType
    config: Dict[str, Any] = Field(default_factory=dict)
    formula: Optional[str] = None
    usage_hint: str = Field(..., description="Short explanation for the AI")

    @field_validator('prefab', mode='before')
    @classmethod
    def sanitize(cls, v):
        mapping = {
            "VAL_NUMBER": "VAL_INT", 
            "RES_BAR": "RES_POOL", 
            "VAL_DIE": "VAL_STEP_DIE",
            "CONT_ARRAY": "CONT_LIST"
        }
        return mapping.get(v, v)

class ExtractedFieldList(BaseModel):
    fields: List[ExtractedField]

class MechanicsExtraction(BaseModel):
    dice_notation: str
    resolution_mechanic: str
    success_condition: str
    crit_rules: str
    fumble_rules: str = ""
    aliases: Dict[str, str] = Field(default_factory=dict, description="Global derived stats formulas (e.g. str_mod)")

class ProceduresExtraction(BaseModel):
    combat: str = ""
    exploration: str = ""
    social: str = ""
    downtime: str = ""
