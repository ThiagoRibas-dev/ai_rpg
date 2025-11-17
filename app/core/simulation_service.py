# File: app/core/simulation_service.py
# --- NEW FILE ---

import logging
from app.llm.llm_connector import LLMConnector
from app.models.npc_profile import NpcProfile
from app.llm.schemas import WorldTickOutcome
from app.prompts.templates import JIT_SIMULATION_TEMPLATE

class SimulationService:
    """
    Handles the just-in-time, on-demand simulation of an NPC's off-screen
    actions when they become relevant to the current scene.
    """
    def __init__(self, llm: LLMConnector, logger: logging.Logger):
        self.llm = llm
        self.logger = logger

    def simulate_npc_downtime(
        self, npc_name: str, profile: NpcProfile, current_time: str
    ) -> WorldTickOutcome | None:
        """
        Calls the LLM to generate a summary of what an NPC has been doing
        during a period of downtime.
        """
        try:
            prompt = JIT_SIMULATION_TEMPLATE.format(
                npc_name=npc_name,
                personality=", ".join(profile.personality_traits),
                motivations=", ".join(profile.motivations),
                directive=profile.directive,
                last_updated_time=profile.last_updated_time,
                current_time=current_time,
            )
            
            self.logger.info(f"Running JIT simulation for {npc_name} from {profile.last_updated_time} to {current_time}...")
            
            outcome = self.llm.get_structured_response(
                system_prompt=prompt,
                chat_history=[],
                output_schema=WorldTickOutcome,
            )
            return outcome
        except Exception as e:
            self.logger.error(
                f"Just-In-Time simulation failed for NPC {npc_name}: {e}",
                exc_info=True,
            )
            return None
