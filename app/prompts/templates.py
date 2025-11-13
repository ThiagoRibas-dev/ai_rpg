from app.tools.schemas import (
    MemoryUpsert,
    SchemaDefineProperty,
    EndSetupAndStartGameplay,
)

# ==============================================================================
# RULES EXTRACTION PROMPTS
# ==============================================================================

TEMPLATE_GENERATION_SYSTEM_PROMPT = """You are a meticulous game system analyst. You will be provided with the full text of a game's rules. Following that, you will be given a series of specific tasks to extract and structure different parts of the game's mechanics into a JSON format. Follow each task's instructions precisely and output ONLY the requested JSON object.
"""

GENERATE_ENTITY_SCHEMA_INSTRUCTION = """
Your task is to extract ONLY the core Attributes (like Strength, Dexterity, Intelligence) and Resources (like Health, Mana, Sanity) from the provided rules text.

- **Attributes:** Fixed scores that characters possess.
- **Resources:** Pools that can be spent or depleted.

For every attribute and resource, you MUST provide a concise, one-sentence description of its purpose in the game.
"""

GENERATE_CORE_RULE_INSTRUCTION = """
Based on the provided rules and the defined character attributes (provided as context), your task is to identify and define the single, primary action resolution mechanic. This is the core dice roll of the game (e.g., '1d20 + Attribute Modifier vs. Difficulty Class').
"""

GENERATE_DERIVED_RULES_INSTRUCTION = """
Your task is to define specific, derived game mechanics based on a foundational rule that has already been established.

You will be given the original rules text, the defined character attributes, and the core action resolution mechanic as context.

Now, using the foundational mechanic as a pattern, extract and define the other rules and systems. A couple of examples of rules would be:
- **Defensive Systems:** How do characters avoid or reduce harm? Is it a static target number (like Armor Class), an active defense roll (like Dodge/Parry), a way to soak/reduce damage after being hit, or something else entirely?
- **Resistance Mechanics:** How do characters endure non-physical effects (like magic, poison, fear, or social influence)? Is it a categorical roll (like "Save vs. Poison"), an attribute-based check, or do they spend a resource (like Willpower or Stress) to resist?
- **Resource Pools:** What key resources do characters track? Look for systems governing Health (Hit Points, Wound Levels, Harm), Magic/Powers (Mana, Spell Slots, Drain), and Mental State (Sanity, Stress, Humanity).
- **Action Sequencing:** How is the order of actions in a round determined? Is there a rolled initiative, a static score, a narrative turn order, or an action point system?
- **Character Advancement:** How do characters improve over time? Is it a level-based system, or do players spend experience points on individual traits?
- **Specialized Subsystems:** Are there detailed rules for specific, complex activities? Look for things like Magic/Spellcasting, Hacking/Netrunning, Social Combat, or Crafting.
- **Movement and Positioning:** How is movement handled? Are there rules for speed, difficult terrain, taking cover, or being concealed?

For each rule you create, ensure it is consistent with the provided foundational mechanic.
"""

## ==============================================================================
## Iterative prompt for derived rules
## ==============================================================================
GENERATE_DERIVED_RULES_INSTRUCTION_ITERATIVE = """
Your task is to extract additional game mechanics and rules from the provided text that are NOT present in the list of rules already found.

Review the existing rules and find any missing systems (e.g., defense, resistance, movement, special subsystems).

If you cannot find any more distinct rules, return an empty list.
"""

GENERATE_ACTION_ECONOMY_INSTRUCTION = """
Your task is to analyze the provided rules and determine the game's Action Economy - the structure of a character's turn. Identify the system type (e.g., Action Points, Fixed Action Types like 'Standard/Move/Bonus', etc.) and describe its components.
"""

GENERATE_SKILLS_INSTRUCTION = """
Your task is to extract all Skills from the provided rules text.
You will be given the list of Attributes that have already been defined.
For each skill you identify, you MUST link it to one of the provided attributes in the `linked_attribute` field.
"""

GENERATE_SKILLS_INSTRUCTION_ITERATIVE = """
Your task is to extract additional Skills from the provided rules text that are NOT present in the list of skills already found.

If you cannot find any more skills, return an empty list.
"""

GENERATE_CONDITIONS_INSTRUCTION = """
Your task is to extract all status effects, also known as Conditions (e.g., 'Blinded', 'Poisoned', 'Stunned'), from the provided rules text. For each condition, provide a concise description of its mechanical effect.
"""

GENERATE_CLASSES_INSTRUCTION = """
Your task is to identify and define the character Classes (e.g., 'Warrior', 'Mage', 'Rogue') from the rules. You will be provided with the game's attributes and skills for context. For each class, describe its primary role and key features.
"""

GENERATE_RACES_INSTRUCTION = """
Your task is to identify and define the character Races or Species (e.g., 'Elf', 'Dwarf', 'Orc') from the rules. You will be provided with the game's attributes and skills for context. For each race, describe its unique traits.
"""

# ==============================================================================
# SETUP MODE PROMPTS
# ==============================================================================

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
 - Fantasy Adventure: Dungeons & Dragons, Pathfinder, The Elder Scrolls, Zork, King's Quest â†’ Stats like Strength, Intelligence, Mana, Hit Points, Alignment, Encumbrance.
 - Sci-Fi & Space Opera: Traveller, Starfinder, Mass Effect, Fallen London, Eventide â†’ Oxygen, Energy, Engineering, Reputation, Ship Integrity, Morale.
 - Cyberpunk & Dystopia: Shadowrun, Cyberpunk 2020/RED, Deus Ex, AI Dungeon â†’ Augmentation Level, Cred, Street Rep, Heat, Cyberpsychosis.
 - Mystery / Noir: GUMSHOE, Blades in the Dark, The Case of the Golden Idol, 80 Days â†’ Clues, Reputation, Vice, Stress, Insight.
 - Lighthearted / Slice of Life: Honey Heist, PokÃ©mon Tabletop, Animal Crossing, 80 Days, A Dark Room â†’ Friendship, Charm, Luck, Creativity, Chaos Meter.
 - Horror & Investigation: Call of Cthulhu, World of Darkness, Sunless Sea, Anchorhead â†’ Sanity, Stress, Willpower, Clue Points, Fear, Insight.
Etc.

I'll do the following:
 - Summarize what's been defined so far
 - Acknowledge any new or updated properties and explain what each represents, how it might work in play, and how it fits the genre or tone we've been developing.
 - Ask what the player would like to do next: refine, add, or finalize the setup.
 - If appropriate, I'll suggest optional refinements, like adding modifiers, linking properties to dice mechanics, etc.

"""

# ==============================================================================
# GAMEPLAY MODE PROMPTS
# ==============================================================================

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