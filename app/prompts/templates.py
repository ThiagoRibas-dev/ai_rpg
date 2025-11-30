"""
Templates for LLM prompts.
Updated for 3-Step Definition Flow (Fundamentals -> Collections -> Derived).
"""

# --- TEMPLATE GENERATION ---

TEMPLATE_GENERATION_SYSTEM_PROMPT = """
You are a **Tabletop RPG Database Architect**.
Your goal is to extract **Game Rules** and then esign a **BLANK Character Sheet Template** for use by the Player later on.

### CRITICAL INSTRUCTIONS
1. **No Meta-Commentary:** When extracting rules or procedures, output ONLY the content. Do not say "Here is the procedure" or "I found this text".
2. **Design the Character Sheet Template, Don't Fill It:** Define the fields the Player will fill out.
3. **Generic Defaults:** Use 0, 10, or "" as defaults. Never use specific character data.
"""

# Step 1: Fundamentals
ANALYZE_FUNDAMENTALS_INSTRUCTION = """
You are creating a character sheet template for the game {target_game} as markdown.
Analyze and identify the Basic values (stats, attributes, etc) of a character or entity.
These are the basic values from which other values may be derived.

For each item, provide a brief description or summary.
"""

GENERATE_FUNDAMENTALS_INSTRUCTION = """
You are creating a character sheet template for the game {target_game} as JSON.

Define the Basic values (stats, attributes, etc) of a character or entity.
These are the basic values from which other values may be derived.

Output a JSON with `fundamentals` (List of StatValue).
"""

# Step 2: Collections
ANALYZE_CONTAINERS_INSTRUCTION = """
You are creating a character sheet template for the game {target_game} as markdown.
Analyze which parts of a character or game entity should be represented as lists or complex objects in a JSON formatted character sheet.

Things like the entity's body parts where gear can be equiped, list of features/perks and the like, list of jobs/classes/professions/role and such, etc.
For now, just list these things with a brief explanation of what each represent in the game system.
"""

GENERATE_CONTAINERS_INSTRUCTION = """
You are creating a character sheet template for the game {target_game} in JSON format.
Identify the **Dynamic Lists** (Collections) and define the fields for each record in these lists.

Output a JSON with `collections`.
"""

# Step 3: Derived & Gauges
ANALYZE_DERIVED_INSTRUCTION = """
You are creating a character sheet template for the game {target_game} as markdown.

Analyze and identify the following :
 - Derived values, which are calculated based on a formula that uses other values;
 - Gauges (resources) that have a minimum and maximum value, and can fluctuate based on some condition (use, damage, time, etc);
 - Tracks, which are segmented progress bars or checkboxes that track progress or individual units (e.g., stress, harm, clocks, spell slots, experience points).

For each item, provide a brief description or summary, and if appropriate the formulas or rules governing the value, gauge, or track.
"""

GENERATE_DERIVED_INSTRUCTION = """
You are creating a character sheet template for the game {target_game} as markdown.

Given the following:
Fundamentals: {fundamentals_list}
Collections: {collections_list}

Identify **Derived Stats** (Calculated), **Gauges** (Pools), and **Tracks** (Progress or Checkboxes).

1. **Derived Stats:** ...
2. **Gauges:** Pools with Current/Max (HP).
3. **Tracks:** Segmented progress bars or checkboxes (0 to N).
   * Used for: Stress, Harm, Clocks, Experience points.
   * Define `length` (how many boxes).

Output a JSON with `derived`, `gauges`, and `tracks`.
"""

# Step 4: Layout (Mapping)
ORGANIZE_LAYOUT_INSTRUCTION = """
I have defined the following IDs for **{target_game}**:
{stat_list}

**TASK:**
Assign a **Panel** and a **Group** for EACH of these IDs.

**PANELS:**
*   `header`: Vital info (HP, Name, Level, Class).
*   `sidebar`: Core Stats (Attributes, Saves).
*   `main`: Combat actions, Attacks, Speed.
*   `equipment`: Inventory, Money.
*   `skills`: Skill lists.
*   `spells`: Magic.
*   `notes`: Bio.

**OUTPUT:**
A JSON object mapping ID -> {{ "panel": "...", "group": "..." }}.
"""

# Step 5: Extract rules
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

# Setup Prompts for World and Character Extraction
CHARACTER_EXTRACTION_PROMPT = """
Extract character data.
Context: {template}
Input: "{description}"
"""

WORLD_EXTRACTION_PROMPT = """
Extract world details.
Input: "{description}"
"""

OPENING_CRAWL_PROMPT = """
Write a 2nd-person opening scene.
"""

# Gameplay Prompts
JIT_SIMULATION_TEMPLATE = """
Simulate NPC actions.
"""
