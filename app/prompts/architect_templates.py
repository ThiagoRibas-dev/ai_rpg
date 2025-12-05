"""
Prompts for the Dynamic Sheet Generator (The Architect).
Refactored to use a single System Prompt for context caching efficiency.
"""

# --- UNIFIED SYSTEM PROMPT ---

SHEET_GENERATOR_SYSTEM_PROMPT = """
You are an expert **TTRPG Designer and Game Master Assistant**.
Your role is to handle the entire lifecycle of character creation:
1.  **Architecting** data structures (JSON schemas) for character sheets.
2.  **Brainstorming** creative character details based on rules.
3.  **Mapping** narrative concepts into strict data models.

Always adhere to the specific instructions provided in the user prompt.
When asked for JSON, ensure it is valid and strictly follows the requested schema.
"""

# --- PASS 1: STRUCTURE GENERATION (Targeting Blueprint) ---

ARCHITECT_INSTRUCTION = """
### TASK: SYSTEM ARCHITECT
Design a **Character Sheet Blueprint** based on the provided Rules and Concept.
Define the "Shape" of the character sheet using the 10 Semantic Categories.

### FIELD CONCEPTS (Choose One for each field)
1.  **stat**: A numeric attribute (e.g. Strength, XP).
2.  **text**: A text field (e.g. Name, Race).
3.  **die**: A die code (e.g. 1d6, d20).
4.  **pool**: A resource with Current/Max (e.g. HP, Mana).
5.  **list**: A container for multiple items (e.g. Inventory, Skills, Feats).
6.  **toggle**: A true/false checkbox.

### CRITICAL RULES
1.  **Lists:** If the rules imply a list (e.g. "Weapons", "Spells"), use `concept="list"` and provide `list_columns` (e.g. ["name", "damage"]).
2.  **Pools:** If a stat goes up and down (HP, Sanity), use `concept="pool"`.
3.  **Defaults:** Provide reasonable defaults (e.g. HP max = 10).
4.  **Categories:** Strictly adhere to the 10 categories (meta, identity, attributes, skills, resources, features, inventory, connections, narrative, progression).

**Output strictly JSON matching the `SheetBlueprint` schema.**
"""

ARCHITECT_USER_TEMPLATE = """
**Game Rules / System Context:**
{rules_text}

**Character Concept:**
{character_concept}

{instruction}
"""

# --- PASS 2A: CHARACTER ANALYSIS (Brainstorming) ---

CHAR_ANALYSIS_INSTRUCTION = """
### TASK: CHARACTER BRAINSTORMING
Analyze the character concept against the rules and the target sheet structure.
**Do NOT output JSON.** Output a structured text analysis.

### REQUIREMENTS
1.  **Identity:** Name, Background, Appearance.
2.  **Stats & Attributes:** Assign values to the specific fields defined in the Sheet Structure.
3.  **Resources:** Calculate starting values for pools (e.g. HP) based on the rules.
4.  **Skills/Abilities:** Select specific skills/feats that fit the concept and rules.
5.  **Equipment:** Choose starting gear.
"""

CHAR_ANALYSIS_USER_TEMPLATE = """
**Game Rules:**
{rules_text}

**Target Sheet Structure (Fields to fill):**
{sheet_structure}

**Character Concept:**
{character_concept}

{instruction}
"""

# --- PASS 2B: DATA POPULATION (Mapping to Schema) ---

POPULATE_INSTRUCTION = """
### TASK: DATA MAPPING
Map the provided **Character Analysis** into the **Target Schema**.

### CRITICAL RULES
1. **Molecule Fields:** If a field is defined as a `molecule` (e.g., HP), you MUST provide a dictionary with the components.
   *   *Wrong:* `"hp": 10`
   *   *Right:* `"hp": { "current": 10, "max": 10 }`
2. **List Fields:** If a field is a `list` container (e.g. Inventory), you MUST provide a dictionary containing the list key.
   *   *Wrong:* `"inventory": [ ...items... ]`
   *   *Right:* `"inventory": { "backpack": [ ...items... ] }`
   *   *(Note: Look at the schema to see the actual list key, usually 'backpack' or 'items')*

**Return a JSON dictionary where keys match the Schema categories exactly.**
"""

POPULATE_WITH_ANALYSIS_TEMPLATE = """
**Character Analysis:**
{analysis_text}

**Target Schema (JSON Structure):**
{schema_json}

{instruction}
"""
