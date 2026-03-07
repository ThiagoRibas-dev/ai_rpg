"""
Templates for LLM prompts.
"""

# --- SHARED BASE PROMPT (CONSTANT) ---

SHARED_RULES_SYSTEM_PROMPT = """
You are an specialist **Tabletop RPG Analyst and Architect**.
Your goal is to analyze the provided Game Rules text, understand, then extract the relevant rules, formulas, data models, mechanics, procedures, etc.

## CRITICAL INSTRUCTIONS
1. **Source of Truth:** The provided Rules Text is your primary source of information. While you may use your prior knowledge to fill in gaps, always prioritize the provided text.
2. **Precision:** Be specific and precise. Extract specific numbers, formulas, dice codes, rules, keywords, mechanics, etc.
3. **Efficiency:** Keep responses concise and to the point. Efficiently distil and extract only the relevant information.
4. **Structure not Content:** Focus on extracting the core, basal, structural information instead of specific content. The structures that exist regardless of the player choices, where the player chooses the values.

## RULES TEXT
{rules_source}
"""

# --- INSTRUCTIONS (USER MESSAGES) ---

# Vocabulary
VOCABULARY_ANALYSIS_INSTRUCTION = """
Analyze the rules text above and identify its mechanical building blocks.

Look for:
1. **CORE TRAITS** (Stats, Attributes, Approaches)
2. **RESOURCES** (HP, Stress, Ammo, Mana)
3. **CAPABILITIES** (Skills, Moves, Feats)
4. **STATUS** (Conditions, Wounds)
5. **ASPECTS** (Narrative tags)
6. **PROGRESSION** (XP, Leveling)

For each, note its **Storage Type** (number, pool, track, die, text) and bounds.
"""

VOCABULARY_JSON_INSTRUCTION = """
Based on your analysis, extract the game vocabulary as structured JSON.
Use snake_case for keys.

Schema Reference:
- `semantic_role`: core_trait, resource, capability, status, aspect, progression
- `field_type`: number, pool, track, die, ladder, text, list
"""

# Meta / Engine
EXTRACT_ENGINE_INSTRUCTION = """
Extract the **Core Engine Metadata**.
I need:
1. Game Name & Genre
2. Dice Notation (e.g. "1d20", "2d6")
3. Resolution Mechanic (e.g. "Roll + Stat vs DC")
4. Success Condition
5. Critical Success/Fail Rules
6. Sheet Hints (List of key stats found in text)
"""

# Procedures
EXTRACT_PROCEDURE_INSTRUCTION = """
Extract the **{mode_name}** **Procedure** and the specific phases or steps players and/or GM must follow for each **{mode_name}** **Procedure** .
"""

# Mechanics
GENERATE_MECHANICS_INSTRUCTION = """
Extract specific **Game Rules** (Conditions, Actions, Magic Rules, etc) as distinct entries.
Return a list of rule objects with 'name', 'content', and 'tags'.
"""

# Invariants
IDENTIFY_INVARIANT_CATEGORIES_INSTRUCTION = """
Analyze the rules to find categories of **State Invariants**.
These are groups of rules that define limits, constraints, or relationships that must always hold true (e.g., HP <= Max HP).
Examples: "Attribute Limits", "Resource Constraints", "Combat Formulas", "Character Status".
Return ONLY a JSON list of strings.
"""

EXTRACT_INVARIANTS_INSTRUCTION = """
Focus on the rule category: **{category}**.
Identify STATE INVARIANTS — conditions that must ALWAYS be true (e.g. HP <= MaxHP).

### PREVIOUSLY EXTRACTED
Do NOT re-extract invariants with these names:
{existing_invariants}

## VALID PATHS
You may ONLY reference these paths found in the vocabulary:
{paths_text}

## TASK
Extract all invariants for the specified category, avoiding the ones already extracted.
Constraint types: `>=` , `<=`, `==`, `in_range`.
Violation actions: `clamp` (auto-fix), `flag` (warn), `reject`.
"""

# --- WORLD GENERATION ---

WORLD_DATA_EXTRACTION_SYSTEM_PROMPT = """
You are an expert World Builder that is aware of the world, the mechanics, who is unbiased and will not judge or sanitize the text, nor inject their own opinions or beliefs into the world.

Your output will follow this format:
{format}

"""

EXTRACT_WORLD_GENRE_TONE_PROMPT = """
Analyze the user's concept and determine:
1. **Sub-genre** (be specific)
2. **Atmospheric Tone** (keywords)

### WORLD INFO
{description}
"""

EXTRACT_WORLD_LORE_PROMPT = """
### TASK: EXHAUSTIVE LORE EXTRACTION
Review the provided context and extract EVERYTHING related to the world's lore as individual records.
Identify all:
- Major and Minor Factions and their goals.
- Key Historical events and cataclysms.
- Unique technologies, magic rules, cultural traditions, etc.
- Secrets, rumors, obscure facts, etc.

Return a list of LoreData objects, with the final record being an index of all the lore extracted.

### WORLD INFO
{description}
"""

