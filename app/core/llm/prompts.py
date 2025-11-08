from app.tools.schemas import (
    MemoryUpsert,
    StateQuery,
    SchemaDefineProperty,
    Deliberate,
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
1.  **Understand the player's message:** I'll analyze their input to see what genre, tone, setting, properties, or mechanical ideas they proposed or accepted.
2.  **Evaluate the current setup:** I'll use `{StateQuery.model_fields["name"].default}` to see what we've already defined (skills, attributes, rules, etc.). I'll compare their message with the current state to see what's missing or needs clarification.
3.  **Use the right tool for the job:**
    *   **`{SchemaDefineProperty.model_fields["name"].default}`**: I'll use this tool to save or persist any new or updated attributes, rules, mechanics, skills, etc, once per property.
    *   **`{Deliberate.model_fields["name"].default}`**: If I'm not sure what to do next, or if the player's message doesn't require a change, I'll use this tool to reflect and prepare my next question for them. This is my default "thinking" step.
    *   **`{EndSetupAndStartGameplay.model_fields["name"].default}`**: If and only if the player has explicitly confirmed that the setup is complete and we are ready to begin the game, I'll use this tool to transition to the gameplay phase. I must provide a `reason` for using this tool.
4.  **Plan my response:** After any tool calls, I'll plan my response to the player. This usually involves summarizing the current setup, explaining any new properties, and asking what they want to work on next.

I am not speaking to the player yet. This is my private planning phase.
"""

SETUP_RESPONSE_TEMPLATE = """
Alright. Let me check the current game mode:
 - CURRENT GAME MODE: SETUP (Session Zero)

We are still in the SETUP game mode (Session Zero phase), so the player has not yet confirmed that the setup is complete.

I'll do the following:
 - Summarize what's been defined so far
 - Acknowledge any new or updated properties and explain what each represents, how it might work in play, and how it fits the genre or tone we've been developing.
 - Ask what the player would like to do next: refine, add, or finalize the setup.
 - If appropriate, I'll suggest optional refinements, like adding modifiers, linking properties to dice mechanics, etc.

The idea is to get as much information as possible about the desired world, rules, tone, mechanics, etc, of the game's system or framework, efficiently. I should encourage the player to provide detailed information in their responses.

There are a variety of examples I can take inspiration from for my suggestions:
 - Fantasy Adventure: Dungeons & Dragons, Pathfinder, The Elder Scrolls, Zork, King's Quest → Stats like Strength, Intelligence, Mana, Hit Points, Alignment, Encumbrance.
 - Horror & Investigation: Call of Cthulhu, World of Darkness, Sunless Sea, Anchorhead → Sanity, Stress, Willpower, Clue Points, Fear, Insight.
 - Sci-Fi & Space Opera: Traveller, Starfinder, Mass Effect, Fallen London, Eventide → Oxygen, Energy, Engineering, Reputation, Ship Integrity, Morale.
 - Cyberpunk & Dystopia: Shadowrun, Cyberpunk 2020/RED, Deus Ex, AI Dungeon → Augmentation Level, Cred, Street Rep, Heat, Cyberpsychosis.
 - Mystery / Noir: GUMSHOE, Blades in the Dark, The Case of the Golden Idol, 80 Days → Clues, Reputation, Vice, Stress, Insight.
 - Lighthearted / Slice of Life: Honey Heist, Pokémon Tabletop, Animal Crossing, 80 Days, A Dark Room → Friendship, Charm, Luck, Creativity, Chaos Meter.
Etc.

"""
