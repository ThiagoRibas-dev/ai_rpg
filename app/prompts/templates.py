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
Write a short, compelling, 2nd-person opening scene that situates the Player's character.
Set the scene and end with a request for the Player's action.

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

# --- STATE INVARIANT EXTRACTION ---

EXTRACT_INVARIANTS_INSTRUCTION = """
Identify STATE INVARIANTS from the rules — conditions that must ALWAYS be true during gameplay.

Look for:
- Resource bounds (HP can't go below 0, Mana can't exceed max)
- Attribute limits (stats capped at certain values)
- Derived constraints (current value cannot exceed max)
- Range restrictions (values must be within specific ranges)

For each constraint, specify:
- name: Human-readable description
- target_path: Dot-path to the field (e.g., "resources.hp.current")
- constraint: The comparison (">=", "<=", "==", "in_range")
- reference: What to compare against (number like "0" or path like "resources.hp.max")
- on_violation: What to do ("clamp" = auto-fix, "flag" = warn only, "reject" = block)
- correction_value: If clamping, what value to use (optional, defaults to reference)

Common Examples:
{
  "name": "HP Floor",
  "target_path": "resources.hp.current",
  "constraint": ">=",
  "reference": "0",
  "on_violation": "clamp",
  "correction_value": "0"
},
{
  "name": "HP Ceiling",
  "target_path": "resources.hp.current",
  "constraint": "<=",
  "reference": "resources.hp.max",
  "on_violation": "clamp",
  "correction_value": "resources.hp.max"
}

Extract 3-10 invariants appropriate for this game system.
"""

# =============================================================================
# VOCABULARY EXTRACTION PROMPTS
# =============================================================================

VOCABULARY_ANALYSIS_PROMPT = """
You are an expert TTRPG system analyst. Your task is to analyze a ruleset and identify its mechanical building blocks.

Read the rules carefully and identify:

1. **CORE TRAITS** — Primary character statistics that define capabilities
   - D&D: Ability Scores (Strength, Dexterity, etc.)
   - Fate: Approaches (Careful, Clever, etc.) or Skills
   - PbtA: Stats (Cool, Hard, Hot, Sharp, Weird)
   - Kids on Bikes: Stats as die types (Brains d8, Brawn d4)

2. **RESOURCES** — Values that get depleted and recovered
   - D&D: Hit Points, Spell Slots
   - Fate: Stress (track), Fate Points (number)
   - Call of Cthulhu: HP, Sanity, Luck

3. **CAPABILITIES** — Skills, proficiencies, or special abilities
   - D&D: Skills (Athletics, Stealth), Proficiencies
   - Fate: Stunts
   - PbtA: Moves

4. **STATUS** — Temporary conditions or states
   - D&D: Conditions (Poisoned, Stunned, Prone)
   - Fate: Consequences, Boosts
   - Generic: Wounded, Exhausted, Inspired

5. **ASPECTS** — Narrative truths that affect gameplay
   - Fate: High Concept, Trouble, other Aspects
   - Beliefs, Instincts, Goals

6. **PROGRESSION** — How characters advance
   - D&D: Level, XP
   - Fate: Milestones, Refresh
   - PbtA: Advancements

For each field, determine:
- **Storage Type**: How is the data structured?
  - `number`: Simple integer (Strength: 16, Level: 5)
  - `pool`: Current/Max pair (HP: 24/30)
  - `track`: Checkbox array (Stress: ☐☐☒☒)
  - `die`: Die notation (Brains: d8)
  - `ladder`: Named rating (Careful: Good +3)
  - `tag`: Narrative text (Aspect: "Former Soldier")
  - `text`: Free-form text
  - `list`: Array of items

- **Bounds**: What are the minimum/maximum values?
- **Relationships**: Does this derive from or govern other fields?

Analyze the provided rules text thoroughly.
"""

VOCABULARY_EXTRACTION_PROMPT = """
Based on your analysis, extract the game vocabulary as structured JSON.

## FIELD TYPES
- `number`: Simple integer value
- `pool`: Has current and max values  
- `track`: Array of checkboxes
- `die`: Stores a die type (d4, d8, d12)
- `ladder`: Rating with labels (Fate-style)
- `tag`: Narrative text
- `text`: Free-form string
- `list`: Collection of items

## SEMANTIC ROLES
- `core_trait`: Primary stats
- `resource`: Depletable values
- `capability`: Skills, abilities
- `status`: Temporary conditions
- `aspect`: Narrative truths
- `progression`: XP, level
- `equipment`: Gear, inventory
- `connection`: Relationships

Use snake_case for all keys. Be thorough — extract ALL mechanical elements.
"""

