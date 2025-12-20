import logging
from typing import Optional, Callable, List, Dict

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.prefabs.registry import PREFABS
from app.prefabs.manifest import SystemManifest, EngineConfig, FieldDef, RuleDef
from app.setup.schemas import (
    ExtractedField, ExtractedFieldList, MechanicsExtraction, 
    ProceduresExtraction, RuleListExtraction
)
from app.prompts.templates import (
    SHARED_RULES_SYSTEM_PROMPT, EXTRACT_MECHANICS_PROMPT,
    EXTRACT_FIELDS_PROMPT, EXTRACT_PROCEDURES_PROMPT, EXTRACT_RULES_PROMPT
)

logger = logging.getLogger(__name__)

class ManifestExtractor:
    def __init__(self, llm: LLMConnector, status_callback: Optional[Callable[[str], None]] = None):
        self.llm = llm
        self.status_callback = status_callback
        self.total_steps = 7 # Added Rule Phase

    def _update_status(self, step: int, msg: str):
        if self.status_callback:
            self.status_callback(f"[Step {step}/{self.total_steps}] {msg}")
        logger.info(f"[ManifestExtractor] {msg}")

    def extract(self, rules_text: str) -> SystemManifest:
        # Phase 0
        self._update_status(1, "Ingesting Rules...")
        system_prompt = SHARED_RULES_SYSTEM_PROMPT.format(rules_source=rules_text)
        menu_text = self._build_menu()

        # Phase 1
        self._update_status(2, "Extracting Mechanics...")
        mechanics = self._extract_mechanics(system_prompt)

        # Phase 2: Fields
        all_fields = []
        self._update_status(3, "Extracting Core Stats...")
        all_fields.extend(self._extract_field_group(system_prompt, menu_text, mechanics.aliases, ["attributes", "resources", "progression"]))
        
        self._update_status(4, "Extracting Capabilities...")
        all_fields.extend(self._extract_field_group(system_prompt, menu_text, mechanics.aliases, ["skills", "combat", "status"]))
        
        self._update_status(5, "Extracting Assets...")
        all_fields.extend(self._extract_field_group(system_prompt, menu_text, mechanics.aliases, ["inventory", "features", "meta", "identity", "narrative"]))

        # Phase 3: Procedures
        self._update_status(6, "Extracting Procedures...")
        procedures = self._extract_procedures(system_prompt)

        # Phase 4: Rules RAG
        self._update_status(7, "Indexing Rulebook...")
        rules = self._extract_rules(system_prompt)

        return self._assemble(mechanics, all_fields, procedures, rules)

    def _build_menu(self) -> str:
        lines = ["### AVAILABLE PREFAB TYPES", "Strictly choose from this list."]
        for pid, prefab in PREFABS.items():
            lines.append(f"- **{pid}**: {prefab.ai_hint}")
        return "\n".join(lines)

    def _extract_mechanics(self, prompt: str) -> MechanicsExtraction:
        try:
            return self.llm.get_structured_response(prompt, [Message(role="user", content=EXTRACT_MECHANICS_PROMPT)], MechanicsExtraction, 0.3)
        except Exception:
            return MechanicsExtraction(dice_notation="1d20", resolution_mechanic="Unknown", success_condition="Unknown", crit_rules="None")

    def _extract_field_group(self, prompt: str, menu: str, aliases: Dict, cats: List[str]) -> List[ExtractedField]:
        p = EXTRACT_FIELDS_PROMPT.format(categories=", ".join(cats), menu=menu, aliases=str(aliases))
        try:
            return self.llm.get_structured_response(prompt, [Message(role="user", content=p)], ExtractedFieldList, 0.4).fields
        except Exception:
            return []

    def _extract_procedures(self, prompt: str) -> Dict[str, str]:
        try:
            return self.llm.get_structured_response(prompt, [Message(role="user", content=EXTRACT_PROCEDURES_PROMPT)], ProceduresExtraction, 0.5).model_dump()
        except Exception:
            return {}

    def _extract_rules(self, prompt: str) -> List[RuleDef]:
        try:
            res = self.llm.get_structured_response(
                prompt, 
                [Message(role="user", content=EXTRACT_RULES_PROMPT)], 
                RuleListExtraction, 
                0.5
            )
            return [RuleDef(name=r.name, content=r.content, tags=r.tags) for r in res.rules]
        except Exception as e:
            logger.warning(f"Rule extraction failed: {e}")
            return []

    def _assemble(self, mech, fields, procs, rules) -> SystemManifest:
        unique = {f.path: f for f in fields}
        defs = [FieldDef(path=f.path, label=f.label, prefab=f.prefab, category=f.category, config=f.config, formula=f.formula, usage_hint=f.usage_hint) for f in unique.values()]
        sys_id = "custom_" + str(hash(mech.resolution_mechanic))[:8]
        return SystemManifest(
            id=sys_id, name="Extracted System", 
            engine=EngineConfig(dice=mech.dice_notation, mechanic=mech.resolution_mechanic, success=mech.success_condition, crit=mech.crit_rules, fumble=mech.fumble_rules),
            procedures=procs, fields=defs, aliases=mech.aliases, rules=rules
        )
