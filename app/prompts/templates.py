from app.tools.schemas import (
    MemoryUpsert,
    SchemaUpsertAttribute,
    EndSetupAndStartGameplay,
    Deliberate,
)

# ==============================================================================
# RULES EXTRACTION PROMPTS
# ==============================================================================

TEMPLATE_GENERATION_SYSTEM_PROMPT = """You are a meticulous game system analyst. You will be provided with the full text of a game's rules. Following that, you will be given a series of specific tasks to extract and structure different parts of the game's mechanics into a JSON format. Follow each task's instructions precisely and output ONLY the requested JSON object.
"""

GENERATE_ENTITY_SCHEMA_INSTRUCTION = """
Your task is to extract ONLY the core Attributes (like Strength, Dexterity, Intelligence) and Resources (like Health, MP, etc) that exist in the provided rules text.

- Attributes: Fixed scores that characters possess.
- Resources: Pools that can be spent or depleted.

For every attribute and resource, you MUST provide a concise, one-sentence description of its purpose in the game.
"""

GENERATE_CORE_RULE_INSTRUCTION = """
Based on the provided rules and the defined character attributes (provided as context), your task is to identify and define the single, primary action resolution mechanic. This is the core dice roll of the game (e.g., '1d20 + Attribute Modifier vs. DC/Difficulty Class', Dice Pool, Narrative, etc).
"""

GENERATE_DERIVED_RULES_INSTRUCTION = """
Your task is to define specific, derived game mechanics based on a foundational rule that has already been established.

You will be given the original rules text, the defined character attributes, and the core action resolution mechanic as context.

Now, using the foundational mechanic as a pattern, extract and define other rules and systems. Some examples of the things you are looking for:
- Armor Class (AC), Dodge, Parry, Soak, Damage Reduction, etc: How characters avoid or reduce harm (Defensive Systems).
- Saving Throws, Resistance Checks, Willpower, etc: How characters endure non-physical effects like magic, poison, or fear (Resistance Mechanics).
- Initiative, Turn Order, Action Points, etc: How the sequence of actions in a round is determined (Action Sequencing).
- Speed, Difficult Terrain, Cover, Concealment: How movement and positioning are handled in the game world (Movement and Positioning).
- Leveling, Experience Points (XP), Milestones: How characters improve over time (Character Advancement).
- Magic, Spellcasting, Hacking, Netrunning, Social Combat, Crafting: Detailed rules for specific, complex activities (Specialized Subsystems).

For each rule you create, ensure it is consistent with the provided foundational mechanic.
"""

GENERATE_ACTION_ECONOMY_INSTRUCTION = """
Your task is to analyze the provided rules and determine the game's Action Economy - the structure of a character's turn. Identify the system type (e.g., Action Points, Fixed Action Types like 'Standard/Move/Bonus', etc.) and describe its components.
"""

GENERATE_SKILLS_INSTRUCTION = """
Your task is to extract all Skills from the provided rules text.
You will be given the list of Attributes that have already been defined.
For each skill you identify, you MUST link it to one of the provided attributes in the `linked_attribute` field.
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
# Three-Phase Planning Prompts
# ==============================================================================

ANALYSIS_TEMPLATE = """
I am in the analysis phase of my turn. I will do the following:
1.  Carefully review the player's most recent message and the last few turns of conversation.
2.  Identify the core intent: what the player wants to do, know, or achieve.
3.  Write a concise, one-sentence summary of this intent.
"""

GAMEPLAY_STRATEGY_TEMPLATE = """
I am in the strategy phase for a GAMEPLAY turn. I will do the following:
1.  Review the Player Intent Analysis and the current game state (character stats, inventory, active quests, relevant memories, and world info).
2.  Create a step-by-step plan detailing the actions I will take to move the game forward. This includes identifying the specific tools I need to call (e.g., `state.query` to check facts, `rng.roll` for chance, `character.update` for damage/healing).
3.  Formulate a `response_plan` that outlines the narrative goal for my next message to the player. This will guide me on how to describe the scene, roleplay NPCs, and present the outcomes of the player's actions.
"""

SETUP_STRATEGY_TEMPLATE = f"""
Alright. Let me check the current game mode:
 - CURRENT GAME MODE: SETUP (Session Zero)

I am in the planning phase for a SETUP turn (Session Zero).
My goal is to help the player build the game's mechanics.