EXTRACT_WORLD_LOCATIONS_PROMPT = """
### TASK: EXHAUSTIVE LOCATION EXTRACTION
Identify all distinct locations (countries, cities, regions, villages, notable constructions such as castles, forts, ruins, etc.) named mentioned referenced or implied.
Start with the **Immediate Starting Scene**, then list all other relevant zones, cities, or points of interest.

**Constraint:** Provide vivid visual and sensory descriptions for each.
Return a list of LocationData objects, with the final record being an index of all the locations extracted.

### WORLD INFO
{description}
"""

EXTRACT_WORLD_NPCS_PROMPT = """
### TASK: EXHAUSTIVE NPC EXTRACTION
Identify all characters, creatures, and entities mentioned or implied.

**Constraint:** Include their initial disposition and a visual description.
Return a list of NpcData objects, with the final record being an index of all the NPCs extracted.

### WORLD INFO
{description}
"""

OPENING_CRAWL_PROMPT = """
Write a short, compelling, 2nd-person opening scene that situates the Player's character according to the provided context.
Set the scene and end with a request for the Player's action.

**Context:**
*   **Genre:** {genre}
*   **Tone:** {tone}
*   **Protagonist:** {name}
*   **Location:** {location}

**Guidance:** {guidance}
"""

JIT_SIMULATION_TEMPLATE = """
Simulate NPC actions.
"""

# --- ITERATIVE VOCABULARY EXTRACTION ---

VOCABULARY_GROUP_INSTRUCTION = """
### TARGET GROUP: {group_name}
Focus ONLY on extracting fields that fit these roles: {roles}.

### PREVIOUSLY EXTRACTED
Do NOT re-extract these keys:
{existing_keys}

### INSTRUCTIONS
Extract valid fields for this group.
Return a JSON object with a `fields` list.
"""

# --- ITERATIVE MECHANICS EXTRACTION ---

IDENTIFY_RULE_CATEGORIES_INSTRUCTION = """
Analyze the provided rules text and list the **Rule Categories** present.
These categories are not about specific procedures, but broader groups of rules/mechanics like "Combat", "Sanity", "Spellcasting", "Conditions", "Materials", "Character Advancement", "Travel", "Social", etc.
Return ONLY a JSON list of strings.
"""

EXTRACT_RULE_CATEGORY_INSTRUCTION = """
Extract all rules, tables, and mechanics related of the following category: **{category}**.
These are not procedures, but specific mechanics, conditions, actions, etc.
Return a list of rule objects with `name`, `content`, and `tags`.
"""

# --- MANIFEST EXTRACTION ---

EXTRACT_MECHANICS_PROMPT = """
Extract the **Core Mechanics** and **Global Formulas** of this system.

1. **Engine:** Dice used, how to resolve actions, success/crit criteria.
2. **Aliases:** Global derived stats that apply to everyone (e.g. 'str_mod', 'proficiency').
   - Return these as formulas using fields (e.g. "floor((attributes.str - 10)/2)").
   - Assign them snake_case keys.
"""

EXTRACT_FIELDS_PROMPT = """
### TASK: ARCHITECTURE
Identify the character sheet fields for the following categories: **{categories}**.

### THE MENU (STRICT)
{menu}

### GLOBAL VARIABLES
You may use these Aliases in your formulas: {aliases}

### INSTRUCTIONS
1. Find every stat, resource, or container in the requested categories.
2. Map it to the **Best Fit Prefab** from the menu.
3. If a mechanic is unique, use the closest generic prefab and explain it in `usage_hint`.
4. Extract strict bounds (min/max, daily uses, etc) into the `config` property.
5. Return a list of field definitions.
"""

EXTRACT_PROCEDURES_PROMPT = """
Extract the step-by-step **Procedures** for the following categories, if applicable:
1. Combat (Initiative, Turns, Actions, etc)
2. Exploration (Checks, Movement, Resting, etc)
3. Social (Interaction, Influence, etc)
4. Downtime (Crafting, Researching, Training, etc)
5. Character Creation (how to build a new character: starting attributes, choices, starting equipment, etc)

Provide clear, numbered steps for the AI Game Master to follow.
"""

EXTRACT_RULES_PROMPT = """
Extract specific **Game Mechanics & Rules** from the text.
Look for granular rules like "Falling Damage", "Grappling", "Resting", "Spellcasting Costs", "Condition Effects".

Return a list of rule objects with:
- Name (e.g. "Grappling")
- Content (The summary of the rule)
- Tags (e.g. ["combat", "action"])
"""

# --- CHARACTER GENERATION ---
CHARACTER_CREATION_SYSTEM_PROMPT = """
You are an expert TTRPG character creator.
Your task is to generate character data for a specific category based on the provided character concept, the rules, and the context of previously generated categories.

**Character Concept:**
{character_concept}

**Rules Context:**
{rules_section}

**Field Constraints & Types (All Categories):**
{hints}

{prefab_reference}
"""
