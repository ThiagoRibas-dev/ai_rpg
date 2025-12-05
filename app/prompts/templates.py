"""
Templates for LLM prompts.
"""

# --- RULES & MECHANICS EXTRACTION ---

TEMPLATE_GENERATION_SYSTEM_PROMPT = """
You are a **Tabletop RPG Analyst and Architect**.
Your goal is to extract **Game Rules** for use by the Player later on.

### CRITICAL INSTRUCTIONS
1. **Precision:** Be precise and through in your extraction and design. Extract all relevant information, rules, and details.
2. **No Meta-Commentary:** When extracting rules or procedures, output ONLY the content. Do not say "Here is the procedure" or "I found this text".
3. **Generic Defaults:** Use 0, 10, or "" as defaults. Never use specific character data.
"""

IDENTIFY_MODES_INSTRUCTION = """
Identify the distinct **Game Modes** (Loops).
Return ONLY a JSON list of strings.
Example: `["Combat", "Exploration", "Social"]`
"""

EXTRACT_PROCEDURE_INSTRUCTION = """
Extract the step-by-step **Procedure** for **{mode_name}**.
"""

GENERATE_MECHANICS_INSTRUCTION = """
Extract specific **Game Rules** (Conditions, Actions, Magic Rules).
"""

# --- WORLD GENERATION ---

ANALYZE_WORLD_INSTRUCTION = """
You are an expert World Builder and Game Master.
Analyze the user's concept for a new RPG campaign.

**Input:** "{description}"

**Your Task:**
1.  **Genre & Tone:** Determine the specific sub-genre and atmospheric tone.
2.  **Starting Location:** Visualize the immediate starting scene location/zone. What does it look/smell/sound like?
3.  **Adjacency:** After defining the starting location, define all other locations that are directly adjacent to the starting zone.
4.  **Lore:** Extract or infer the key facts about the world (factions, history, technology, etc).
5.  **NPCs:** Identify who is immediately present in the scene.

Output your analysis as a structured thought process.
"""

GENERATE_WORLD_INSTRUCTION = """
Based on your analysis, extract the World Data into JSON.
"""

OPENING_CRAWL_PROMPT = """
Write a compelling, 2nd-person opening scene (approx 100-150 words).
Set the scene and end with a call to action.

**Context:**
*   **Genre:** {genre}
*   **Tone:** {tone}
*   **Protagonist:** {name}
*   **Location:** {location}

**Guidance:** {guidance}
"""

# --- GAMEPLAY ---

JIT_SIMULATION_TEMPLATE = """
Simulate NPC actions.
"""