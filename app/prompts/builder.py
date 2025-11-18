from app.models.ruleset import Ruleset

def build_ruleset_summary(ruleset: Ruleset) -> str:
    """
    Generate minimal Ruleset summary for system prompt.
    Replaces the old build_lean_schema_reference.
    """
    if not ruleset:
        return ""
    
    sections = []
    
    # 1. Core Resolution
    sections.append(f"**Resolution**: {ruleset.resolution_mechanic}")
    
    # 2. Tactical Rules (Key mechanics)
    if ruleset.tactical_rules:
        rule_names = [r.name for r in ruleset.tactical_rules[:5]]
        sections.append(f"**Tactics**: {', '.join(rule_names)}")
    
    # 3. Compendium Highlights
    if ruleset.compendium:
        # Conditions
        if ruleset.compendium.conditions:
            cond_names = [c.name for c in ruleset.compendium.conditions[:6]]
            sections.append(f"**Conditions**: {', '.join(cond_names)}")
            
        # Skills
        if ruleset.compendium.skills:
             sections.append(f"**Skills**: {len(ruleset.compendium.skills)} available")
    
    # 4. Environment
    if ruleset.exploration_rules:
         env_names = [r.name for r in ruleset.exploration_rules[:4]]
         sections.append(f"**Environment**: {', '.join(env_names)}")
    
    return "\n".join(sections)