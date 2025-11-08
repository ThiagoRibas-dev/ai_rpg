from typing import Dict, Any

def handler(
    action_id: str, actor_id: str, resolution_policy: Dict[str, Any], **context
) -> Dict[str, Any]:
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
            source = mod.get("source", "Unknown")
            value = mod.get("value", 0)
            sign = "+" if value >= 0 else ""
            explanation += f"  - {source}: {sign}{value}\n"

    explanation += f"- Final Formula: {final_formula}"

    return {"dc": dc, "formula": final_formula, "explanation": explanation}
