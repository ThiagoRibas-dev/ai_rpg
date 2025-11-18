from app.tools.schemas import (
    MemoryUpsert,
    SchemaUpsertAttribute,
)

# ==============================================================================
# RULES EXTRACTION PROMPTS
# ==============================================================================

TEMPLATE_GENERATION_SYSTEM_PROMPT = """You are a meticulous game system analyst. You will be provided with the full text of a game's rules.

Your job is to convert this text into a structured database format.
You will perform this in two major phases:
1. **Ruleset Extraction**: Defining the global physics, resolution mechanics, and content libraries (Compendium).
2. **StatBlock Definition**: Defining the structure of a Player Character sheet (Abilities, Vitals, Tracks, Slots).

Follow each task's instructions precisely and output ONLY the requested JSON object.
"""

# --- PHASE 1: RULESET ---

ANALYZE_RULESET_INSTRUCTION = """
**Task**: Analyze the text for Global Game Rules.

Please list the following based **ONLY** on the provided text:
1. The **Core Resolution Mechanic** (How do you roll for success?).
2. Any **Tactical Rules** (Movement, Combat actions, Environmental hazards).
3. **Compendium Items**: Lists of Conditions, Skills, and Damage Types explicitly mentioned.

If a common mechanic (like "Magic" or "Sanity") is NOT in the text, explicitly state that it is absent.
"""

GENERATE_CORE_RESOLUTION_INSTRUCTION = """
**Task**: Identify the game's **Core Resolution Mechanic**.

This is the fundamental method used to resolve uncertainty (e.g., "d20 + Mod vs DC", "Roll Xd6, count 6s", "Percentile Roll under Skill").
Also identify the **Dice System** used.
"""

GENERATE_TACTICAL_RULES_INSTRUCTION = """
**Task**: Extract **Tactical & Environmental Rules**.

Look for rules that apply to everyone, not just specific characters.
- **Tactical**: Grappling, Flanking, Cover, Movement, Initiative, Range.
- **Environmental**: Falling, Drowning, Illumination, Travel Pace, Starvation.

Return a list of rule entries.
"""

GENERATE_COMPENDIUM_INSTRUCTION = """
**Task**: Build the **Compendium** (Global Library).

Extract lists of:
1. **Conditions**: Status effects (e.g., Prone, Blinded, Stunned).
2. **Skills**: Learned abilities (e.g., Athletics, Stealth). If linked to an attribute (like DEX), note it.
3. **Damage Types**: (e.g., Fire, Slashing, Mental).
"""

# --- PHASE 2: STATBLOCK ---

ANALYZE_STATBLOCK_INSTRUCTION = """
**Task**: Analyze the text for Character Sheet Structure.

Please list the following based **ONLY** on the provided text:
1. **Abilities/Attributes**: The core stats (e.g., STR, DEX). Are they numbers or dice codes?
2. **Vitals/Resources**: Pools that fluctuate (e.g., HP). Is there a formula for them?
3. **Tracks**: Abstract progress bars (e.g., XP, Clocks). 
4. **Slots/Inventory**: How items or spells are carried.

**CRITICAL**: Do not infer mechanics not present. If the text does not mention "Sanity", "Stress", or "Cyberware", explicitly note that they are NOT in the system.
"""

GENERATE_ABILITIES_INSTRUCTION = """
**Task**: Define the **Abilities** (Core Stats) for a Player Character.

Determine the `data_type`:
- `integer`: Standard numbers (e.g., D&D Strength 1-20).
- `die_code`: Polyhedral dice codes (e.g., Savage Worlds "d6", "d8").
- `dots`: Small integers (e.g., Vampire 1-5).
"""

GENERATE_VITALS_INSTRUCTION = """
**Task**: Define **Vitals** (Resource Pools).

These are pools that go up and down frequently (HP, Mana, Sanity, Stamina).
If there is a formula for the maximum value (e.g., "10 + Constitution"), extract it.
"""

GENERATE_TRACKS_SLOTS_INSTRUCTION = """
**Task**: Define **Tracks** and **Slots**.

1. **Tracks**: Abstract progress bars or clocks (e.g., Experience Points, Stress, Corruption, Alert Level).
2. **Slots**: Containers for items or features (e.g., Inventory, Spell Slots, Cyberware Capacity).
"""

# ==============================================================================
# Two-Phase Planning Prompts
# ==============================================================================

GAMEPLAY_PLAN_TEMPLATE = """
I am in the planning phase for a GAMEPLAY turn. I will perform two tasks and structure my output as a JSON object with 'analysis' and 'plan_steps'.
1. **Analysis**: Review the player's last message and the conversation history to determine their core intent.
2. **Plan Steps**: Based on my analysis and the current game state (character, inventory, quests, memories, world info, etc), create a step-by-step plan of actions I will take. This includes naming the necessary tool calls.
"""

SETUP_PLAN_TEMPLATE = f"""
What is the current game mode?
- CURRENT GAME MODE: SETUP (Session Zero)

Okay, so I am in the planning phase for a SETUP turn and my goal, instead of narrating a scene or roleplay, is to help the player build the game's mechanics before we begin the game.
I will structure my output as a JSON object with 'analysis' and 'plan_steps' for setting the rules of the game up.

I will perform two tasks:
1. **Analysis**: Review the player's last message and the conversation history to determine their core intent.
2. **Plan Steps**: I will write a step-by-step plan for my actions right now, where:
    - For each new or updated property the player explicitly requested or agreed to, I will plan a call to the `{SchemaUpsertAttribute.model_fields["name"].default}` tool, naming it more than once if necessary.
    - When necessary, I will plan asking questions about the game's systems and rules, as well as clarifying questions in general.
    - I'll plan a response to the player's last message. If the player is asking a question, I will plan my reply.
"""
 
