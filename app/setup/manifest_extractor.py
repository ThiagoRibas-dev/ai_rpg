import logging
import re
from collections.abc import Callable

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.vocabulary import CategoryName, PrefabID
from app.prefabs.manifest import (
    EngineConfig,
    FieldDef,
    RuleDef,
    SystemManifest,
    validate_manifest,
)
from app.prefabs.registry import PREFABS
from app.prompts.templates import (
    EXTRACT_FIELDS_PROMPT,
    EXTRACT_MECHANICS_PROMPT,
    EXTRACT_PROCEDURES_PROMPT,
    EXTRACT_RULES_PROMPT,
    SHARED_RULES_SYSTEM_PROMPT,
)
from app.setup.schemas import (
    ExtractedField,
    ExtractedFieldList,
    MechanicsExtraction,
    ProceduresExtraction,
    RuleListExtraction,
)

logger = logging.getLogger(__name__)

class ManifestExtractor:
    KNOWN_SYSTEM_IDS = {
        "dungeons & dragons 3.5e": "dnd_3_5e",
        "dungeons and dragons 3.5e": "dnd_3_5e",
    }

    def _slugify_system_id(self, name: str) -> str:
        slug = name.lower().strip()
        slug = slug.replace("&", "and")
        slug = re.sub(r"[^a-z0-9]+", "_", slug)
        slug = re.sub(r"_+", "_", slug).strip("_")
        return slug or "extracted_system"

    def _derive_system_id(self, system_name: str) -> str:
        key = system_name.lower().strip()
        return self.KNOWN_SYSTEM_IDS.get(key, self._slugify_system_id(system_name))

    def _normalize_aliases(self, aliases: dict[str, str], fields: list[ExtractedField]) -> dict[str, str]:
        """
        Rewrites alias formulas so compound fields are referenced via `.score`
        instead of the container path itself.
        Example: `attributes.str` -> `attributes.str.score`
        """
        compound_paths = {f.path for f in fields if f.prefab == PrefabID.VAL_COMPOUND}
        normalized: dict[str, str] = {}

        for alias_key, formula in aliases.items():
            updated = formula
            for path in compound_paths:
                # Replace bare references only, not already-dotted ones like `.score`
                pattern = rf"\b{re.escape(path)}\b(?!\.)"
                updated = re.sub(pattern, f"{path}.score", updated)
            normalized[alias_key] = updated

        return normalized

    def __init__(self, llm: LLMConnector, status_callback: Callable[[str], None] | None = None):
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
        all_fields.extend(self._extract_field_group(system_prompt, menu_text, mechanics.aliases, [CategoryName.ATTRIBUTES, CategoryName.RESOURCES, CategoryName.PROGRESSION]))

        self._update_status(4, "Extracting Capabilities...")
        all_fields.extend(self._extract_field_group(system_prompt, menu_text, mechanics.aliases, [CategoryName.SKILLS, CategoryName.COMBAT, CategoryName.STATUS]))

        self._update_status(5, "Extracting Assets...")
        all_fields.extend(
            self._extract_field_group(
                system_prompt,
                menu_text,
                mechanics.aliases,
                [
                    CategoryName.INVENTORY,
                    CategoryName.FEATURES,
                    CategoryName.META,
                    CategoryName.IDENTITY,
                    CategoryName.NARRATIVE,
                    CategoryName.CONNECTIONS,
                ],
            )
        )

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
        messages = [Message(role="user", content=EXTRACT_MECHANICS_PROMPT)]
        for attempt in range(3):
            try:
                return self.llm.get_structured_response(prompt, messages, MechanicsExtraction, 0.3)
            except Exception as e:
                logger.warning(f"Mechanics extraction failed (attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    return MechanicsExtraction(
                        system_name="Extracted System",
                        dice_notation="1d20",
                        resolution_mechanic="Unknown",
                        success_condition="Unknown",
                        crit_rules="None",
                        fumble_rules="",
                        aliases={},
                    )
                messages.append(Message(role="assistant", content="I provided an invalid JSON response."))
                messages.append(Message(role="user", content=f"Validation failed: {e}. Please fix the errors and try again. Provide ONLY valid JSON."))

    def _extract_field_group(
        self,
        prompt: str,
        menu: str,
        aliases: dict,
        cats: list[CategoryName],
    ) -> list[ExtractedField]:
        p = EXTRACT_FIELDS_PROMPT.format(
            categories=", ".join(cats),
            menu=menu,
            aliases=str(aliases),
        )
        messages = [Message(role="user", content=p)]

        for attempt in range(3):
            try:
                result = self.llm.get_structured_response(prompt, messages, ExtractedFieldList, 0.4)
                allowed = {str(c) for c in cats}
                filtered = [f for f in result.fields if str(f.category) in allowed]

                dropped = [f.path for f in result.fields if str(f.category) not in allowed]
                if dropped:
                    logger.info(f"Dropped out-of-batch fields for cats {cats}: {dropped}")

                return filtered
            except Exception as e:
                logger.warning(f"Field extraction failed for cats {cats} (attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    return []
                messages.append(Message(role="assistant", content="I provided an invalid JSON response."))
                messages.append(Message(role="user", content=f"Validation failed: {e}. Please fix the errors and try again. Provide ONLY valid JSON."))

    def _extract_procedures(self, prompt: str) -> dict[str, str]:
        messages = [Message(role="user", content=EXTRACT_PROCEDURES_PROMPT)]
        for attempt in range(3):
            try:
                return self.llm.get_structured_response(prompt, messages, ProceduresExtraction, 0.5).model_dump()
            except Exception as e:
                logger.warning(f"Procedures extraction failed (attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    return {}
                messages.append(Message(role="assistant", content="I provided an invalid JSON response."))
                messages.append(Message(role="user", content=f"Validation failed: {e}. Please fix the errors and try again. Provide ONLY valid JSON."))

    def _extract_rules(self, prompt: str) -> list[RuleDef]:
        messages = [Message(role="user", content=EXTRACT_RULES_PROMPT)]
        for attempt in range(3):
            try:
                res = self.llm.get_structured_response(prompt, messages, RuleListExtraction, 0.5)
                return [RuleDef(name=r.name, content=r.content, tags=r.tags) for r in res.rules]
            except Exception as e:
                logger.warning(f"Rule extraction failed (attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    return []
                messages.append(Message(role="assistant", content="I provided an invalid JSON response."))
                messages.append(Message(role="user", content=f"Validation failed: {e}. Please fix the errors and try again. Provide ONLY valid JSON."))

    def _assemble(self, mech, fields, procs, rules) -> SystemManifest:
        # Deduplicate by path; last one wins
        unique = {f.path: f for f in fields}
        deduped_fields = list(unique.values())

        # Normalize aliases now that we know actual field shapes
        normalized_aliases = self._normalize_aliases(mech.aliases, deduped_fields)

        defs = [
            FieldDef(
                path=f.path,
                label=f.label,
                prefab=f.prefab,
                category=f.category,
                config=f.config,
                formula=f.formula,
                usage_hint=f.usage_hint,
            )
            for f in deduped_fields
        ]

        system_name = (mech.system_name or "Extracted System").strip()
        system_id = self._derive_system_id(system_name)

        manifest = SystemManifest(
            id=system_id,
            name=system_name,
            engine=EngineConfig(
                dice=mech.dice_notation,
                mechanic=mech.resolution_mechanic,
                success=mech.success_condition,
                crit=mech.crit_rules,
                fumble=mech.fumble_rules,
            ),
            procedures=procs,
            fields=defs,
            aliases=normalized_aliases,
            rules=rules,
        )

        problems = validate_manifest(manifest)
        for problem in problems:
            logger.warning(f"Manifest validation: {problem}")

        return manifest
