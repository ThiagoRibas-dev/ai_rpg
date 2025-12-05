import logging
import json
from typing import Dict, Any, List, Type
from pydantic import BaseModel, create_model

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.sheet_schema import (
    CharacterSheetSpec,
    FieldDisplay,
    SheetField,
    SheetCategory,
)
from app.setup.blueprints import SheetBlueprint
from app.prompts.architect_templates import (
    ARCHITECT_SYSTEM_PROMPT,
    ARCHITECT_USER_TEMPLATE,
    POPULATE_SYSTEM_PROMPT,
    POPULATE_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)


class SheetGenerator:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def generate_structure(
        self, rules_text: str, character_concept: str
    ) -> CharacterSheetSpec:
        """Pass 1: Architecting the Sheet (Blueprint Mode)."""
        logger.info("Architecting sheet structure...")
        user_prompt = ARCHITECT_USER_TEMPLATE.format(
            rules_text=rules_text or "Generic RPG Rules",
            character_concept=character_concept,
        )

        try:
            blueprint = self.llm.get_structured_response(
                system_prompt=ARCHITECT_SYSTEM_PROMPT,
                chat_history=[Message(role="user", content=user_prompt)],
                output_schema=SheetBlueprint,
                temperature=0.7,
            )
            return self._hydrate_blueprint(blueprint)
        except Exception as e:
            logger.error(f"Structure generation failed: {e}", exc_info=True)
            return CharacterSheetSpec()

    def populate_sheet(
        self, spec: CharacterSheetSpec, character_concept: str
    ) -> Dict[str, Any]:
        """Pass 2: Populating Data with Strict Dynamic Schema."""
        logger.info("Populating sheet data...")

        # 1. Build a Strict Pydantic Model on the fly based on the Spec
        # This replaces Dict[str, Any] with a rigid structure.
        DynamicSchema = self._build_dynamic_schema(spec)

        # 2. Generate Prompt
        # We still provide the skeleton in text to help the "reasoning" part of the LLM,
        # but the enforcement happens via output_schema.
        skeleton = self._generate_data_skeleton(spec)
        schema_json = json.dumps(skeleton, indent=2)

        user_prompt = POPULATE_USER_TEMPLATE.format(
            schema_json=schema_json, character_concept=character_concept
        )

        try:
            # 3. Call LLM with the strict model
            result_model = self.llm.get_structured_response(
                system_prompt=POPULATE_SYSTEM_PROMPT,
                chat_history=[Message(role="user", content=user_prompt)],
                output_schema=DynamicSchema,
                temperature=0.7,
            )

            # 4. Convert back to Dict
            return result_model.model_dump()

        except Exception as e:
            logger.error(f"Data population failed: {e}")
            # Fallback: return empty dict (renderer handles missing data gracefully now)
            return {}

    def _build_dynamic_schema(self, spec: CharacterSheetSpec) -> Type[BaseModel]:
        """
        Dynamically constructs a Pydantic Model class that mirrors the Spec.
        This forces the LLM to output ONLY keys defined in the spec.
        """
        category_fields = {}
        spec_dict = spec.model_dump()

        for cat_key, cat_data in spec_dict.items():
            fields = cat_data.get("fields", {})
            if not fields:
                continue

            # Build the model for this Category (e.g. AttributesModel)
            field_definitions = {}

            for f_key, f_def in fields.items():
                container = f_def.get("container_type", "atom")
                dtype = f_def.get("data_type", "string")

                # Determine Python Type
                if container == "atom":
                    py_type = int if dtype == "number" else str
                    # Use (type, default) syntax for create_model
                    field_definitions[f_key] = (py_type, ...)

                elif container == "molecule":
                    # Build nested model for Molecule (e.g. Current/Max)
                    comps = f_def.get("components", {})
                    mol_fields = {}
                    for c_key in comps.keys():
                        mol_fields[c_key] = (int, ...)  # Usually numbers for pools

                    MoleculeModel = create_model(f"{f_key}_Molecule", **mol_fields)
                    field_definitions[f_key] = (MoleculeModel, ...)

                elif container == "list":
                    # Build nested model for Row Item
                    item_schema = f_def.get("item_schema", {})
                    row_fields = {}
                    for col_key, col_def in item_schema.items():
                        c_dtype = col_def.get("data_type", "string")
                        py_type = int if c_dtype == "number" else str
                        row_fields[col_key] = (py_type, ...)

                    RowModel = create_model(f"{f_key}_Item", **row_fields)
                    field_definitions[f_key] = (List[RowModel], ...)

            # Create Category Model
            CatModel = create_model(f"{cat_key.title()}Model", **field_definitions)

            # Add to Root fields
            category_fields[cat_key] = (CatModel, ...)

        # Create Root Model
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
        """Expands the flat blueprint into the full UCST Spec."""
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
        # ... (Same as previous step, kept for completeness of file) ...
        if bp_field.concept in ["stat", "text", "die", "toggle"]:
            widget_map = {
                "stat": "number",
                "text": "text",
                "die": "die",
                "toggle": "toggle",
            }
            data_type = "number" if bp_field.concept == "stat" else "string"
            default_val = bp_field.default_val
            if (
                bp_field.concept == "stat"
                and isinstance(default_val, str)
                and default_val.isdigit()
            ):
                default_val = int(default_val)

            return SheetField(
                key=bp_field.key,
                container_type="atom",
                data_type=data_type,
                default=default_val,
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
                default = 1 if dtype == "number" else ""
                item_schema[col] = SheetField(
                    key=col,
                    container_type="atom",
                    data_type=dtype,
                    default=default,
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
