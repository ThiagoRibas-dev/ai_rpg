import logging
from typing import Optional, Callable, List, Dict

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.prefabs.registry import PREFABS
from app.prefabs.manifest import SystemManifest, EngineConfig, FieldDef
from app.setup.schemas import (
    ExtractedField, 
    ExtractedFieldList, 
    MechanicsExtraction, 
    ProceduresExtraction
)
from app.prompts.templates import (
    SHARED_RULES_SYSTEM_PROMPT,
    EXTRACT_MECHANICS_PROMPT,
    EXTRACT_FIELDS_PROMPT,
    EXTRACT_PROCEDURES_PROMPT
)

logger = logging.getLogger(__name__)

class ManifestExtractor:
    """
    Extracts a strict SystemManifest from raw rules text using a 3-Phase pipeline.
    Phase 1: Mechanics & Aliases
    Phase 2: Fields (Iterative Groups)
    Phase 3: Procedures
    """

    def __init__(
        self, 
        llm: LLMConnector, 
        status_callback: Optional[Callable[[str], None]] = None
    ):
        self.llm = llm
        self.status_callback = status_callback
        self.total_steps = 6 # Init + Mech + 3 Field Groups + Proc

    def _update_status(self, step: int, msg: str):
        if self.status_callback:
            self.status_callback(f"[Step {step}/{self.total_steps}] {msg}")
        logger.info(f"[ManifestExtractor] {msg}")

    def extract(self, rules_text: str) -> SystemManifest:
        # Phase 0: Context Ingestion
        self._update_status(1, "Ingesting Rules...")
        system_prompt = SHARED_RULES_SYSTEM_PROMPT.format(rules_source=rules_text)
        
        # Build the Menu string once
        menu_text = self._build_menu()

        # Phase 1: Mechanics
        self._update_status(2, "Extracting Mechanics & Formulas...")
        mechanics = self._extract_mechanics(system_prompt)

        # Phase 2: Fields (Loop)
        all_fields: List[ExtractedField] = []
        
        # Group 1: Core Stats
        self._update_status(3, "Extracting Attributes & Resources...")
        f1 = self._extract_field_group(
            system_prompt, 
            menu_text, 
            mechanics.aliases, 
            ["attributes", "resources", "progression"]
        )
        all_fields.extend(f1)

        # Group 2: Capabilities
        self._update_status(4, "Extracting Skills & Combat...")
        f2 = self._extract_field_group(
            system_prompt, 
            menu_text, 
            mechanics.aliases, 
            ["skills", "combat", "status"]
        )
        all_fields.extend(f2)

        # Group 3: Assets & Meta
        self._update_status(5, "Extracting Inventory & Features...")
        f3 = self._extract_field_group(
            system_prompt, 
            menu_text, 
            mechanics.aliases, 
            ["inventory", "features", "meta", "identity", "narrative"]
        )
        all_fields.extend(f3)

        # Phase 3: Procedures
        self._update_status(6, "Extracting Procedures...")
        procedures = self._extract_procedures(system_prompt)

        # Assembly
        return self._assemble(mechanics, all_fields, procedures)

    def _build_menu(self) -> str:
        lines = ["### AVAILABLE PREFAB TYPES (The Menu)", "You must strictly choose from this list."]
        for pid, prefab in PREFABS.items():
            lines.append(f"- **{pid}**: {prefab.ai_hint}")
        return "\n".join(lines)

    def _extract_mechanics(self, system_prompt: str) -> MechanicsExtraction:
        try:
            return self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=[Message(role="user", content=EXTRACT_MECHANICS_PROMPT)],
                output_schema=MechanicsExtraction,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"Mechanics extraction failed: {e}")
            return MechanicsExtraction(
                dice_notation="1d20", 
                resolution_mechanic="Unknown", 
                success_condition="Unknown", 
                crit_rules="None"
            )

    def _extract_field_group(
        self, 
        system_prompt: str, 
        menu: str, 
        aliases: Dict[str, str], 
        categories: List[str]
    ) -> List[ExtractedField]:
        
        alias_str = ", ".join(aliases.keys()) if aliases else "None"
        cat_str = ", ".join(categories)
        
        prompt = EXTRACT_FIELDS_PROMPT.format(
            categories=cat_str,
            menu=menu,
            aliases=alias_str
        )

        try:
            result = self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=[Message(role="user", content=prompt)],
                output_schema=ExtractedFieldList,
                temperature=0.4
            )
            return result.fields
        except Exception as e:
            logger.warning(f"Field group {cat_str} extraction failed: {e}")
            return []

    def _extract_procedures(self, system_prompt: str) -> Dict[str, str]:
        try:
            res = self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=[Message(role="user", content=EXTRACT_PROCEDURES_PROMPT)],
                output_schema=ProceduresExtraction,
                temperature=0.5
            )
            return res.model_dump()
        except Exception as e:
            logger.warning(f"Procedure extraction failed: {e}")
            return {}

    def _assemble(
        self, 
        mech: MechanicsExtraction, 
        fields: List[ExtractedField], 
        procs: Dict[str, str]
    ) -> SystemManifest:
        
        # Deduplicate fields by path
        unique_fields = {}
        for f in fields:
            if f.path not in unique_fields:
                unique_fields[f.path] = f
        
        # Convert to FieldDef
        field_defs = []
        for f in unique_fields.values():
            field_defs.append(FieldDef(
                path=f.path,
                label=f.label,
                prefab=f.prefab,
                category=f.category,
                config=f.config,
                formula=f.formula,
                usage_hint=f.usage_hint
            ))

        # Generate ID from name
        sys_id = "custom_" + str(hash(mech.resolution_mechanic))[:8]

        return SystemManifest(
            id=sys_id,
            name="Extracted System", # Can be updated by user later
            engine=EngineConfig(
                dice=mech.dice_notation,
                mechanic=mech.resolution_mechanic,
                success=mech.success_condition,
                crit=mech.crit_rules,
                fumble=mech.fumble_rules
            ),
            procedures=procs,
            fields=field_defs,
            aliases=mech.aliases
        )
