from app.models.ruleset import Ruleset

def build_ruleset_summary(ruleset: Ruleset) -> str:
    """
    Generate minimal Ruleset summary for system prompt.
    Refactored to match the current Ruleset -> EngineConfig schema.
    """
    if not ruleset:
        return ""
    
    e = ruleset.engine
    sections = ["# SYSTEM RULES"]
    
    # 1. Core Resolution
    sections.append(f"- **Dice**: {e.dice_notation}")
    sections.append(f"- **Resolution**: {e.roll_mechanic}")
    sections.append(f"- **Success**: {e.success_condition}")
    sections.append(f"- **Crit**: {e.crit_rules}")
    
    # 2. Procedures (Highlights)
    if ruleset.combat_procedures:
        sections.append("**Combat Modes**: " + ", ".join(ruleset.combat_procedures.keys()))
    
    if ruleset.exploration_procedures:
        sections.append("**Exploration Modes**: " + ", ".join(ruleset.exploration_procedures.keys()))

    # 3. Sheet Hints
    if ruleset.sheet_hints:
        sections.append("**Stats**: " + ", ".join(ruleset.sheet_hints[:5]))
    
    return "\n".join(sections)
