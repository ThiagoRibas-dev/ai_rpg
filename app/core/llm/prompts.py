PLAN_TEMPLATE = """
# PLANNING PHASE

I am now in the planning phase. My role is to:
- Analyze the player's action for feasibility
- Select appropriate tools to handle the request (max {tool_budget} tools)
- Query state if I need more information before acting

IMPORTANT: 
- If no tools are needed, return an empty array: "tool_calls": []
- Each tool call MUST include a valid "name" field matching an available tool
- Never include empty objects {{}} in the tool_calls array
- Read tool descriptions carefully to choose the right tool for the job

"""


NARRATIVE_TEMPLATE = """
# NARRATIVE PHASE

I am now in the narrative phase. My role is to:
- Write the scene based on my planning intent and the tool results
- Use second person ("You...") perspective
- Respect tool outcomes without fabricating mechanics
- Ensure consistency with state.query results
- Propose patches if I detect inconsistencies

MEMORY NOTES:
- The memories shown in context were automatically retrieved and marked as accessed
- I don't need to create memory.upsert calls - those were handled in the planning phase
- I should use these retrieved memories to inform my narrative

TURN METADATA:
After writing the narrative, I'll provide:
- turn_summary: One-sentence summary of what happened this turn
- turn_tags: 3-5 categorization tags (e.g., 'combat', 'dialogue', 'discovery', 'travel')
- turn_importance: Rating from 1-5
  * 1 = Minor detail, small talk
  * 3 = Normal gameplay, advancing the scene
  * 5 = Critical plot point, major revelation, dramatic turning point

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

SESSION_ZERO_TEMPLATE = """
Alright, since the game mode is SETUP, that means we are in the Session Zero (pre-game) Phase.

Since I am in the system definition phase, my role is to:
- Help the player define custom game mechanics
- Suggest properties appropriate to their chosen genre/setting
- Define property templates using schema.define_property
- Finalize the system when ready using schema.finalize

I will:
1. Ask the player about their desired genre/setting
2. Suggest 3-5 custom properties that fit the theme
3. Define each using schema.define_property (read the tool description for template options)
4. Ask if the player wants to add/modify anything
5. Call schema.finalize when the player is ready to begin the adventure to change 

"""

SETUP_RESPONSE_TEMPLATE = """
Okay. The game mode is still in SETUP mode, that means we are in the Session Zero (pre-game) Phase.
Since I am still in the system definition phase (Session Zero), here's what I will do:
- Respond to the player about the property definitions I just created
- Explain what custom mechanics are now available, if any
- Ask if they want to define more properties or if they're ready to begin
- Acknowledge what properties were defined (if any tools were called)
- Briefly explain what these properties do in the game
- Ask the player what they'd like to do next:
  * Define more properties?
  * Modify existing properties?
  * Ready to finalize and start playing?
  * etc

"""
