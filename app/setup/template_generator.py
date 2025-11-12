"""
Template Generator - Extracts game mechanics from rules documents.
"""

import logging
from typing import Dict, Any, List
from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.game_schemas import GameTemplate
from app.prompts.templates import RULES_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

class TemplateGenerator:
    """Generates game templates from rules documents using AI."""
    
    def __init__(self, llm: LLMConnector):
        self.llm = llm
    
    def generate_from_rules(self, rules_text: str) -> Dict[str, Any]:
        """
        Analyze rules document and generate a template manifest.
        
        Args:
            rules_text: Raw rules document (SRD, homebrew, etc.)
        
        Returns:
            Template manifest dict with genre, tone, entity_schemas, etc.
        """
        system_prompt = RULES_ANALYSIS_PROMPT
        user_message = f"# RULES DOCUMENT TO ANALYZE\n\n{rules_text}"
        
        try:
            result = self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=[Message(role="user", content=user_message)],
                output_schema=GameTemplate
            )
            
            if not result:
                raise ValueError("AI returned empty result")
            
            # Convert to dict for storage
            template_dict = result.model_dump()
            
            # Validate descriptions
            warnings = validate_descriptions(template_dict)
            if warnings:
                logger.warning("Template validation warnings:\n" + "\n".join(warnings))
            
            return template_dict
            
        except Exception as e:
            logger.error(f"Template generation failed: {e}", exc_info=True)
            raise


def validate_descriptions(template: dict) -> List[str]:
    """Validate that all descriptions are concise and useful."""
    warnings = []
    
    # Check attributes
    for attr in template.get("entity_schemas", {}).get("character", {}).get("attributes", []):
        desc = attr.get("description", "")
        if not desc:
            warnings.append(f"Attribute '{attr['name']}' has no description")
        elif len(desc) < 10:
            warnings.append(f"Attribute '{attr['name']}' description too short: '{desc}'")
        elif len(desc) > 100:
            warnings.append(f"Attribute '{attr['name']}' description too long ({len(desc)} chars)")
        elif desc.lower() == attr['name'].lower():
            warnings.append(f"Attribute '{attr['name']}' description is just the name")
    
    # Check resources
    for resource in template.get("entity_schemas", {}).get("character", {}).get("resources", []):
        desc = resource.get("description", "")
        if not desc or len(desc) < 10:
            warnings.append(f"Resource '{resource['name']}' needs better description")
    
    # Check skills
    for skill in template.get("skills", []):
        desc = skill.get("description", "")
        if not desc or len(desc) < 10:
            warnings.append(f"Skill '{skill['name']}' needs better description")
    
    return warnings