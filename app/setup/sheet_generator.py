import json
import logging
from typing import Any, Dict, List, Type, Tuple

from pydantic import BaseModel, create_model

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.sheet_schema import (
    CharacterSheetSpec,
    FieldDisplay,
    SheetCategory,
    SheetField,
)
from app.models.vocabulary import GameVocabulary
from app.setup.schema_builder import SchemaBuilder
from app.prompts.architect_templates import (
    ARCHITECT_INSTRUCTION,
    ARCHITECT_USER_TEMPLATE,
    CHAR_ANALYSIS_INSTRUCTION,
    CHAR_ANALYSIS_USER_TEMPLATE,
    POPULATE_INSTRUCTION,
    POPULATE_WITH_ANALYSIS_TEMPLATE,
    SHEET_GENERATOR_SYSTEM_PROMPT,
)
from app.setup.blueprints import SheetBlueprint

logger = logging.getLogger(__name__)


class SheetGenerator:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    # -------------------------------------------------------------------------
    # STRATEGY 1: LEGACY / ARCHITECT (No Vocabulary)
    # -------------------------------------------------------------------------
    def generate_structure(
        self, rules_text: str, character_concept: str
    ) -> CharacterSheetSpec:
        """Pass 1: Architecting the Sheet (Blueprint Mode)."""
        logger.info("Architecting sheet structure (Legacy Mode)...")

        user_prompt = ARCHITECT_USER_TEMPLATE.format(
            rules_text=rules_text or "Generic RPG Rules",
            character_concept=character_concept,
            instruction=ARCHITECT_INSTRUCTION,
        )

        try:
            blueprint = self.llm.get_structured_response(
                system_prompt=SHEET_GENERATOR_SYSTEM_PROMPT,
                chat_history=[Message(role="user", content=user_prompt)],
                output_schema=SheetBlueprint,
                temperature=0.5,
            )
            return self._hydrate_blueprint(blueprint)
        except Exception as e:
            logger.error(f"Structure generation failed: {e}", exc_info=True)
            return CharacterSheetSpec()

    # -------------------------------------------------------------------------
    # STRATEGY 2: VOCABULARY-AWARE (Preferred)
    # -------------------------------------------------------------------------
    def generate_from_vocabulary(
        self, vocabulary: GameVocabulary, character_concept: str, rules_text: str = ""
    ) -> Tuple[CharacterSheetSpec, Dict[str, Any]]:
        """
        Skip the 'Architect' step. Use the Vocabulary to build the spec,
        then ask LLM to fill data for that specific schema.

        Returns: (Spec, Values)
        """
        logger.info("Generating sheet from Vocabulary...")

        # 1. Build Spec & Schema from Vocab
        builder = SchemaBuilder(vocabulary)
        spec = builder.build_sheet_spec()

        # Get the 'Simplified' model (e.g. pools are just ints) for the LLM to fill
        CreationModel = builder.build_creation_prompt_model()
        hints = builder.get_creation_prompt_hints()

        # 2. Build Prompt
        prompt = f"""
### TASK: CREATE CHARACTER DATA
You are populating a character sheet for the system: {vocabulary.system_name}.

**Rules Context:**
{rules_text[:3000]}

**Character Concept:**
{character_concept}

**Field Constraints & Types:**
{hints}

**Instructions:**
- Fill in values that fit the concept and rules.
- Respect the type hints (e.g., if range 1-20, don't put 25).
- For Lists, provide 3-5 items.
"""

        # 3. Call LLM
        try:
            simplified_data = self.llm.get_structured_response(
                system_prompt="You are an expert TTRPG character creator.",
                chat_history=[Message(role="user", content=prompt)],
                output_schema=CreationModel,
                temperature=0.5,
            )

            # 4. Expand to Full Data (e.g. int -> {current, max})
            full_values = builder.convert_simplified_to_full(
                simplified_data.model_dump()
            )

            return spec, full_values

        except Exception as e:
            logger.error(f"Vocab-based generation failed: {e}", exc_info=True)
            # Return empty spec/values on failure so setup doesn't crash
            return spec, {}

    # -------------------------------------------------------------------------
    # DATA POPULATION (Legacy/Hybrid)
    # -------------------------------------------------------------------------
    def populate_sheet(
        self, spec: CharacterSheetSpec, character_concept: str, rules_text: str = ""
    ) -> Dict[str, Any]:
        """
        Pass 2: Populating Data with Two-Step Analysis (Used by Legacy Strategy 1).
        """
        logger.info("Populating sheet data...")

        # 1. Prepare Schema Hint
        skeleton = self._generate_data_skeleton(spec)
        schema_json = json.dumps(skeleton, indent=2)

        # --- Sub-Step A: Analysis ---
        logger.info(" > Step A: Analyzing character details...")
        safe_rules = rules_text[:4000] if rules_text else "Generic RPG"
        analysis_prompt = CHAR_ANALYSIS_USER_TEMPLATE.format(
            rules_text=safe_rules,
            sheet_structure=schema_json,
            character_concept=character_concept,
            instruction=CHAR_ANALYSIS_INSTRUCTION,
        )

        try:
            analysis_stream = self.llm.get_streaming_response(
                system_prompt=SHEET_GENERATOR_SYSTEM_PROMPT,
                chat_history=[Message(role="user", content=analysis_prompt)],
            )
            analysis_text = "".join(analysis_stream)
        except Exception as e:
            logger.error(f"Character analysis failed: {e}")
            analysis_text = character_concept

        # --- Sub-Step B: Schema Mapping ---
        logger.info(" > Step B: Mapping to schema...")
        DynamicSchema = self._build_dynamic_schema(spec)
        user_prompt = POPULATE_WITH_ANALYSIS_TEMPLATE.format(
            analysis_text=analysis_text,
            schema_json=schema_json,
            instruction=POPULATE_INSTRUCTION,
        )

        try:
            result_model = self.llm.get_structured_response(
                system_prompt=SHEET_GENERATOR_SYSTEM_PROMPT,
                chat_history=[Message(role="user", content=user_prompt)],
                output_schema=DynamicSchema,
                temperature=0.5,
            )
            return result_model.model_dump()
        except Exception as e:
            logger.error(f"Data population failed: {e}")
            return {}

    def _build_dynamic_schema(self, spec: CharacterSheetSpec) -> Type[BaseModel]:
        """Dynamically constructs a Pydantic Model class that mirrors the Spec."""
        category_fields = {}
        spec_dict = spec.model_dump()

        for cat_key, cat_data in spec_dict.items():
            fields = cat_data.get("fields", {})
            if not fields:
                continue

            field_definitions = {}
            for f_key, f_def in fields.items():
                container = f_def.get("container_type", "atom")
                dtype = f_def.get("data_type", "string")

                if container == "atom":
                    py_type = int if dtype == "number" else str
                    field_definitions[f_key] = (py_type, ...)

                elif container == "molecule":
                    comps = f_def.get("components", {})
                    mol_fields = {}
                    for c_key in comps.keys():
                        mol_fields[c_key] = (int, ...)
                    MoleculeModel = create_model(f"{f_key}_Molecule", **mol_fields)
                    field_definitions[f_key] = (MoleculeModel, ...)

                elif container == "list":
                    item_schema = f_def.get("item_schema", {})
                    row_fields = {}
                    for col_key, col_def in item_schema.items():
                        c_dtype = col_def.get("data_type", "string")
                        py_type = int if c_dtype == "number" else str
                        row_fields[col_key] = (py_type, ...)
                    RowModel = create_model(f"{f_key}_Item", **row_fields)
                    field_definitions[f_key] = (List[RowModel], ...)

            CatModel = create_model(f"{cat_key.title()}Model", **field_definitions)
            category_fields[cat_key] = (CatModel, ...)

        RootModel = create_model("DynamicCharacterSheet", **category_fields)
        return RootModel

    def _generate_data_skeleton(self, spec: CharacterSheetSpec) -> Dict[str, Any]:
        """Visual hint for the prompt."""
        skeleton = {}
        spec_dict = spec.model_dump()
        for cat_key, cat_data in spec_dict.items():
            fields = cat_data.get("fields", {})
            if not fields:
                continue
            skeleton[cat_key] = {}
            for field_key, field_def in fields.items():
                ctype = field_def.get("container_type", "atom")
                if ctype == "atom":
                    skeleton[cat_key][field_key] = 0
                elif ctype == "molecule":
                    skeleton[cat_key][field_key] = {"current": 0, "max": 0}
                elif ctype == "list":
                    skeleton[cat_key][field_key] = []
        return skeleton

    def _hydrate_blueprint(self, bp: SheetBlueprint) -> CharacterSheetSpec:
        """Expands the flat blueprint into the full UCST Spec (Legacy)."""
        spec = CharacterSheetSpec()
        for cat_key in spec.model_fields.keys():
            bp_cat = getattr(bp, cat_key, None)
            if not bp_cat or not bp_cat.fields:
                continue
            ucst_cat = SheetCategory()
            for field in bp_cat.fields:
                ucst_field = self._create_field_from_concept(field)
                ucst_cat.fields[field.key] = ucst_field
            setattr(spec, cat_key, ucst_cat)
        return spec

    def _create_field_from_concept(self, bp_field: Any) -> Any:
        # Legacy mapper
        if bp_field.concept in ["stat", "text", "die", "toggle"]:
            widget_map = {
                "stat": "number",
                "text": "text",
                "die": "die",
                "toggle": "toggle",
            }
            data_type = "number" if bp_field.concept == "stat" else "string"
            return SheetField(
                key=bp_field.key,
                container_type="atom",
                data_type=data_type,
                default=bp_field.default_val,
                display=FieldDisplay(
                    widget=widget_map[bp_field.concept], label=bp_field.label
                ),
            )
        elif bp_field.concept == "pool":
            max_val = int(bp_field.max_val) if bp_field.max_val else 10
            return SheetField(
                key=bp_field.key,
                container_type="molecule",
                display=FieldDisplay(widget="pool", label=bp_field.label),
                components={
                    "current": SheetField(
                        key="current",
                        container_type="atom",
                        data_type="number",
                        default=max_val,
                        display=FieldDisplay(label="Cur", widget="number"),
                    ),
                    "max": SheetField(
                        key="max",
                        container_type="atom",
                        data_type="number",
                        default=max_val,
                        display=FieldDisplay(label="Max", widget="number"),
                    ),
                },
            )
        elif bp_field.concept == "list":
            item_schema = {}
            columns = bp_field.list_columns or ["name", "description"]
            for col in columns:
                dtype = (
                    "number" if col in ["qty", "weight", "cost", "value"] else "string"
                )
                widget = "number" if dtype == "number" else "text"
                item_schema[col] = SheetField(
                    key=col,
                    container_type="atom",
                    data_type=dtype,
                    default=1 if dtype == "number" else "",
                    display=FieldDisplay(label=col.title(), widget=widget),
                )
            return SheetField(
                key=bp_field.key,
                container_type="list",
                display=FieldDisplay(widget="repeater", label=bp_field.label),
                item_schema=item_schema,
            )
        return SheetField(
            key=bp_field.key,
            container_type="atom",
            display=FieldDisplay(label=bp_field.label, widget="text"),
        )
