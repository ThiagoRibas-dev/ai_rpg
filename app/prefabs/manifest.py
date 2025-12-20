"""
Manifest Data Structures
========================
Defines the core dataclasses for system manifests.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.prefabs.registry import PREFABS

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {
    "identity",
    "attributes",
    "skills",
    "resources",
    "features",
    "inventory",
    "progression",
    "status",
    "combat",
    "connections",
    "narrative",
    "meta",
}


@dataclass
class FieldDef:
    path: str
    label: str
    prefab: str
    category: str
    config: Dict[str, Any] = field(default_factory=dict)
    formula: Optional[str] = None
    max_formula: Optional[str] = None
    default_formula: Optional[str] = None
    threshold_hint: Optional[str] = None
    usage_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "path": self.path,
            "label": self.label,
            "prefab": self.prefab,
            "category": self.category,
        }
        if self.config:
            result["config"] = self.config
        if self.formula:
            result["formula"] = self.formula
        if self.max_formula:
            result["max_formula"] = self.max_formula
        if self.default_formula:
            result["default_formula"] = self.default_formula
        if self.threshold_hint:
            result["threshold_hint"] = self.threshold_hint
        if self.usage_hint:
            result["usage_hint"] = self.usage_hint
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldDef":
        return cls(
            path=data["path"],
            label=data["label"],
            prefab=data["prefab"],
            category=data["category"],
            config=data.get("config", {}),
            formula=data.get("formula"),
            max_formula=data.get("max_formula"),
            default_formula=data.get("default_formula"),
            threshold_hint=data.get("threshold_hint"),
            usage_hint=data.get("usage_hint"),
        )


@dataclass
class EngineConfig:
    dice: str
    mechanic: str
    success: str
    crit: str
    fumble: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EngineConfig":
        return cls(**data)

    def to_prompt_text(self) -> str:
        lines = [
            f"**Dice:** {self.dice}",
            f"**Mechanic:** {self.mechanic}",
            f"**Success:** {self.success}",
        ]
        if self.crit:
            lines.append(f"**Critical:** {self.crit}")
        if self.fumble:
            lines.append(f"**Fumble:** {self.fumble}")
        return "\n".join(lines)


@dataclass
class RuleDef:
    name: str
    content: str
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "content": self.content, "tags": self.tags}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuleDef":
        return cls(
            name=data["name"], content=data["content"], tags=data.get("tags", [])
        )


@dataclass
class SystemManifest:
    id: str
    name: str
    engine: EngineConfig
    procedures: Dict[str, str] = field(default_factory=dict)
    fields: List[FieldDef] = field(default_factory=list)
    aliases: Dict[str, str] = field(default_factory=dict)
    rules: List[RuleDef] = field(default_factory=list)  # RAG Knowledge Base

    def get_field(self, path: str) -> Optional[FieldDef]:
        for f in self.fields:
            if f.path == path:
                return f
        return None

    def get_fields_by_category(self, category: str) -> List[FieldDef]:
        return [f for f in self.fields if f.category == category]

    def get_categories(self) -> List[str]:
        return sorted(set(f.category for f in self.fields))

    def get_path_hints(self) -> str:
        lines = ["## VALID PATHS"]
        for category in self.get_categories():
            fields = self.get_fields_by_category(category)
            if not fields:
                continue
            lines.append(f"\n**{category.title()}:**")
            for f in fields:
                prefab = PREFABS.get(f.prefab)
                hint = prefab.ai_hint if prefab else ""
                suffix = ".current" if f.prefab == "RES_POOL" else ""
                lines.append(f"  `{f.path}{suffix}` - {f.label} ({hint})")
        return "\n".join(lines)

    def get_procedure(self, mode: str) -> Optional[str]:
        return self.procedures.get(mode.lower())

    def get_engine_text(self) -> str:
        return self.engine.to_prompt_text()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "engine": self.engine.to_dict(),
            "procedures": self.procedures,
            "fields": [f.to_dict() for f in self.fields],
            "aliases": self.aliases,
            "rules": [r.to_dict() for r in self.rules],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemManifest":
        return cls(
            id=data["id"],
            name=data["name"],
            engine=EngineConfig.from_dict(data.get("engine", {})),
            procedures=data.get("procedures", {}),
            fields=[FieldDef.from_dict(f) for f in data.get("fields", [])],
            aliases=data.get("aliases", {}),
            rules=[RuleDef.from_dict(r) for r in data.get("rules", [])],
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "SystemManifest":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_file(cls, path: Path) -> "SystemManifest":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