# Per-Step Tool Selection Prompt ---
TOOL_SELECTION_PER_STEP_TEMPLATE = """
I will now select the single best tool to accomplish the following plan step.

For this response, I'll do exactly the following:
1. Analyze the provided "Plan Step" in the context of the overall "Analysis" and conversation history for what actions I need to take *now*.
2. If the step is an action that needs to be executed now, choose one or more tools that directly executes this step from the "Available Tools" list.
3. If the step is a future action,, is purely for dialogue, narration, doesn't require a tool, or if there isn't enough information to select a tool with the correct arguments, I will select the {deliberate_tool}.
4. When faced with a step that mentions changing or transitioning the game's mode (SETUP, GAMEPLAY), I'll consider very carefully if that tool should be selected now, or if the intent is to do that later. In that case, I'll select the {deliberate_tool} 

**Analysis**: {analysis}
**Available Tools**: {tool_names_list}
**Plan Step to execute**: "{plan_step}"

Now I'm ready to do this.

Selected tools :
"""

# ==============================================================================
# WORLD SIMULATION PROMPTS
# ==============================================================================
 
JIT_SIMULATION_TEMPLATE = """
You are a Just-In-Time world simulator. An NPC who has been "off-screen" is now relevant to the player. Your job is to determine what plausibly happened to them in the intervening time.

**INSTRUCTIONS:**
1.  Review the NPC's profile and their directive.
2.  Based on the time that has passed, generate a brief, plausible summary of what they have been doing. Not every action results in a grand discovery; minor progress or setbacks are common.
3.  Decide if this outcome is **significant**. A significant event changes the world state, creates a new story hook, or is important for the player to discover. Minor progress (e.g., 'continued their patrol') is NOT significant.
4.  If the outcome causes a direct change to the NPC or the world, create one or more JSON patches to reflect it.

**CONTEXT:**
- **NPC Name:** {npc_name}
- **Personality:** {personality}
- **Motivations:** {motivations}
- **Directive (Goal):** "{directive}"
- **Time Passed:** From '{last_updated_time}' to '{current_time}'

Now, provide the outcome as a JSON object conforming to the WorldTickOutcome schema.
"""

# ==============================================================================
# SETUP MODE PROMPTS
# ==============================================================================

SETUP_RESPONSE_TEMPLATE = """
Alright. Let me check the current game mode:
 - CURRENT GAME MODE: SETUP (Session Zero)

We are still in the SETUP game mode (Session Zero/pre-game phase), so the player has not yet confirmed that the setup is complete.
Right now I need to get as much information as possible about the desired world, rules, tone, mechanics, etc, of the game's system or framework, efficiently.
Instead of trying to narrate scenes or roleplay, I will encourage the player to provide detailed information in their responses until we are both satisfied with the details.

There are a variety of examples I can take inspiration from for my suggestions:
 - Fantasy Adventure: Dungeons & Dragons, Pathfinder, The Elder Scrolls, Zork, King's Quest; Stats like Strength, Intelligence, Mana, Hit Points, Alignment, Encumbrance.
 - Sci-Fi & Space Opera: Traveller, Starfinder, Mass Effect, Fallen London, Eventide; Oxygen, Energy, Engineering, Reputation, Ship Integrity, Morale.
 - Cyberpunk & Dystopia: Shadowrun, Cyberpunk 2020/RED, Deus Ex, AI Dungeon; Augmentation Level, Cred, Street Rep, Heat, Cyberpsychosis.
 - Mystery / Noir: GUMSHOE, Blades in the Dark, The Case of the Golden Idol, 80 Days; Clues, Reputation, Vice, Stress, Insight.
 - Lighthearted / Slice of Life: Honey Heist, PokÃ©mon Tabletop, Animal Crossing, 80 Days, A Dark Room; Friendship, Charm, Luck, Creativity, Chaos Meter.
 - Horror & Investigation: Call of Cthulhu, World of Darkness, Sunless Sea, Anchorhead; Sanity, Stress, Willpower, Clue Points, Fear, Insight.
Etc.

Since we are not yet playing the game, I will not narrate or describe a scene. Instead, I'll do the following:
 - Summarize what's been defined so far
 - Acknowledge any new or updated properties and explain what each represents, how it might work in play, and how it fits the genre or tone we've been developing.
 - Ask what the player would like to do next: refine, add, or finalize the Session Zero and begin the game (transition from SETUP mode to GAMEPLAY mode).
 - If appropriate, I'll suggest optional refinements, like adding mechanics, game properties, rules, etc.
 - Acknowledge that for now there will be no roleplay, describing scenes, or narration. We are still setting the rules of the game up.
"""

# ==============================================================================
# GAMEPLAY MODE PROMPTS
# ==============================================================================

NARRATIVE_TEMPLATE = f"""
Okay. I am now in the narrative phase.
My role as the Game Master is to:
- Write the scene based on the conversation history so far, the player's last message, the planning intent, and the tool results
- Balance the pace and speed of events, not too slow and not too fast by default
- Use second person ("You...") perspective
- Respect tool outcomes without fabricating mechanics
- Ensure consistency with state.query results
- Propose patches if I detect inconsistencies
- And most crucial of all, respect the player's agency, always asking for his input, never assuming his actions, thoughts, feelings, etc

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

Now to respond as the Game Master and continue the game.
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
