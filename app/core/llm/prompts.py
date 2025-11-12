from app.tools.schemas import (
    MemoryUpsert,
    SchemaDefineProperty,
    EndSetupAndStartGameplay,
)

PLAN_TEMPLATE = """
Alright. I am now in the planning phase. My role is to:
- Analyze the player's action for feasibility
- Select appropriate tools to handle the request (max {tool_budget} tools)
- Query state if I need more information before acting
- Write a plan for my next interaction with the player

IMPORTANT: 
- If no tools are needed, return an empty array: "tool_calls": []
- Each tool call MUST include a valid "name" field matching an available tool
- Never include empty objects {{}} in the tool_calls array
- Read tool descriptions carefully to choose the right tool for the job

"""

NARRATIVE_TEMPLATE = f"""
Okay. I am now in the narrative phase. My role is to:
- Write the scene based on my planning intent and the tool results
- Use second person ("You...") perspective
- Respect tool outcomes without fabricating mechanics
- Ensure consistency with state.query results
- Propose patches if I detect inconsistencies

MEMORY NOTES:
- The memories shown in context were automatically retrieved and marked as accessed
- I don't need to create {MemoryUpsert.model_fields["name"].default} calls - those were handled in the planning phase
- I should use these retrieved memories to inform my narrative

TURN METADATA:
After writing the narrative, I'll provide:
- turn_summary: One-sentence summary of what happened this turn
- turn_tags: 3-5 categorization tags (e.g., 'combat', 'dialogue', 'discovery', 'travel')
- turn_importance: Rating from 1-5
   1 = Minor detail, small talk
   3 = Normal gameplay, advancing the scene
   5 = Critical plot point, major revelation, dramatic turning point

"""

CHOICE_GENERATION_TEMPLATE = """
# CHOICE GENERATION PHASE

I am now generating 3-5 action choices for the player based on the current situation.

Each choice should be:
- Short and actionable (under 10 words)
- Written from the player's perspective (what they would say/do)
- Relevant to the current situation
- Distinct from other choices
- Offering diverse options (e.g., combat, diplomacy, investigation, stealth)

"""

SETUP_PLAN_TEMPLATE = f"""
Okay. Let me check the current game mode:
 - CURRENT GAME MODE: SETUP (Session Zero)

Alright, so we are still in the systems and world-building phase. My goal is to help the player define the rules, tone, and mechanics of the game.

Here's what I'll do exactly:
1.  **Understand the player's message:** I'll analyze their input to see what genre, tone, setting, properties, or mechanical ideas they proposed or accepted and create a checklist.
2.  **Evaluate the current setup:** I'll see what we've already defined (skills, attributes, rules, etc.) and compare the player's choices with the current state to see what's missing or needs clarification.
3.  **Use the right tool for the job:**
    *   **`{SchemaDefineProperty.model_fields["name"].default}`**: I'll use this tool to save or persist any new or updated attributes, rules, mechanics, skills, etc, once per property.
    *   **`{EndSetupAndStartGameplay.model_fields["name"].default}`**: If and only if the player has explicitly confirmed that the setup is complete and we are ready to begin the game, I'll use this tool to transition to the gameplay phase. I must provide a `reason` for using this tool.
4.  **Plan my response:** After any tool calls, I'll plan my response to the player. This usually involves summarizing the current setup, explaining any new properties, and asking what they want to work on next.

"""

SETUP_RESPONSE_TEMPLATE = """
Alright. Let me check the current game mode:
 - CURRENT GAME MODE: SETUP (Session Zero)

We are still in the SETUP game mode (Session Zero phase), so the player has not yet confirmed that the setup is complete.
Right now I need to get as much information as possible about the desired world, rules, tone, mechanics, etc, of the game's system or framework, efficiently. I should encourage the player to provide detailed information in their responses.

There are a variety of examples I can take inspiration from for my suggestions:
 - Fantasy Adventure: Dungeons & Dragons, Pathfinder, The Elder Scrolls, Zork, King's Quest → Stats like Strength, Intelligence, Mana, Hit Points, Alignment, Encumbrance.
 - Sci-Fi & Space Opera: Traveller, Starfinder, Mass Effect, Fallen London, Eventide → Oxygen, Energy, Engineering, Reputation, Ship Integrity, Morale.
 - Cyberpunk & Dystopia: Shadowrun, Cyberpunk 2020/RED, Deus Ex, AI Dungeon → Augmentation Level, Cred, Street Rep, Heat, Cyberpsychosis.
 - Mystery / Noir: GUMSHOE, Blades in the Dark, The Case of the Golden Idol, 80 Days → Clues, Reputation, Vice, Stress, Insight.
 - Lighthearted / Slice of Life: Honey Heist, Pokémon Tabletop, Animal Crossing, 80 Days, A Dark Room → Friendship, Charm, Luck, Creativity, Chaos Meter.
 - Horror & Investigation: Call of Cthulhu, World of Darkness, Sunless Sea, Anchorhead → Sanity, Stress, Willpower, Clue Points, Fear, Insight.
Etc.

I'll do the following:
 - Summarize what's been defined so far
 - Acknowledge any new or updated properties and explain what each represents, how it might work in play, and how it fits the genre or tone we've been developing.
 - Ask what the player would like to do next: refine, add, or finalize the setup.
 - If appropriate, I'll suggest optional refinements, like adding modifiers, linking properties to dice mechanics, etc.

"""

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
