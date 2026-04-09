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
Identify STATE INVARIANTS - conditions that must ALWAYS be true (e.g. HP <= MaxHP).

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
You are an expert World Builder and Game Master who is aware of the world, the mechanics, and is unbiased and will not judge or sanitize the text, nor inject their own opinions or beliefs into the world.

## CORE PRINCIPLES
1. **Extraction Only**: Your goal is to extract, organize, connect, and sometimes extrapolate data from the provided Source Material.
2. **Contextual Awareness**: When provided with a list of already recorded entries (Reference Context), use that list to ensure logical consistency and to build connections instead of returning the same information again.
3. **No Redundancy**: NEVER repeat or re-extract information that is already listed in the Reference Context. Focus exclusively on discovering NEW details from the Source Material.
4. **Atomicity (One Entity = One Record)**: Do not fragment information about a single entity into multiple entries. Each entry must be self-contained and include all relevant sub-details found in the material.

### SOURCE MATERIAL
{description}

Your output will follow this format:

### OUTPUT FORMAT
{format}
"""

EXTRACT_WORLD_GENRE_TONE_PROMPT = """
Analyze the source material and determine:
1. **Sub-genre** (be specific, e.g. 'Epic Fantasy', 'Cyberpunk Noir').
2. **Atmospheric Tone** (keywords, e.g. 'grim', 'hopeful', 'mysterious').
"""

EXTRACT_WORLD_INDEX_PROMPT = """
Create a comprehensive list indexing every unique Location, NPC, and significant information (Lore) entry of the provided source material, taking care to avoid duplicating information.
For example, a city should not be listed as location, culture, and a faction.

For each item/entry, determine its Type according to these rules:

1. **location**: Physical sites, settlements, countries, nations, cities, towns, villages, geographic landmarks, notable structures or buildings, etc.
2. **npc**: Specific named individuals, unique legendary creatures, or distinct characters.
3. **systems**: Foundational laws of reality (Magic, Tech, Physics) and Cosmology (Deities, Planes).
4. **races**: Biological species, lineages, ancestries, and their traits.
5. **factions**: Organizations, religions (as institutions), guilds, military orders, governments, or political entities.
6. **history**: Named historical events, eras, wars, cataclysms, timelines, and other such historical events.
7. **culture**: Social norms, traditions, daily life, folklore, and etiquette.
8. **status**: Current rumors, active local conflicts, impending threats, or plot hooks.
9. **misc**: Anything elses significant that does not fit into the above buckets.


Return a JSON list of objects with 'name' and 'type' of each entry, E.g.
```json
[
    {
        "name": "The Shire",
        "type": "location"
    },
    {
        "name": "Frodo Baggins",
        "type": "npc"
    },...
]
```
and so on.

"""

EXTRACT_WORLD_DETAILS_PROMPT = """
You are extracting detailed records for the following WORLD ENTITIES of type: **{type}**.

### TARGET ENTITIES
Extract full, exhaustive records for only these specific entities:
{names}

## INSTRUCTIONS
- If type is **LOCATION**: Focus on 'description_visual', 'description_sensory', and 'type' (indoor/outdoor/etc).
- If type is **NPC**: Focus on 'visual_description', 'stat_template' (Civilian/Warrior/etc), and 'initial_disposition'.
- If type is any **LORE** category (Systems, Races, Factions, etc): Extract the 'name' and the 'content' for the entry. The 'content' should be a detailed paragraph describing it within the context of the world.

Do NOT extract entities not listed in the TARGET ENTITIES list.
Ensure each entry is self-contained and descriptive.
"""

OPENING_CRAWL_PROMPT = """
Write a short, compelling, 2nd-person opening scene that situates the Player's character according to the provided context, unless the User provides their own opening scene.
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
Extract the **System Metadata**, **Core Mechanics**, and **Global Formulas** of this system.

1. **System Name:** Official or most common published name of the game/system.
2. **Engine:** Primary dice used, how to resolve actions, success criteria, critical rules, and fumble rules.
3. **Aliases:** Global derived stats that apply to everyone (e.g. 'str_mod', 'proficiency').

### FORMULA RULES
- Assign aliases snake_case keys.
- Formulas must reference the actual stored field shape.
- If a trait is represented as a score+modifier object, reference the numeric score as `.score`
  (e.g. "(attributes.str.score - 10) / 2", not "attributes.str").
- Prefer concise reusable formulas that later field extraction can reference.
- Do not invent aliases unless they are broadly applicable across most characters in the system.
"""

EXTRACT_FIELDS_PROMPT = """
We are building the architecture of the character sheet, and I need you to identify the structured fields for the following categories: **{categories}**.

### THE MENU (STRICT)
{menu}

### GLOBAL VARIABLES
You may use these Aliases in your formulas: {aliases}

### INSTRUCTIONS
1. Find every stat, resource, or container in the requested categories.
2. Map each field to the **Best Fit Prefab** from the menu.
3. If a mechanic is unique, use the closest generic prefab and explain it clearly in `usage_hint`.
4. Extract strict bounds (min/max, daily uses, etc) into the `config` property.
5. When writing formulas, reference the actual stored field shape.
   - Example: for a compound attribute field, use `attributes.str.score` if you need the numeric score.
6. Do NOT return fields outside the requested categories.
7. Return a single JSON object with a `fields` list.
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
You are an expert **Game Master and Character Creator**.
Your goal is to extract and generate character data based on the provided character sheet and rules.

## CORE PRINCIPLES
1. **Source Fidelity**: Extract data precisely as it appears in the Provided Character Sheet.
2. **Rules Adherence**: Ensure all values, bonuses, and prerequisites follow the Game Rules.
3. **Consistency**: Ensure the generated data is internally consistent and follows the established character concept.

## SOURCES
### Character Sheet (Provided Text)
{character_sheet}

### Game Rules & Mechanics
{rules_section}

{prefab_reference}
"""

EXTRACT_CHARACTER_BATCH_PROMPT = """
Analyze the provided character sheet and extract information for the following categories: **{branch_cats_str}** ({branch_name}).

## FIELD CONSTRAINTS & HINTS
{hints}

## PREVIOUS PROGRESS
Below is the data already extracted for this character. Use it to ensure consistency (e.g., skill bonuses matching attribute modifiers).
```json
{ctx_snap}
```

## TARGET CATEGORIES
You must generate data for these categories: {branch_cats_str}.
Ensure the output is a single valid JSON matching the schema, with NO extra text.
"""
