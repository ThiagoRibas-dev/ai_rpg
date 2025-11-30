"""
Templates for LLM prompts.
Updated for Flattened Layout and Strict Procedure Extraction.
"""

# --- GAMEPLAY ---
GAME_MASTER_SYSTEM_PROMPT = """
You are an expert Game Master (GM).
Your goal is to provide a vivid, immersive experience while adhering to the extracted rules.
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

# Phase 1: Core Stats
GENERATE_CORE_STATS_INSTRUCTION = """
You are creating a character sheet template for the game {target_game}.
Identify the **Fixed Global Stats** (Values & Gauges).

**DISTINCTIONS:**
*   **StatValue**: Static properties (Str, Dex, Level, AC).
*   **StatGauge**: Fluctuating resources (HP, Mana, Ammo).

**CONSTRAINTS:**
*   Mutually Exclusive: A stat cannot be both Value and Gauge.
*   Formulas: Use Python syntax (`10 + dex`) for derived stats. Do not write the result (`14`).

Output a JSON with `values` and `gauges`.
"""

# Phase 2: Containers
GENERATE_CONTAINERS_INSTRUCTION = """
You are creating a character sheet template for the game {target_game}.
Identify the **Dynamic Lists** (Collections).
Define the fields for items in these lists.

Examples:
- Skills (Name, Rank)
- Inventory (Name, Weight)
- Spells (Name, Cost, Effect)

Output a JSON with `collections`.
"""

# Phase 3: Layout (Flattened)
ORGANIZE_LAYOUT_INSTRUCTION = """
Now that you created the character sheet template for the game {target_game}, you are going to configure how everything will be laid out in the UI.
Assign every defined Stat (Value, Gauge, Collection) to a **Panel** and a **Group**.

**PANELS (Strict Assignment):**
*   `header`: Vital info (HP, Name, Level, Class, XP).
*   `sidebar`: Core Stats (Attributes, Saves, Passive Defenses).
*   `main`: Combat actions, Attacks, Initiative, Speed.
*   `equipment`: Inventory, Money, Encumbrance.
*   `skills`: Skill lists.
*   `spells`: Magic/Powers.
*   `notes`: Bio, Background.

**INSTRUCTION:**
Update the objects to set their `panel` field.
Use the `group` field to label the section within that panel (e.g. Panel: 'sidebar', Group: 'Attributes').
Do NOT dump everything in 'main'.
"""

# Phase 4: Procedures (Strict)
IDENTIFY_MODES_INSTRUCTION = """
Identify the distinct **Game Modes** (Loops).
Return ONLY a JSON list of strings.
Example: `["Combat", "Exploration", "Social"]`
"""

EXTRACT_PROCEDURE_INSTRUCTION = """
Extract the step-by-step **Procedure** for **{mode_name}**.

**STRICT FORMATTING:**
*   `description`: A concise summary of what this mode resolves.
*   `steps`: A list of strings. Each string is one step.
*   **NO CHAT:** Do not write "The user is asking..." or "I will extract...". Just output the data.
"""

# Phase 5: Mechanics
GENERATE_MECHANICS_INSTRUCTION = """
Extract specific **Game Rules** (Conditions, Actions, Magic Rules) for the Reference Index.
Key: Rule Name. Value: Rule Text + Tags.
"""

# --- WORLD GEN ---
CHARACTER_EXTRACTION_PROMPT = """
Extract character data into the schema.
Context: {template}
Input: "{description}"
"""

WORLD_EXTRACTION_PROMPT = """
Extract world details.
Input: "{description}"
"""

OPENING_CRAWL_PROMPT = """
Write a 2nd-person opening scene.
Genre: {genre}
Protagonist: {name}
Location: {location}
"""

JIT_SIMULATION_TEMPLATE = """
Simulate NPC actions.
NPC: {npc_name}
Time: {last_updated_time} -> {current_time}
"""
