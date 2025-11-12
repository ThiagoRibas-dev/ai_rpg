def build_lean_schema_reference(manifest: dict) -> str:
    """Generate minimal schema reference for system prompt (~100-200 tokens)."""
    
    sections = []
    
    # 1. Attributes (just names + abbreviations)
    if manifest.get("entity_schemas", {}).get("character", {}).get("attributes"):
        attrs = manifest["entity_schemas"]["character"]["attributes"]
        attr_names = [f"{a['name']} ({a.get('abbreviation', '')})" for a in attrs]
        sections.append(f"**Attributes**: {', '.join(attr_names)}")
    
    # 2. Resources (just names + death condition if any)
    if manifest.get("entity_schemas", {}).get("character", {}).get("resources"):
        resources = manifest["entity_schemas"]["character"]["resources"]
        resource_list = []
        for r in resources:
            death_note = f" (death at {r['death_at']})" if r.get('death_at') is not None else ""
            resource_list.append(f"{r['name']}{death_note}")
        sections.append(f"**Resources**: {', '.join(resource_list)}")
    
    # 3. Skills (count + system type)
    if manifest.get("skills"):
        skill_count = len(manifest["skills"])
        skill_system = manifest["skills"][0].get("system_type", "ranked")
        
        system_hint = {
            "ranked": "d20 + ranks + modifier",
            "percentile": "d100 ≤ skill%",
            "dice_pool": "roll skill dice",
            "binary": "have it or don't"
        }.get(skill_system, "")
        
        sections.append(f"**Skills**: {skill_count} {skill_system} skills ({system_hint})")
    
    # 4. Action Economy (ultra-compressed)
    if manifest.get("action_economy"):
        ae = manifest["action_economy"]
        
        if ae.get("system_type") == "fixed_types":
            action_summary = ", ".join([
                f"{at['name']} ({at['quantity_per_turn']})"
                for at in ae.get("action_types", [])
                if at.get("timing") == "your_turn"
            ][:5])  # Limit to 5 action types
            sections.append(f"**Actions/Turn**: {action_summary}")
        
        elif ae.get("system_type") == "action_points":
            sections.append(f"**Actions/Turn**: {ae.get('points_per_turn', 3)} action points")
        
        elif ae.get("system_type") == "multi_action":
            sections.append(f"**Actions/Turn**: Unlimited ({ae.get('multi_action_penalty', '')})")
        
        elif ae.get("system_type") == "narrative":
            sections.append("**Actions/Turn**: Narrative (fiction-driven)")
    
    # 5. Core Mechanic (one line)
    if manifest.get("rule_schemas"):
        core_rule = next((r for r in manifest["rule_schemas"] if r.get("type") == "resolution"), None)
        if core_rule:
            sections.append(f"**Core Mechanic**: {core_rule.get('formula', 'See rules')}")
    
    # 6. Classes/Races (just names if applicable)
    if manifest.get("classes"):
        class_names = [c["name"] for c in manifest["classes"][:8]]
        more = f" (+{len(manifest['classes']) - 8} more)" if len(manifest["classes"]) > 8 else ""
        sections.append(f"**Classes**: {', '.join(class_names)}{more}")
    
    if manifest.get("races"):
        race_names = [r["name"] for r in manifest["races"][:8]]
        more = f" (+{len(manifest['races']) - 8} more)" if len(manifest["races"]) > 8 else ""
        sections.append(f"**Races**: {', '.join(race_names)}{more}")
    
    return "\n".join(sections)