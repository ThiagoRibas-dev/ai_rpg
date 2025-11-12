"""
Template Generator - Extracts game mechanics from rules documents.
"""

import logging
from typing import Dict, Any, List
from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.game_template import GameTemplate

logger = logging.getLogger(__name__)


RULES_ANALYSIS_PROMPT = """
You are a game system analyst. Extract structured game mechanics from rules documents.

CRITICAL: For EVERY property you define, provide a **concise, actionable description**.

**DESCRIPTION GUIDELINES:**
✅ Good: "Physical power; affects melee attacks and carrying capacity"
✅ Good: "Mental fortitude against cosmic horrors; loss causes madness"
✅ Good: "Social influence and persuasion; determines NPC reactions"

❌ Bad: "Strength" (not descriptive)
❌ Bad: "This attribute represents the character's physical capabilities..." (too verbose)

**FORMAT:** One sentence (max 15 words), explain WHAT it is and WHAT it affects.

---

OUTPUT STRUCTURE:

**ENTITY SCHEMAS** - How game entities are structured

1. **Attributes** - Core abilities (STR, DEX, INT, etc.)
   - name: Attribute name
   - abbreviation: Short code (e.g., "Str")
   - description: ONE SENTENCE (required!)
   - default: Starting value
   - range: [min, max] if applicable
   - modifier_formula: e.g., "floor((score - 10) / 2)"
   - applies_to: 3-5 examples of what it affects

2. **Resources** - Expendable pools (HP, Mana, Sanity, etc.)
   - name: Resource name
   - description: ONE SENTENCE (required!)
   - default: Starting value
   - has_max: true/false
   - regenerates: true/false
   - death_at: Value at death (if applicable)

3. **Derived Stats** - Calculated values (AC, Initiative, etc.)
   - name: Stat name
   - description: ONE SENTENCE (required!)
   - formula: How it's calculated

**SKILLS** - Learned abilities
- name, description (ONE SENTENCE), system_type (ranked/percentile/dice_pool/binary)
- linked_attribute: Which attribute it uses

**ACTION ECONOMY** - How turns work
Identify system type:
- fixed_types: Specific categories (D&D: standard/move/swift)
- action_points: Pool system (PF2e: 3 actions)
- multi_action: Penalty-based (Savage Worlds: -2 per extra)
- narrative: Fiction-first (PbtA/BitD)

**RULE SCHEMAS** - Core mechanics
- Core resolution mechanic (d20 + mods >= DC, etc.)

**CONDITIONS** - Status effects (Blinded, Stunned, etc.)

**CLASSES** - Character archetypes (if applicable)

**RACES** - Character species (if applicable)

---

EXAMPLE D&D 3.5e OUTPUT:

```json
{
  "genre": {"description": "High fantasy", "tags": ["fantasy", "d20"]},
  "tone": {"description": "Epic heroic adventure", "tags": ["heroic", "tactical"]},
  "entity_schemas": {
    "character": {
      "attributes": [
        {
          "name": "Strength",
          "abbreviation": "Str",
          "description": "Physical power; affects melee attacks and carrying capacity",
          "default": 10,
          "range": [3, 18],
          "modifier_formula": "floor((score - 10) / 2)",
          "applies_to": ["Melee attacks", "Damage", "Climb", "Jump", "Swim"]
        }
      ],
      "resources": [
        {
          "name": "HP",
          "description": "Hit points; damage capacity before unconsciousness or death",
          "base_formula": "class_hit_die + CON_modifier",
          "has_max": true,
          "regenerates": true,
          "death_at": -10
        }
      ]
    }
  },
  "skills": [
    {
      "name": "Climb",
      "description": "Scale walls, cliffs, or ropes",
      "system_type": "ranked",
      "linked_attribute": "Strength"
    }
  ],
  "action_economy": {
    "system_type": "fixed_types",
    "action_types": [
      {
        "name": "Standard Action",
        "description": "Main action on your turn",
        "quantity_per_turn": 1,
        "timing": "your_turn",
        "examples": ["Attack once", "Cast a spell"]
      }
    ]
  }
}
```

Now analyze the provided rules document:
"""


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
            
            logger.info(f"Generated template: {result.analysis_notes}")
            
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
