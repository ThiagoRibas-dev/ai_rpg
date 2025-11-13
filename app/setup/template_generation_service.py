import logging
import json
from typing import Dict, Any, List, Callable, Optional, cast
from pydantic import BaseModel, create_model

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.game_schemas import (
    GameTemplate, EntitySchema, RuleSchema, ActionEconomyDefinition,
    SkillDefinition, ConditionDefinition, ClassDefinition, RaceDefinition,
    SkillList, ConditionList, ClassList, RaceList
)
# Use the new instruction-based prompts
from app.prompts.templates import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    GENERATE_ENTITY_SCHEMA_INSTRUCTION,
    GENERATE_CORE_RULE_INSTRUCTION,
    GENERATE_DERIVED_RULES_INSTRUCTION,
    GENERATE_ACTION_ECONOMY_INSTRUCTION,
    GENERATE_SKILLS_INSTRUCTION,
    GENERATE_CONDITIONS_INSTRUCTION,
    GENERATE_CLASSES_INSTRUCTION,
    GENERATE_RACES_INSTRUCTION
)

logger = logging.getLogger(__name__)

class TemplateGenerationService:
    """Orchestrates the multi-step generation of a GameTemplate from rules."""

    def __init__(self, llm: LLMConnector, rules_text: str, status_callback: Optional[Callable[[str], None]] = None):
        """
        Initializes the service.
        Args:
            llm: The language model connector.
            rules_text: The raw text of the game rules.
            status_callback: An optional function to call with status updates for the GUI.
        """
        self.llm = llm
        self.rules_text = rules_text
        self.status_callback = status_callback
        
        # --- V11 REFACTOR: Create a single, static system prompt ---
        self.static_system_prompt = f"""{TEMPLATE_GENERATION_SYSTEM_PROMPT}

# GAME RULES DOCUMENT
---
{self.rules_text}
---
"""

    def _update_status(self, message: str):
        """Safely invokes the status callback if it exists."""
        if self.status_callback:
            self.status_callback(message)

    def generate_template(self) -> Dict[str, Any]:
        """
        Run the full generation pipeline and assemble the final GameTemplate.
        """
        # --- Step 1: Generate Entity Schemas (Attributes & Resources) ---
        self._update_status("Analyzing Attributes & Resources...")
        entity_schemas = self._generate_entity_schemas()
        attributes_list = entity_schemas.attributes if entity_schemas else []
        attributes_context = json.dumps([attr.model_dump() for attr in attributes_list], indent=2)
        
        # --- Step 2a: Generate Core Resolution Mechanic ---
        self._update_status("Defining Core Resolution Mechanic...")
        core_rule: Optional[RuleSchema] = self._generate_core_rule(attributes_context)
        
        # --- Step 2b: Generate Derived Rules & Mechanics ---
        self._update_status("Defining Specific Game Mechanics...")
        core_rule_context = core_rule.model_dump_json(indent=2) if core_rule else "No core rule defined."
        derived_rules: List[RuleSchema] = self._generate_derived_rules(attributes_context, core_rule_context)
        
        all_rules: List[RuleSchema] = ([core_rule] if core_rule else []) + derived_rules

        # Step 3: Generate Action Economy
        self._update_status("Designing Action Economy...")
        action_economy = self._generate_action_economy()

        # Step 4: Generate Skills
        self._update_status("Extracting Skills...")
        skills = self._generate_skills(attributes_context)
        skills_context = json.dumps([skill.model_dump() for skill in skills], indent=2)

        # Step 5: Generate Conditions
        self._update_status("Defining Conditions...")
        conditions = self._generate_conditions()

        # Step 6: Generate Classes
        self._update_status("Building Classes...")
        classes = self._generate_classes(attributes_context, skills_context)

        # Step 7: Generate Races
        self._update_status("Constructing Races...")
        races = self._generate_races(attributes_context, skills_context)

        # Final Assembly
        self._update_status("Assembling final template...")
        final_template = GameTemplate(
            genre={"name": "TBD"},
            tone={"name": "TBD"},
            entity_schemas={"character": entity_schemas},
            rule_schemas=all_rules if all_rules else [],
            action_economy=action_economy,
            skills=skills,
            conditions=conditions,
            classes=classes,
            races=races,
        )

        return final_template.model_dump(exclude_none=True)

    def _generate_entity_schemas(self) -> EntitySchema:
        """Generates entity schemas (attributes and resources)."""
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=GENERATE_ENTITY_SCHEMA_INSTRUCTION)],
            output_schema=EntitySchema
        )
        return cast(EntitySchema, result) or EntitySchema()

    def _generate_core_rule(self, attributes_context: str) -> Optional[RuleSchema]:
        """Generates the core rule, using attributes as context."""
        user_instruction = f"""{GENERATE_CORE_RULE_INSTRUCTION}

# CONTEXT: DEFINED ATTRIBUTES
---
{attributes_context}
---
"""
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=user_instruction)],
            output_schema=RuleSchema
        )
        return cast(Optional[RuleSchema], result)

    def _generate_derived_rules(self, attributes_context: str, core_rule_context: str) -> List[RuleSchema]:
        """Generates specific rules, using the core rule as a foundation."""
        user_instruction = f"""{GENERATE_DERIVED_RULES_INSTRUCTION}

# CONTEXT: DEFINED ATTRIBUTES
---
{attributes_context}
---

# CONTEXT: CORE RESOLUTION MECHANIC
---
{core_rule_context}
---
"""
        RulesWrapper = create_model("RulesWrapper", rules=(List[RuleSchema], ...), __base__=BaseModel)
        
        result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=user_instruction)],
            output_schema=RulesWrapper
        )
        casted_result = cast(RulesWrapper, result)
        return casted_result.rules if casted_result else []

    def _generate_action_economy(self) -> Optional[ActionEconomyDefinition]:
        """Generates the action economy definition."""
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=GENERATE_ACTION_ECONOMY_INSTRUCTION)],
            output_schema=ActionEconomyDefinition
        )
        return cast(Optional[ActionEconomyDefinition], result)

    def _generate_skills(self, attributes_context: str) -> List[SkillDefinition]:
        """Generates skills, ensuring they link to existing attributes."""
        user_instruction = f"""{GENERATE_SKILLS_INSTRUCTION}

# CONTEXT: DEFINED ATTRIBUTES
---
{attributes_context}
---
"""
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=user_instruction)],
            output_schema=SkillList
        )
        casted_result = cast(SkillList, result)
        return casted_result.skills if casted_result else []

    def _generate_conditions(self) -> List[ConditionDefinition]:
        """Generates conditions."""
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=GENERATE_CONDITIONS_INSTRUCTION)],
            output_schema=ConditionList
        )
        casted_result = cast(ConditionList, result)
        return casted_result.conditions if casted_result else []

    def _generate_classes(self, attributes_context: str, skills_context: str) -> List[ClassDefinition]:
        """Generates classes, using attributes and skills as context."""
        user_instruction = f"""{GENERATE_CLASSES_INSTRUCTION}

# CONTEXT: DEFINED ATTRIBUTES
---
{attributes_context}
---

# CONTEXT: DEFINED SKILLS
---
{skills_context}
---
"""
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=user_instruction)],
            output_schema=ClassList
        )
        casted_result = cast(ClassList, result)
        return casted_result.classes if casted_result else []

    def _generate_races(self, attributes_context: str, skills_context: str) -> List[RaceDefinition]:
        """Generates races, using attributes and skills as context."""
        user_instruction = f"""{GENERATE_RACES_INSTRUCTION}

# CONTEXT: DEFINED ATTRIBUTES
---
{attributes_context}
---

# CONTEXT: DEFINED SKILLS
---
{skills_context}
---
"""
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=user_instruction)],
            output_schema=RaceList
        )
        casted_result = cast(RaceList, result)
        return casted_result.races if casted_result else []
