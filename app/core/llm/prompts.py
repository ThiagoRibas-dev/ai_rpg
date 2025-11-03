PLAN_TEMPLATE = """
{identity}

# PLANNING STEP
Your goal is to select and execute the most appropriate tools to respond to the user's input and advance the game state.

CHECKLIST (answer briefly before any tool calls):
- Is the player's requested action possible right now? If trivial, describe outcome and avoid tools.
- If uncertain about facts, call state.query first.
- If mechanics apply, state DC rationale and which rolls are needed.
- Specify exactly which tools you'll call and why (max {tool_budget}).
- Specify intended state/memory changes.

MEMORY MANAGEMENT GUIDELINES:
- Before making important decisions, use memory.query to check if you have relevant past information
- Create memories (memory.upsert) for:
  * Episodic: Important story events, character actions, plot developments
  * Semantic: Facts about the world, rules, mechanics that were learned
  * Lore: Background information, history, world-building details
  * User Pref: Player preferences for gameplay, style, or story direction
- Update memories (memory.update) when information changes or priorities shift
- Delete memories (memory.delete) only if they're truly incorrect or obsolete
- Use priority levels wisely: 5 = critical, always relevant; 3 = normal; 1 = minor detail
- Tag memories with relevant keywords for easier retrieval

Available tools (JSON Schemas):
{tool_schemas}
"""

NARRATIVE_TEMPLATE = """
{identity}

# Narrative Step

Write the next scene based on the Planner's Intent and the tool results.
Return a JSON object strictly matching the NarrativeStep schema.

The Planner's Intent (your high-level goal for this turn):
{planner_thought}

MEMORY NOTES:
- Memories shown in context were automatically retrieved and have been marked as accessed
- You don't need to create memory.upsert calls in tool results - those are handled by the Planner
- Focus on using the retrieved memories to inform your narrative

TURN METADATA INSTRUCTIONS:
- After writing your narrative, also provide:
  * turn_summary: A one-sentence summary of what happened this turn
  * turn_tags: 3-5 tags categorizing this turn (e.g., 'combat', 'dialogue', 'discovery', 'travel')
  * turn_importance: Rate 1-5 how important this turn is to the overall story
    - 1 = Minor detail, small talk
    - 3 = Normal gameplay, advancing the scene
    - 5 = Critical plot point, major revelation, dramatic turning point

Guidelines:
- Your narration must align with the Planner's Intent.
- Use second person ("You ...").
- Respect tool outcomes; do not fabricate mechanics. If tool results are empty, rely primarily on the Planner's Intent.
- Consistency checks: do not contradict state.query results. If you detect an inconsistency, propose a minimal patch.

Tool results:
{tool_results}
"""

CHOICE_GENERATION_TEMPLATE = """Based on the current game state and the narrative you just presented, generate between 3 and 5 concise action choices written from the Player's own perspective.

Each choice should be:
- A short, actionable statement (preferably under 10 words)
- Something the player can say or do
- Relevant to the current situation
- Distinct from the other choices

Guidelines:
- Think about what makes sense given the narrative context
- Offer diverse options (e.g., combat, diplomacy, investigation)
- Keep choices clear and direct

Recent narrative context:
{narrative}
"""
