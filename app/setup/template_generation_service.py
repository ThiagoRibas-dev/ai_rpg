import logging
import json
from typing import Dict, Any, List, Callable, Optional, Type, TypeVar, cast
from pydantic import BaseModel, create_model

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.game_schemas import (
    GameTemplate, EntitySchema, RuleSchema, ActionEconomyDefinition,
    ConditionDefinition, ClassDefinition, RaceDefinition,
    SkillList, ConditionList, ClassList, RaceList
)
from app.prompts.templates import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    GENERATE_ENTITY_SCHEMA_INSTRUCTION,
    GENERATE_CORE_RULE_INSTRUCTION,
    GENERATE_DERIVED_RULES_INSTRUCTION,
    GENERATE_ACTION_ECONOMY_INSTRUCTION,
    GENERATE_SKILLS_INSTRUCTION,
    GENERATE_SKILLS_INSTRUCTION_ITERATIVE,
    GENERATE_CONDITIONS_INSTRUCTION,
    GENERATE_CLASSES_INSTRUCTION,
    GENERATE_RACES_INSTRUCTION
)

logger = logging.getLogger(__name__)

# Generic Type for our Pydantic models
T = TypeVar('T', bound=BaseModel)

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

    # ==============================================================================
    # Iterative Generation Helper
    # ==============================================================================
    def _iterative_generation_loop(
        self,
        initial_instruction: str,
        iterative_instruction: str,
        output_schema: Type[T],
        list_accessor: str,
        context_key: str,
        context_data: str = "",
        max_iterations: int = 5
    ) -> List[Any]:
        """
        A generic loop to iteratively extract a list of items from the rules.

        Args:
            initial_instruction: The prompt for the first call.
            iterative_instruction: The prompt for subsequent calls.
            output_schema: The Pydantic model that wraps the list (e.g., SkillList).
            list_accessor: The attribute name of the list within the schema (e.g., "skills").
            context_key: The placeholder name for the list of found items in the prompt.
            context_data: Additional static context (like attributes).
            max_iterations: Safety break to prevent infinite loops.
        """
        all_items = []
        found_item_names = set()

        for i in range(max_iterations):
            self._update_status(f"Running {context_key} extraction pass {i + 1}...")

            # Use initial prompt on first loop, iterative on subsequent ones
            current_instruction = initial_instruction if i == 0 else iterative_instruction

            # Build the user prompt with context
            found_items_context = json.dumps([item.model_dump() for item in all_items], indent=2)
            
            user_prompt = f"""{current_instruction}
{context_data}

# CONTEXT: {context_key.upper()} ALREADY FOUND
---
{found_items_context}
---
"""
            
            # Make the LLM call
            response = self.llm.get_structured_response(
                system_prompt=self.static_system_prompt,
                chat_history=[Message(role="user", content=user_prompt)],
                output_schema=output_schema
            )

            if not response:
                break # Stop if we get no response

            new_items = getattr(response, list_accessor, [])

            # Termination condition: model returned an empty list
            if not new_items:
                self._update_status(f"No new {context_key} found. Concluding extraction.")
                break

            # Filter out duplicates before adding
            unique_new_items = []
            for item in new_items:
                item_name = getattr(item, 'name', '').lower()
                if item_name and item_name not in found_item_names:
                    unique_new_items.append(item)
                    found_item_names.add(item_name)
            
            if unique_new_items:
                all_items.extend(unique_new_items)
                self._update_status(f"Found {len(unique_new_items)} new {context_key}. Total: {len(all_items)}.")
            else:
                 # Stop if all returned items were duplicates
                self._update_status(f"No unique new {context_key} found. Concluding extraction.")
                break
        
        return all_items


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

        # ==============================================================================
        # MODIFIED: Use the iterative loop for skills
        # ==============================================================================
        self._update_status("Extracting Skills (iteratively)...")
        skills = self._iterative_generation_loop(
            initial_instruction=GENERATE_SKILLS_INSTRUCTION,
            iterative_instruction=GENERATE_SKILLS_INSTRUCTION_ITERATIVE,
            output_schema=SkillList,
            list_accessor="skills",
            context_key="Skills",
            context_data=f"# CONTEXT: DEFINED ATTRIBUTES\n---\n{attributes_context}\n---"
        )
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
