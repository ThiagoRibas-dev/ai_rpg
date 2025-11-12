"""
Schema query tool - look up game mechanics on-demand.
"""

def handler(query_type: str, specific_name: str | None = None, **context) -> dict:
    """Query game schema for detailed mechanics."""
    from app.core.setup_manifest import SetupManifest
    
    session_id = context.get("session_id")
    db = context.get("db_manager")
    
    if not session_id or not db:
        return {"error": "Missing session context"}
    
    manifest_mgr = SetupManifest(db)
    manifest = manifest_mgr.get_manifest(session_id)
    
    if query_type == "attribute":
        attrs = manifest.get("entity_schemas", {}).get("character", {}).get("attributes", [])
        
        if specific_name:
            attr = next((a for a in attrs if a["name"].lower() == specific_name.lower()), None)
            if not attr:
                return {"error": f"Attribute '{specific_name}' not found"}
            return {
                "name": attr["name"],
                "description": attr["description"],
                "range": attr.get("range"),
                "modifier_formula": attr.get("modifier_formula"),
                "applies_to": attr.get("applies_to", [])
            }
        else:
            return {
                "attributes": [
                    {
                        "name": a["name"],
                        "description": a["description"],
                        "applies_to": a.get("applies_to", [])[:3]
                    }
                    for a in attrs
                ]
            }
    
    elif query_type == "skill":
        skills = manifest.get("skills", [])
        
        if specific_name:
            skill = next((s for s in skills if s["name"].lower() == specific_name.lower()), None)
            if not skill:
                return {"error": f"Skill '{specific_name}' not found"}
            return {
                "name": skill["name"],
                "description": skill["description"],
                "system_type": skill.get("system_type"),
                "linked_attribute": skill.get("linked_attribute")
            }
        else:
            return {
                "skill_count": len(skills),
                "system_type": skills[0].get("system_type") if skills else None,
                "skills": [s["name"] for s in skills]
            }
    
    elif query_type == "action_economy":
        ae = manifest.get("action_economy", {})
        
        if ae.get("system_type") == "fixed_types":
            return {
                "system_type": "fixed_types",
                "action_types": [
                    {
                        "name": at["name"],
                        "quantity_per_turn": at["quantity_per_turn"],
                        "timing": at.get("timing"),
                        "examples": at.get("examples", [])[:5]
                    }
                    for at in ae.get("action_types", [])
                ]
            }
        else:
            return ae
    
    elif query_type == "class":
        classes = manifest.get("classes", [])
        
        if specific_name:
            cls = next((c for c in classes if c["name"].lower() == specific_name.lower()), None)
            if not cls:
                return {"error": f"Class '{specific_name}' not found"}
            return cls
        else:
            return {
                "classes": [
                    {"name": c["name"], "description": c.get("description", "")}
                    for c in classes
                ]
            }
    
    elif query_type == "race":
        races = manifest.get("races", [])
        
        if specific_name:
            race = next((r for r in races if r["name"].lower() == specific_name.lower()), None)
            if not race:
                return {"error": f"Race '{specific_name}' not found"}
            return race
        else:
            return {
                "races": [
                    {"name": r["name"], "description": r.get("description", "")}
                    for r in races
                ]
            }
    
    elif query_type == "all":
        return {
            "attributes": manifest.get("entity_schemas", {}).get("character", {}).get("attributes", []),
            "resources": manifest.get("entity_schemas", {}).get("character", {}).get("resources", []),
            "skills_count": len(manifest.get("skills", [])),
            "action_economy": manifest.get("action_economy", {}),
            "classes_count": len(manifest.get("classes", [])),
            "races_count": len(manifest.get("races", []))
        }
    
    return {"error": f"Unknown query_type: {query_type}"}
