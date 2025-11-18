import logging
from typing import Any, List, Callable, Optional, Type, TypeVar, Tuple
from pydantic import BaseModel, create_model

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
# Import new models
from app.models.ruleset import (
    Ruleset, Compendium, RuleEntry
)
from app.models.stat_block import (
    StatBlockTemplate, AbilityDef, VitalDef, TrackDef, SlotDef
)
# Import new prompts
from app.prompts.templates import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    ANALYZE_RULESET_INSTRUCTION,
    ANALYZE_STATBLOCK_INSTRUCTION,
    GENERATE_CORE_RESOLUTION_INSTRUCTION,
    GENERATE_TACTICAL_RULES_INSTRUCTION,
    GENERATE_COMPENDIUM_INSTRUCTION,
    GENERATE_ABILITIES_INSTRUCTION,
    GENERATE_VITALS_INSTRUCTION,
    GENERATE_TRACKS_SLOTS_INSTRUCTION
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class TemplateGenerationService:
    """
    Service for generating game templates from raw text using an LLM.
    Now supports the v13 Ruleset + StatBlock architecture.
    """

    def __init__(self, llm_connector: LLMConnector, rules_text: str, status_callback: Optional[Callable[[str], None]] = None):
        self.llm = llm_connector
        self.rules_text = rules_text
        self.status_callback = status_callback
        
        # Pre-compute the static system prompt with the rules text
        self.static_system_prompt = f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\n\n# GAME RULES TEXT\n{self.rules_text}"

    def _update_status(self, message: str):
        """Helper to send status updates to the UI."""
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[TemplateGeneration] {message}")

    def _iterative_generation_loop(
        self, 
        current_instruction: str, 
        output_schema: Type[T], 
        list_accessor: str,
        context_key: str,
        context_data: str
    ) -> List[Any]:
        """
        Generic helper for the "generate until done" pattern.
        (Kept for potential future use, though v13 uses single-pass lists more often)
        """
        all_items = []
        # Implementation omitted for brevity as v13 uses single-pass for now
        return all_items

    def _analyze_text(self, instruction: str) -> str:
        """
        Performs a raw text analysis step (Thinking Phase).
        Returns the AI's analysis string to be used as context.
        """
        # We use a simple non-structured call here to let the LLM explain itself freely
        response_generator = self.llm.get_streaming_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=instruction)]
        )
        
        # Consume generator to get full text
        full_text = "".join([chunk for chunk in response_generator])
        return full_text


    def generate_template(self) -> Tuple[Ruleset, StatBlockTemplate]:
        """
        Run the full generation pipeline and assemble the Ruleset and StatBlockTemplate.
        Returns Pydantic models.
        """
        
        # ==========================================
        # PHASE 1: RULESET (The Physics)
        # ==========================================
        
        # 0. Analyze Phase 1
        self._update_status("Analyzing Global Rules...")
        ruleset_analysis = self._analyze_text(ANALYZE_RULESET_INSTRUCTION)
        logger.debug(f"Ruleset Analysis:\n{ruleset_analysis}")
        
        # Create a context block for the extraction steps
        ruleset_analysis_context = f"*** ANALYSIS OF RULES ***\n{ruleset_analysis}\n\nUse the analysis above to ensure accuracy."

        # 1. Core Mechanics
        self._update_status("Defining Core Resolution Mechanics...")
        ruleset_base = self._generate_resolution(ruleset_analysis_context)
        
        # 2. Tactical Rules
        self._update_status("Extracting Tactical Rules...")
        # Define wrapper for list extraction
        RuleList = create_model("RuleList", rules=(List[RuleEntry], ...), __base__=BaseModel)
        tactical_result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=f"{ruleset_analysis_context}\n\n{GENERATE_TACTICAL_RULES_INSTRUCTION}")],
            output_schema=RuleList
        )
        tactical_rules = getattr(tactical_result, "rules", [])

        # 3. Compendium (Skills, Conditions)
        self._update_status("Building Compendium (Skills & Conditions)...")
        compendium_result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=f"{ruleset_analysis_context}\n\n{GENERATE_COMPENDIUM_INSTRUCTION}")],
            output_schema=Compendium
        )
        compendium = compendium_result if compendium_result else Compendium()
        
        # Assemble Ruleset
        ruleset = Ruleset(
            resolution_mechanic=ruleset_base.resolution_mechanic,
            tactical_rules=tactical_rules,
            compendium=compendium
        )
        
        ruleset_context = ruleset.model_dump_json(indent=2)

        # ==========================================
        # PHASE 2: STATBLOCK (The Character Sheet)
        # ==========================================
        
        # 0. Analyze Phase 2
        self._update_status("Analyzing Character Structure...")
        statblock_analysis = self._analyze_text(ANALYZE_STATBLOCK_INSTRUCTION)
        logger.debug(f"StatBlock Analysis:\n{statblock_analysis}")

        # Create context block
        statblock_analysis_context = f"*** ANALYSIS OF CHARACTER SHEET ***\n{statblock_analysis}\n\nUse the analysis above. Do not include mechanics noted as 'absent'."

        # 4. Abilities
        self._update_status("Structuring Character Abilities...")
        # Context: Ruleset implies what stats are needed
        AbilityList = create_model("AbilityList", abilities=(List[AbilityDef], ...), __base__=BaseModel)
        
        abilities_result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=f"{statblock_analysis_context}\n\n{GENERATE_ABILITIES_INSTRUCTION}\n\n# CONTEXT: RULESET\n{ruleset_context}")],
            output_schema=AbilityList
        )
        abilities = getattr(abilities_result, "abilities", [])
        
        # 5. Vitals
        self._update_status("Structuring Vitals (HP/Mana)...")
        VitalList = create_model("VitalList", vitals=(List[VitalDef], ...), __base__=BaseModel)
        vitals_result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=f"{statblock_analysis_context}\n\n{GENERATE_VITALS_INSTRUCTION}\n\n# CONTEXT: RULESET\n{ruleset_context}")],
            output_schema=VitalList
        )
        vitals = getattr(vitals_result, "vitals", [])

        # 6. Tracks & Slots
        self._update_status("Defining Tracks and Slots...")
        class TrackSlotWrapper(BaseModel):
            tracks: List[TrackDef]
            slots: List[SlotDef]
            
        tracks_slots_result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=f"{statblock_analysis_context}\n\n{GENERATE_TRACKS_SLOTS_INSTRUCTION}")],
            output_schema=TrackSlotWrapper
        )
        tracks = getattr(tracks_slots_result, "tracks", [])
        slots = getattr(tracks_slots_result, "slots", [])

        # 7. Derived Stats (Automated for now)
        # We assume derived stats are often implied by Vitals (AC, etc). 
        # For this pass, we'll skip explicit extraction or infer it later.
        derived = []

        # --- Final Assembly ---
        self._update_status("Assembling final template...")
        
        stat_template = StatBlockTemplate(
            template_name="Player Character",
            abilities=abilities,
            vitals=vitals,
            tracks=tracks,
            slots=slots,
            derived_stats=derived
        )

        return ruleset, stat_template

    def _generate_resolution(self, analysis_context: str) -> Ruleset:
        """
        Generates the shell of the ruleset with just resolution mechanics.
        We use the Ruleset model but only require partial fields, 
        so we create a temporary subset model to help the LLM.
        """
        class ResolutionShell(BaseModel):
            resolution_mechanic: str
            
        result = self.llm.get_structured_response(
            system_prompt=self.static_system_prompt,
            chat_history=[Message(role="user", content=f"{analysis_context}\n\n{GENERATE_CORE_RESOLUTION_INSTRUCTION}")],
            output_schema=ResolutionShell
        )
        
        # Return a partial Ruleset
        return Ruleset(resolution_mechanic=result.resolution_mechanic) if result else Ruleset(resolution_mechanic="Unknown")
