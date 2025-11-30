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
GENERATE_FUNDAMENTALS_INSTRUCTION = """
You are defining the template for **{target_game}**.

Identify the **Fundamental Stats** (Raw Inputs).
These are values the player assigns directly (e.g., Attributes, Level, Race, Class).

**DO NOT** include stats that are calculated from other stats (like AC or Save Bonuses).
**DO NOT** include lists (like Skills or Inventory).

Output a JSON with `fundamentals` (List of StatValue).
"""

# Step 2: Collections
GENERATE_CONTAINERS_INSTRUCTION = """
Identify the **Collections** (Dynamic Lists) for **{target_game}**.
Define the **Table Schema** (Columns) for items in these lists.

Examples:
- Skills (Name, Rank, Attribute Used)
- Inventory (Name, Weight, Qty)
- Spells (Name, Level, School)
- Feats/Talents (Name, Description)

Output a JSON with `collections`.
"""

# Step 3: Derived & Gauges
GENERATE_DERIVED_INSTRUCTION = """
I have defined the following for **{target_game}**:
Fundamentals: {fundamentals_list}
Collections: {collections_list}

**TASK:**
Identify **Derived Stats** (Calculated Formulas) and **Gauges** (Resources).

1.  **Derived Stats:** Values calculated from Fundamentals (e.g., `AC = 10 + Dex`).
    *   *Constraint:* You MUST provide a Python-syntax formula in the `calculation` field using the keys from Fundamentals.
2.  **Gauges:** Pools that fluctuate (e.g., HP, Mana, Ammo).
    *   *Constraint:* `max_formula` should reference Fundamentals (e.g., `10 + Con`).

Output a JSON with `derived` and `gauges`.
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

# ... (Procedures/Mechanics/WorldGen remain the same) ...
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

JIT_SIMULATION_TEMPLATE = """
Simulate NPC actions.
"""
