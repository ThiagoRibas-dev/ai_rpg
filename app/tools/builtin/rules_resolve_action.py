from typing import Dict, Any

schema = {
    "name": "rules.resolve_action",
    "description": "Resolves an action based on a dynamically provided resolution policy from the LLM.",
    "parameters": {
        "type": "object",
        "properties": {
            "action_id": {
                "type": "string",
                "description": "A simple descriptive label for the action being resolved (e.g., 'Open Humming Lock')."
            },
            "actor_id": {
                "type": "string",
                "description": "The ID of the actor performing the action."
            },
            "resolution_policy": {
                "type": "object",
                "description": "The complete policy for resolving the action, defined by the LLM.",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["skill_check"],
                        "description": "The type of resolution mechanic (e.g., 'skill_check')."
                    },
                    "dc": {
                        "type": "integer",
                        "description": "The final Difficulty Class for the check, as determined by the LLM."
                    },
                    "base_formula": {
                        "type": "string",
                        "description": "The base dice roll formula (e.g., '1d20')."
                    },
                    "modifiers": {
                        "type": "array",
                        "description": "A list of all modifiers the LLM has decided to apply.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string", "description": "The reason for the modifier (e.g., 'Player's Tech Skill', 'Magic Item Bonus')."},
                                "value": {"type": "integer", "description": "The value of the modifier."}
                            },
                            "required": ["source", "value"]
                        }
                    }
                },
                "required": ["type", "dc", "base_formula"]
            }
        },
        "required": ["action_id", "actor_id", "resolution_policy"]
    }
}

def handler(action_id: str, actor_id: str, resolution_policy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the resolution policy provided by the LLM.
    """
    dc = resolution_policy.get("dc", 10)
    base_formula = resolution_policy.get("base_formula", "1d20")
    modifiers = resolution_policy.get("modifiers", [])
    
    total_modifier = sum(mod.get("value", 0) for mod in modifiers)
    
    # Construct the final formula
    if total_modifier > 0:
        final_formula = f"{base_formula}+{total_modifier}"
    elif total_modifier < 0:
        final_formula = f"{base_formula}{total_modifier}"
    else:
        final_formula = base_formula
        
    # Create a detailed explanation
    explanation = f"Action '{action_id}' for actor '{actor_id}':\n"
    explanation += f"- Resolution Type: {resolution_policy.get('type', 'unknown')}\n"
    explanation += f"- Target DC: {dc}\n"
    explanation += f"- Base Formula: {base_formula}\n"
    
    if modifiers:
        explanation += "- Modifiers:\n"
        for mod in modifiers:
            source = mod.get('source', 'Unknown')
            value = mod.get('value', 0)
            sign = "+" if value >= 0 else ""
            explanation += f"  - {source}: {sign}{value}\n"
            
    explanation += f"- Final Formula: {final_formula}"

    return {
        "dc": dc,
        "formula": final_formula,
        "explanation": explanation
    }