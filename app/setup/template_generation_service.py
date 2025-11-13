import logging
import json
from typing import Dict, Any, List, Callable, Optional
from pydantic import BaseModel, create_model

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.game_schemas import (
    GameTemplate, EntitySchema, RuleSchema, ActionEconomyDefinition,
    SkillDefinition, ConditionDefinition, ClassDefinition, RaceDefinition,
    SkillList, ConditionList, ClassList, RaceList
)
# We will create these new prompts in the next step
from app.prompts.templates import (
    GENERATE_ENTITY_SCHEMA_PROMPT,
    GENERATE_CORE_RULE_PROMPT,
    GENERATE_DERIVED_RULES_PROMPT,
    GENERATE_ACTION_ECONOMY_PROMPT,
    GENERATE_SKILLS_PROMPT,
    GENERATE_CONDITIONS_PROMPT,
    GENERATE_CLASSES_PROMPT,
    GENERATE_RACES_PROMPT
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
        attributes_context = json.dumps(attributes_list)
        
        # --- Step 2a: Generate Core Resolution Mechanic ---
        self._update_status("Defining Core Resolution Mechanic...")
        core_rule: Optional[RuleSchema] = self._generate_core_rule(attributes_context)
        
        # --- Step 2b: Generate Derived Rules & Mechanics ---
        self._update_status("Defining Specific Game Mechanics...")
        # Feed the core rule into the prompt for the next step!
        core_rule_context = core_rule.model_dump_json(indent=2) if core_rule else "No core rule defined."
        derived_rules: List[RuleSchema] = self._generate_derived_rules(attributes_context, core_rule_context)
        
        all_rules: List[RuleSchema] = ([core_rule] if core_rule else []) + derived_rules

        # Step 3: Generate Action Economy
        self._update_status("Designing Action Economy...")
        action_economy = self._generate_action_economy()

        # Step 4: Generate Skills
        self._update_status("Extracting Skills...")
        skills = self._generate_skills(attributes_context)
        skills_context = json.dumps([skill.model_dump() for skill in skills])

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
            system_prompt=GENERATE_ENTITY_SCHEMA_PROMPT,
            chat_history=[Message(role="user", content=self.rules_text)],
            output_schema=EntitySchema
        )
        return cast(EntitySchema, result) or EntitySchema() # Return empty object on failure

    def _generate_core_rule(self, attributes_context: str) -> Optional[RuleSchema]:
        """Generates the core rule, using attributes as context."""
        prompt = f"""
        Here are the rules:
        {self.rules_text}
        
        Here are the attributes that have already been defined for a character:
        {attributes_context}
        
        Now, define the single core rule for action resolution.
        """
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=GENERATE_CORE_RULE_PROMPT,
            chat_history=[Message(role="user", content=prompt)],
            output_schema=RuleSchema
        )
        return cast(Optional[RuleSchema], result)

    def _generate_derived_rules(self, attributes_context: str, core_rule_context: str) -> List[RuleSchema]:
        """
        Generates specific rules like AC, saves, movement, etc.,
        using the core rule as a foundation.
        """
        # This prompt is much more comprehensive, as you wanted.
        prompt = f"""
        Here are the game rules to analyze:
        {self.rules_text}
        
        We have already defined the following core character attributes:
        {attributes_context}
        
        And we have defined the FOUNDATIONAL action resolution mechanic as:
        {core_rule_context}
        
        Now, using the foundational mechanic as a pattern, extract and define the specific rules for the following concepts if they are present in the rules text:
        - Armor Class / Defense calculation
        - Saving Throws or Resistance checks
        - Initiative or turn order determination
        - Movement rules (speed, difficult terrain, etc.)
        - Rules for Cover and/or Concealment
        - Any other key combat or exploration mechanics.
        
        For each rule, provide a name, a description, and a formula if applicable.
        """
        RulesWrapper = create_model(
            "RulesWrapper",
            rules=(
                List[RuleSchema]
            ),
            __base__=BaseModel,
        )
        
        result = self.llm.get_structured_response(
            system_prompt=GENERATE_DERIVED_RULES_PROMPT,
            chat_history=[Message(role="user", content=prompt)],
            output_schema= RulesWrapper
        )
        return result.rules if result else []

    def _generate_action_economy(self) -> Optional[ActionEconomyDefinition]:
        """Generates the action economy definition."""
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=GENERATE_ACTION_ECONOMY_PROMPT,
            chat_history=[Message(role="user", content=self.rules_text)],
            output_schema=ActionEconomyDefinition
        )
        return cast(Optional[ActionEconomyDefinition], result)

    def _generate_skills(self, attributes_context: str) -> List[SkillDefinition]:
        """Generates skills, ensuring they link to existing attributes."""
        prompt = f"""
        Rules: {self.rules_text}
        Defined Attributes: {attributes_context}
        
        Extract all skills from the rules. For each skill, ensure you set 'linked_attribute'
        to one of the provided attribute names.
        """
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=GENERATE_SKILLS_PROMPT,
            chat_history=[Message(role="user", content=prompt)],
            output_schema=SkillList  # Use the wrapper model
        )
        casted_result = cast(SkillList, result)
        return casted_result.skills if casted_result else [] # Unwrap the list from the result object

    def _generate_conditions(self) -> List[ConditionDefinition]:
        """Generates conditions."""
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=GENERATE_CONDITIONS_PROMPT,
            chat_history=[Message(role="user", content=self.rules_text)],
            output_schema=ConditionList # Use the wrapper model
        )
        casted_result = cast(ConditionList, result)
        return casted_result.conditions if casted_result else [] # Unwrap the list from the result object

    def _generate_classes(self, attributes_context: str, skills_context: str) -> List[ClassDefinition]:
        """Generates classes, using attributes and skills as context."""
        prompt = f"""
        Rules: {self.rules_text}
        Defined Attributes: {attributes_context}
        Defined Skills: {skills_context}
        
        Extract all character classes from the rules.
        """
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=GENERATE_CLASSES_PROMPT,
            chat_history=[Message(role="user", content=prompt)],
            output_schema=ClassList # Use the wrapper model
        )
        casted_result = cast(ClassList, result)
        return casted_result.classes if casted_result else [] # Unwrap the list from the result object

    def _generate_races(self, attributes_context: str, skills_context: str) -> List[RaceDefinition]:
        """Generates races, using attributes and skills as context."""
        prompt = f"""
        Rules: {self.rules_text}
        Defined Attributes: {attributes_context}
        Defined Skills: {skills_context}
        
        Extract all character races/species from the rules.
        """
        from typing import cast
        result = self.llm.get_structured_response(
            system_prompt=GENERATE_RACES_PROMPT,
            chat_history=[Message(role="user", content=prompt)],
            output_schema=RaceList # Use the wrapper model
        )
        casted_result = cast(RaceList, result)
        return casted_result.races if casted_result else [] # Unwrap the list from the result object