I will start by analyzing the player's request to determine which game properties/attributes (stats, resources, equipment, skills, etc.) I should create or modify if any.
Then, I will write a step-by-step plan, following:
    1.  For each new or updated property requested by the player, I will plan a call to the `{SchemaUpsertAttribute.model_fields["name"].default}` tool, ensuring I fill out all the necessary details like name, description, and type.
    2.  If the player asked a question or I need more information before acting, I will plan to use the `{Deliberate.model_fields["name"].default}` tool.
    3.  I'll plan to call the `{EndSetupAndStartGameplay.model_fields["name"].default}` tool in order to transition for the current SETUP mode into the GAMEPLAY mode as ssoon as the player has confirmed his desire to start the game.

And finally, I'll formulate a `response_plan` to guide my reply.
This `response_plan` will describe the current game mode (SETUP), the changes I made, affirm my understanding, and asks what the player wants to do next (add another stat or resource, modify an existing one, finish the SETUP mode and start the game, etc).

An example of my output : 
{{
  "plan_steps": [
    "1. Define the 'attribute1' attribute using `{SchemaUpsertAttribute.model_fields["name"].default}`. This will be a core stat for [description]], with a default value of 10.",
    "2. Create the 'resource1' resource using `{SchemaUpsertAttribute.model_fields["name"].default}`. I'll set it up as a resource with a maximum value based on another stat, and a default of 100.",
    "3. Add the 'resource2' property via `{SchemaUpsertAttribute.model_fields["name"].default}`. This will be a resource, starting at 100, that decreases in [condition] and regenerates 1 point per hour.",
    "4. The player has said they are happy with the defined attributes and are ready to start. I will call `{EndSetupAndStartGameplay.model_fields["name"].default}` to transition from SETUP mode to GAMEPLAY mode and start the game."
  ],
  "response_plan": "I will tell player that the core attributes of attribute1, resource1, and resource2 have been successfully created.\nAnd since the player has given the green light to start the game, I will announce that the setup is complete."
}}
"""

TOOL_SELECTION_SETUP_TEMPLATE = """
Alright, we are still in SETUP mode.
I have analyzed the player's intent, and concocted a "Step-by-step plan".

Now, I will do the following:
1.  Follow the step-by-step plan I created in the strategy phase.
2.  Translate each step into precise, structured tool calls from the list of available tools.
3.  Ensure I do not exceed the tool budget of {{tool_budget}} calls for this turn.
4.  Only use tools from this list: {{tool_names_list}}.

An example of my output :
[
  {{
    "tool_name": "{TOOL_NAME_SCHEMA_UPSERT}",
    "arguments": {{
      "property_name": "Attribute1",
      "description": "A core stat for physical actions.",
      "template": "stat",
      "default_value": 10,
      "min_value": 1,
      "max_value": 20
    }}
  }},
  {{
    "tool_name": "{TOOL_NAME_SCHEMA_UPSERT}",
    "arguments": {{
      "property_name": "Resource1",
      "description": "Maximum value based on [attribute].",
      "template": "resource",
      "default_value": 100,
      "max_value": 100
    }}
  }},
  {{
    "tool_name": "{TOOL_NAME_SCHEMA_UPSERT}",
    "arguments": {{
      "property_name": "Resource2",
      "description": "A resource that decreases and regenerates automatically.",
      "template": "resource",
      "default_value": 100,
      "max_value": 100,
      "regenerates": true
    }}
  }},
  {{
    "tool_name": "{TOOL_NAME_END_SETUP}",
    "arguments": {{
      "reason": "The player has confirmed that they are satisfied with the setup and that I should start the game by transitioning to GAMEPLAY mode."
    }}
  }}
]
"""

TOOL_SELECTION_GAMEPLAY_TEMPLATE = """
Okay. We are in GAMEPLAY mode, so let's continue.
I have analyzed the player's intent, and concocted a "Step-by-step plan".

Now, I will do the following:
1.  Follow the step-by-step plan I created in the strategy phase.
2.  Translate each step into precise, structured tool calls from the list of available tools.
3.  Ensure I do not exceed the tool budget of {tool_budget} calls for this turn.
4.  Only use tools from this list: {tool_names_list}.
"""

# ==============================================================================
# SETUP MODE PROMPTS
# ==============================================================================

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
