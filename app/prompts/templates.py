from app.tools.schemas import (
    MemoryUpsert,
    SchemaDefineProperty,
    EndSetupAndStartGameplay,
)

RULES_ANALYSIS_PROMPT = """
You are a game system analyst.
Extract detailed structured game mechanics from rules documents.

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
   - abbreviation: Short code (e.g., "STR")
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

```

Now analyze the provided rules document and generate the JSON rules schema.
"""


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
