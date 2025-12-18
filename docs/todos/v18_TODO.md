TODO CHecklist of our current tasks : 
```
# Implementation Checklist: Prefab System v2

## Functional Specification & TODO

---

## Overview

This document specifies the "Lego Protocol" implementation—transitioning from generative AI architecture to selective AI configuration.

### Core Insight

| Layer | What AI Does | What Code Does |
|-------|--------------|----------------|
| **Vocabulary** | Classifies fields into prefabs | Validates data shapes |
| **Invariants** | Nothing (implicit in prefabs) | Clamps values, evaluates formulas |
| **Mechanics** | Interprets rules, narrates outcomes | Provides `roll` tool |
| **Procedures** | Follows text guidelines | Nothing (pure prompt context) |

### Prefab Catalog (Derived from 17-Game Analysis)

**Tier 1: Essential (8 prefabs)**

| ID | Family | Shape | Games Using |
|----|--------|-------|-------------|
| `VAL_INT` | Value | `int` | 10+ (universal) |
| `VAL_COMPOUND` | Value | `{score: int, mod: int}` | D&D, Pathfinder |
| `VAL_STEP_DIE` | Value | `str` (d4-d12) | Savage Worlds, KoB, T2000 |
| `RES_POOL` | Resource | `{current: int, max: int}` | 15+ (HP, Mana, Sanity) |
| `RES_COUNTER` | Resource | `int` | 10+ (XP, Gold, Fate Points) |
| `RES_TRACK` | Resource | `[bool, ...]` | 12+ (Stress, Wounds, Death Saves) |
| `CONT_LIST` | Container | `[{...}, ...]` | 17 (Inventory, Abilities) |
| `CONT_TAGS` | Container | `[str, ...]` | 8 (Languages, Proficiencies) |

**Tier 2: Common Extensions**

| ID | Family | Shape | When Needed |
|----|--------|-------|-------------|
| `VAL_LADDER` | Value | `{value: int, label: str}` | Fate, Castle Falkenstein |
| `VAL_BOOL` | Value | `bool` | Simple toggles |
| `CONT_WEIGHTED` | Container | `[{..., weight: int}]` | GURPS, PF encumbrance |

### Invariant Strategy

| Type | Frequency | Implementation |
|------|-----------|----------------|
| **Structural** | Every field | Built into prefab validator |
| **Bounded** | 90% of fields | `config: {min, max}` |
| **Cross-field** | 30% of fields | `max_formula: "level + 3"` |
| **Derived** | 20% of fields | `formula: "floor((str - 10) / 2)"` |
| **Threshold** | 70% of tracks | `threshold_hint:` (prompt text) |
| **Inverse** | 2 games | `threshold_hint:` (prompt text) |

### Tool Reduction

| Current (11 tools) | Proposed (6 tools) |
|--------------------|--------------------|
| EntityUpdate | → `adjust`, `set` |
| GameRoll | → `roll` |
| WorldTravel | → `move` |
| GameLog, MemoryUpsert | → `note` |
| TimeAdvance | → `set` (on time path) |
| InventoryAddItem | → `set` (on list path) |
| StateQuery | Keep for debug only |
| NpcSpawn, LocationCreate | Setup-only tools |

---

## Task 1: Define the Prefab Catalog

### What

Create the Python module containing:
- `Prefab` dataclass (id, family, shape, validate, widget, ai_hint)
- 8 core prefab definitions with validator functions
- 3 extended prefabs for common edge cases

### Why

Prefabs are the atomic building blocks. A prefab bundles:
1. **Data shape** — What the JSON looks like
2. **Validator** — How to clamp/correct invalid data
3. **Widget hint** — How UI should render it
4. **AI hint** — One-line explanation for prompts

By selecting a prefab, you get all four for free. No extraction, no hallucination.

### File Structure

```
app/prefabs/
├── __init__.py          # Exports PREFABS dict, Prefab class
├── registry.py          # Prefab definitions
└── validators.py        # Validator functions (pure, testable)
```

### Subtasks

- [ ] **1.1 Create `app/prefabs/` package structure**
  - Create directory with `__init__.py`
  - Export `PREFABS: Dict[str, Prefab]`
  - Export `Prefab` dataclass

- [ ] **1.2 Define `Prefab` dataclass**
  ```python
  @dataclass
  class Prefab:
	  id: str                                  # "RES_POOL"
	  family: Literal["VAL", "RES", "CONT"]   # For categorization
	  shape: Any                               # Example structure for docs
	  validate: Callable[[Any, Dict], Any]    # (value, config) -> corrected_value
	  widget: str                              # UI hint: "progress_bar"
	  ai_hint: str                             # <100 chars, action-oriented
  ```

- [ ] **1.3 Implement VALUE validators**

  | Prefab | Validator Logic | Config Options |
  |--------|-----------------|----------------|
  | `VAL_INT` | Clamp to `[min, max]`, default 0 | `min`, `max`, `default` |
  | `VAL_COMPOUND` | Validate score, compute modifier | `min`, `max`, `mod_formula` |
  | `VAL_STEP_DIE` | Must be in chain | `chain: ["d4","d6","d8","d10","d12"]` |
  | `VAL_LADDER` | Clamp value, lookup label | `min`, `max`, `labels: {0: "Terrible", ...}` |
  | `VAL_BOOL` | Coerce to boolean | — |

- [ ] **1.4 Implement RESOURCE validators**

  | Prefab | Validator Logic | Config Options |
  |--------|-----------------|----------------|
  | `RES_POOL` | Ensure `current ≤ max`, `current ≥ min` | `min` (default 0), `default_max` |
  | `RES_COUNTER` | Clamp to `≥ min` (usually 0) | `min` (default 0) |
  | `RES_TRACK` | Pad/truncate to length, all bools | `length` |

- [ ] **1.5 Implement CONTAINER validators**

  | Prefab | Validator Logic | Config Options |
  |--------|-----------------|----------------|
  | `CONT_LIST` | Ensure list, preserve items | — |
  | `CONT_TAGS` | Ensure list of strings | — |
  | `CONT_WEIGHTED` | Ensure list, validate weight field | `capacity_path` (optional) |

- [ ] **1.6 Write AI hints for each prefab**

  Requirements:
  - Under 100 characters
  - Action-oriented (what tools to use)
  - Include data shape hint

  Examples:
  ```
  VAL_INT: "Simple number. Use 'adjust' to add/subtract, 'set' to replace."
  RES_POOL: "Has current/max. Adjust 'path.current' for damage/healing. Auto-clamped."
  RES_TRACK: "Sequential boxes. Use 'mark' to fill, 'mark' with negative to clear."
  ```

- [ ] **1.7 Add `get_default(config)` function to each prefab**

  | Prefab | Default Value |
  |--------|---------------|
  | `VAL_INT` | `config.get("default", 0)` |
  | `VAL_COMPOUND` | `{"score": default, "mod": computed}` |
  | `RES_POOL` | `{"current": max, "max": max}` |
  | `RES_TRACK` | `[False] * length` |
  | `RES_COUNTER` | `0` |
  | `CONT_LIST` | `[]` |
  | `CONT_TAGS` | `[]` |

- [ ] **1.8 Write unit tests for validators**

  Test cases per prefab:
  - None input → sensible default
  - Wrong type → coerced or default
  - Out of bounds → clamped
  - Valid input → unchanged
  - Edge cases (empty list, zero, negative)

### Acceptance Criteria

- [ ] `from app.prefabs import PREFABS` returns dict of 8+ prefabs
- [ ] Each validator handles garbage input without raising exceptions
- [ ] Each AI hint is under 100 characters
- [ ] All unit tests pass

---

## Task 2: Create Manifest Data Structures

### What

Define the data structures for system manifests:
- `FieldDef` — Single field definition with prefab binding
- `EngineConfig` — Resolution mechanics (prompt context)
- `SystemManifest` — Complete game system definition

### Why

Manifests replace both `GameVocabulary` and `StateInvariant` extraction. A manifest is:
- **Complete** — All fields, formulas, and hints in one place
- **Static** — No LLM generation needed for known systems
- **Portable** — JSON files that can be shared

### File Structure

```
app/prefabs/
├── manifest.py          # Dataclass definitions
└── formula.py           # Formula evaluation engine
```

### Subtasks

- [ ] **2.1 Define `FieldDef` dataclass**

  ```python
  @dataclass
  class FieldDef:
	  # Required
	  path: str                    # "resources.hp"
	  label: str                   # "Hit Points"
	  prefab: str                  # "RES_POOL"
	  category: str                # "resources"
	  
	  # Prefab configuration
	  config: Dict[str, Any] = field(default_factory=dict)
	  
	  # Formula support (optional)
	  formula: Optional[str] = None        # Derived value (read-only)
	  max_formula: Optional[str] = None    # For pool max computation
	  default_formula: Optional[str] = None # Starting value
	  
	  # AI context hints (optional)
	  threshold_hint: Optional[str] = None  # "At 0: unconscious"
	  usage_hint: Optional[str] = None      # "Spend to boost rolls"
  ```

- [ ] **2.2 Define `EngineConfig` dataclass**

  ```python
  @dataclass
  class EngineConfig:
	  dice: str              # "1d20", "2d6", "d100"
	  mechanic: str          # "Roll + Mod vs DC"
	  success: str           # "Meet or beat target"
	  crit: str              # "Natural 20 = auto-hit + double damage"
	  fumble: str = ""       # "Natural 1 = auto-miss"
  ```

- [ ] **2.3 Define `SystemManifest` dataclass**

  ```python
  @dataclass
  class SystemManifest:
	  # Identity
	  id: str                         # "dnd_5e"
	  name: str                       # "D&D 5th Edition"
	  
	  # Resolution (injected into prompts)
	  engine: EngineConfig
	  
	  # Procedures by game mode (injected into prompts)
	  procedures: Dict[str, str]      # {"combat": "...", "exploration": "..."}
	  
	  # Field definitions
	  fields: List[FieldDef]
	  
	  # Formula aliases (shortcuts for common calculations)
	  aliases: Dict[str, str] = field(default_factory=dict)
	  
	  # Utility methods
	  def get_field(self, path: str) -> Optional[FieldDef]: ...
	  def get_fields_by_category(self, category: str) -> List[FieldDef]: ...
	  def get_all_paths(self) -> List[str]: ...
  ```

- [ ] **2.4 Implement formula evaluation**

  ```python
  # app/prefabs/formula.py
  
  def evaluate(formula: str, context: Dict[str, Any]) -> float:
	  """
	  Evaluate formula against flattened entity context.
	  
	  Supports:
	  - Arithmetic: +, -, *, /, //, %
	  - Functions: floor(), ceil(), max(), min()
	  - Paths: attributes.str, progression.level
	  - Aliases: str_mod (pre-resolved)
	  """
  ```

  Requirements:
  - Use `simpleeval` for safe evaluation
  - Replace dots with underscores for valid Python identifiers
  - Return 0 on any error (no exceptions)
  - Support: `floor`, `ceil`, `max`, `min`

- [ ] **2.5 Implement manifest validation**

  ```python
  def validate_manifest(manifest: SystemManifest) -> List[str]:
	  """Return list of validation errors, empty if valid."""
  ```

  Checks:
  - All `prefab` values exist in PREFABS
  - All `category` values are valid
  - All paths are unique
  - All formula references exist (fields or aliases)
  - Required config present for each prefab type

- [ ] **2.6 Implement manifest serialization**

  ```python
  def manifest_to_json(manifest: SystemManifest) -> str: ...
  def manifest_from_json(json_str: str) -> SystemManifest: ...
  def manifest_from_file(path: Path) -> SystemManifest: ...
  ```

### Acceptance Criteria

- [ ] `FieldDef`, `EngineConfig`, `SystemManifest` dataclasses defined
- [ ] Formula evaluator handles all test cases
- [ ] Manifest round-trips through JSON without data loss
- [ ] Validation catches common errors

---

## Task 3: Create Example Manifests

### What

Hand-author complete manifests for 3-4 popular systems:
- D&D 5th Edition (d20, most popular)
- Call of Cthulhu 7e (d100, different engine)
- Blades in the Dark (dice pool, track-heavy)
- Fate Core (optional, ladder + aspects)

### Why

1. **Validates prefab coverage** — If D&D doesn't fit, prefabs are wrong
2. **Provides instant value** — Zero LLM cost for popular systems
3. **Serves as few-shot examples** — Template for AI classification

### File Structure

```
app/data/manifests/
├── dnd_5e.json
├── coc_7e.json
├── bitd.json
└── fate_core.json (optional)
```

### Subtasks

- [ ] **3.1 Create D&D 5e manifest**

  Fields to include:
  
  | Category | Fields |
  |----------|--------|
  | attributes | STR, DEX, CON, INT, WIS, CHA (VAL_INT, 1-30) |
  | resources | HP (RES_POOL), Hit Dice (RES_POOL), Spell Slots ×9 (RES_POOL) |
  | status | Death Save Success/Failure (RES_TRACK, length 3) |
  | combat | AC (VAL_INT, derived), Initiative (VAL_INT, derived) |
  | progression | Level (VAL_INT, 1-20), XP (RES_COUNTER) |
  | inventory | Equipment (CONT_LIST) |
  | features | Proficiencies (CONT_TAGS), Features (CONT_LIST) |

  Aliases:
  ```json
  {
	"str_mod": "floor((attributes.str - 10) / 2)",
	"proficiency": "ceil(progression.level / 4) + 1"
  }
  ```

  Engine:
  ```json
  {
	"dice": "1d20",
	"mechanic": "Roll d20 + modifier vs Difficulty Class",
	"success": "Total meets or beats DC",
	"crit": "Natural 20 on attack = auto-hit + double damage dice",
	"fumble": "Natural 1 on attack = auto-miss"
  }
  ```

- [ ] **3.2 Create Call of Cthulhu 7e manifest**

  Fields to include:

  | Category | Fields |
  |----------|--------|
  | attributes | STR, CON, SIZ, DEX, APP, INT, POW, EDU (VAL_INT, 1-99) |
  | resources | HP, MP, Sanity (RES_POOL), Luck (RES_COUNTER) |
  | skills | Core skills: ~15-20 common ones (VAL_INT, 0-99) |
  | features | Phobias, Manias (CONT_TAGS) |
  | inventory | Equipment (CONT_LIST) |

  Special:
  - `max_formula` for HP: `floor((attributes.con + attributes.siz) / 10)`
  - `max_formula` for Sanity: `99 - skills.cthulhu_mythos`
  - `threshold_hint` for Sanity: "Lose 5+ at once: temporary insanity"

  Engine:
  ```json
  {
	"dice": "1d100",
	"mechanic": "Roll d100 vs skill value",
	"success": "Roll ≤ skill (Regular), ≤ half (Hard), ≤ fifth (Extreme)",
	"crit": "01 is always critical success",
	"fumble": "96-100 if skill < 50, 100 always fumble"
  }
  ```

- [ ] **3.3 Create Blades in the Dark manifest**

  Fields to include:

  | Category | Fields |
  |----------|--------|
  | actions | 12 actions (VAL_INT, 0-4): Hunt, Study, Survey, Tinker, Finesse, Prowl, Skirmish, Wreck, Attune, Command, Consort, Sway |
  | attributes | Insight, Prowess, Resolve (VAL_INT, derived from action counts) |
  | resources | Stress (RES_TRACK, 9), Trauma (RES_TRACK, 4) |
  | harm | Level 1, 2, 3 Harm (RES_TRACK, lengths 2, 2, 1) |
  | status | Armor, Heavy Armor (VAL_BOOL) |
  | features | Abilities (CONT_LIST) |

  Engine:
  ```json
  {
	"dice": "d6 pool",
	"mechanic": "Roll Action Rating in d6s, read highest die",
	"success": "6 = full success, 4-5 = partial, 1-3 = bad outcome",
	"crit": "Multiple 6s = critical (enhanced effect)"
  }
  ```

  Threshold hints:
  - Stress: "All 9 filled → take Trauma, clear Stress"
  - Trauma: "At 4 → character retires"

- [ ] **3.4 Create Fate Core manifest (optional)**

  Fields to include:

  | Category | Fields |
  |----------|--------|
  | approaches | Careful, Clever, Flashy, Forceful, Quick, Sneaky (VAL_LADDER, -1 to +4) |
  | resources | Physical Stress, Mental Stress (RES_TRACK, 2-4), Fate Points (RES_COUNTER) |
  | consequences | Mild, Moderate, Severe (CONT_TAGS or VAL_TEXT) |
  | features | Stunts (CONT_LIST) |
  | narrative | Aspects (CONT_TAGS, 5 aspects) |
  | progression | Refresh (VAL_INT) |

  Engine:
  ```json
  {
	"dice": "4dF",
	"mechanic": "Roll 4 Fate dice + Approach vs opposition",
	"success": "Meet or beat = success, +3 over = succeed with style",
	"crit": "Succeed with style grants boost"
  }
  ```

- [ ] **3.5 Validate all manifests load correctly**

  - Run `manifest_from_file()` on each
  - Run `validate_manifest()` on each
  - Verify all paths are unique
  - Verify all prefab IDs exist

- [ ] **3.6 Create manifest index**

  ```json
  // app/data/manifests/index.json
  {
	"builtin": [
	  {"id": "dnd_5e", "name": "D&D 5th Edition", "file": "dnd_5e.json"},
	  {"id": "coc_7e", "name": "Call of Cthulhu 7e", "file": "coc_7e.json"},
	  {"id": "bitd", "name": "Blades in the Dark", "file": "bitd.json"}
	]
  }
  ```

### Acceptance Criteria

- [ ] Each manifest loads without validation errors
- [ ] Each manifest covers ≥80% of core character sheet fields
- [ ] Formulas evaluate correctly with sample data
- [ ] All prefab IDs used exist in PREFABS

---

## Task 4: Rewrite Tool Schemas

### What

Replace current 11 complex tools with 6 atomic operations:
- `adjust` — Add/subtract from number
- `set` — Set any value directly
- `roll` — Roll dice
- `mark` — Fill/clear track boxes
- `move` — Change location
- `note` — Create memory entry

### Why

Current tools like `EntityUpdate` have multiple optional fields:
```python
adjustments: Optional[Dict]  # Relative
updates: Optional[Dict]       # Absolute
inventory: Optional[Dict]     # Items
```

Small models can't reliably choose between these. Atomic tools have **one purpose each**.

### File Structure

```
app/tools/
├── schemas.py           # 6 tool Pydantic models
├── handlers/
│   ├── adjust.py
│   ├── set.py
│   ├── roll.py
│   ├── mark.py
│   ├── move.py
│   └── note.py
└── executor.py          # Simplified dispatch
```

### Subtasks

- [ ] **4.1 Define `Adjust` tool**

  ```python
  class Adjust(BaseModel):
	  """Add or subtract from a numeric value."""
	  name: Literal["adjust"] = "adjust"
	  path: str = Field(..., description="Full path like 'resources.hp.current'")
	  delta: int = Field(..., description="Amount to add (negative to subtract)")
	  reason: str = Field("", description="Brief reason for the change")
  ```

  Handler behavior:
  - Get current value at path
  - Add delta
  - Look up field's prefab from manifest
  - Validate through prefab (clamp pool to max, etc.)
  - Return `{path, old, new, delta}`

- [ ] **4.2 Define `Set` tool**

  ```python
  class Set(BaseModel):
	  """Set a field to a specific value."""
	  name: Literal["set"] = "set"
	  path: str = Field(..., description="Full path to field")
	  value: Any = Field(..., description="New value")
  ```

  Handler behavior:
  - Set value at path
  - Validate through prefab
  - Return `{path, old, new}`

- [ ] **4.3 Define `Roll` tool**

  ```python
  class Roll(BaseModel):
	  """Roll dice and report result."""
	  name: Literal["roll"] = "roll"
	  formula: str = Field(..., description="Dice notation: '1d20+5', '2d6', '4dF'")
	  reason: str = Field(..., description="What this roll is for")
  ```

  Handler behavior:
  - Parse formula (handle: NdX, NdX+M, NdX-M, dX)
  - Generate random results
  - Return `{formula, rolls, modifier, total, reason}`

- [ ] **4.4 Define `Mark` tool**

  ```python
  class Mark(BaseModel):
	  """Mark or clear boxes on a track."""
	  name: Literal["mark"] = "mark"
	  path: str = Field(..., description="Path to track field")
	  count: int = Field(1, description="Boxes to mark (negative to clear)")
  ```

  Handler behavior:
  - Get track array
  - Mark from left (positive) or clear from right (negative)
  - Return `{path, marked, total_filled, total_length}`

- [ ] **4.5 Define `Move` tool**

  ```python
  class Move(BaseModel):
	  """Move to a different location."""
	  name: Literal["move"] = "move"
	  destination: str = Field(..., description="Location key to move to")
  ```

  Handler behavior:
  - Update scene location
  - Update character location_key
  - Return `{destination, location_name, description}`

- [ ] **4.6 Define `Note` tool**

  ```python
  class Note(BaseModel):
	  """Record an important event or fact."""
	  name: Literal["note"] = "note"
	  content: str = Field(..., description="What to remember")
	  kind: Literal["event", "fact", "lore"] = Field("event")
  ```

  Handler behavior:
  - Create memory in database
  - Index in vector store
  - Return `{id, kind, content}`

- [ ] **4.7 Create unified executor**

  ```python
  def execute(tool: BaseModel, ctx: ExecutionContext) -> dict:
	  """Single dispatcher for all tools."""
	  # Simple if/elif on type
	  # Each branch calls handler function
	  # All handlers receive ctx with: session_id, db, manifest, entity
  ```

- [ ] **4.8 Integrate prefab validation into handlers**

  For `Adjust` and `Set`:
  ```python
  field_def = manifest.get_field(path)
  if field_def:
	  prefab = PREFABS[field_def.prefab]
	  value = prefab.validate(value, field_def.config)
  ```

- [ ] **4.9 Update tool registry**

  - Register only the 6 new tools for gameplay
  - Keep `StateQuery` for debug (not in active tool list)
  - Keep `NpcSpawn`, `LocationCreate` for setup phase only

- [ ] **4.10 Delete deprecated tool files**

  Remove or archive:
  - `entity_update.py`
  - `inventory_add_item.py`
  - `time_advance.py` (merge into `set`)
  - `game_log.py` (replaced by `note`)

### Acceptance Criteria

- [ ] 6 tool schemas defined with <50 word descriptions
- [ ] Each handler is <30 lines of code
- [ ] Prefab validation applied in `adjust` and `set`
- [ ] All existing test scenarios covered by new tools

---

## Task 5: Update Context Builder

### What

Modify context generation to use manifests instead of vocabulary:
- Path hints from manifest fields (not extracted vocabulary)
- Tool examples section (critical for small models)
- Compact state rendering using prefab widgets
- Engine/procedures injected by game mode

### Why

Current context pulls from multiple sources (vocabulary, invariants, state). With manifests:
- Paths are explicit (no derivation)
- Invariants are implicit (no explanation needed)
- State renders using prefab widget hints
- Engine/procedures are plain text injection

Target: <2000 tokens for dynamic context.

### File Changes

```
app/context/
├── context_builder.py   # Major update
└── state_context.py     # Simplify using prefabs
```

### Subtasks

- [ ] **5.1 Add manifest to context pipeline**

  ```python
  class ContextBuilder:
	  def __init__(self, ..., manifest: SystemManifest = None):
		  self.manifest = manifest
  ```

- [ ] **5.2 Generate path hints from manifest**

  ```python
  def _build_path_hints(self) -> str:
	  """
	  # VALID PATHS
	  
	  **Resources:**
		`resources.hp.current` - Hit Points (current/max pool)
		`resources.stress` - Stress (9 boxes, mark to fill)
	  
	  **Attributes:**
		`attributes.str` - Strength (1-30)
	  """
  ```

  Format per field:
  - Path in backticks
  - Label
  - Prefab AI hint (parenthetical)

- [ ] **5.3 Add tool examples section**

  **Critical for small models.** Include 4-5 concrete examples:

  ```python
  TOOL_EXAMPLES = """
  # TOOL EXAMPLES
  
  Deal 5 damage:
  {"name": "adjust", "path": "resources.hp.current", "delta": -5, "reason": "Goblin attack"}
  
  Heal 3 HP:
  {"name": "adjust", "path": "resources.hp.current", "delta": 3, "reason": "Potion"}
  
  Attack roll:
  {"name": "roll", "formula": "1d20+5", "reason": "Longsword vs AC 15"}
  
  Mark 2 stress:
  {"name": "mark", "path": "resources.stress", "count": 2}
  
  Move location:
  {"name": "move", "destination": "loc_tavern"}
  
  Remember fact:
  {"name": "note", "content": "The baron is secretly a vampire", "kind": "fact"}
  """
  ```

- [ ] **5.4 Update state rendering**

  Render based on prefab widget:

  | Prefab | Render Format |
  |--------|---------------|
  | `RES_POOL` | `HP: 23/45` |
  | `RES_TRACK` | `Stress: ●●●●○○○○○` |
  | `RES_COUNTER` | `XP: 1250` |
  | `VAL_INT` | `STR: 18` |
  | `VAL_COMPOUND` | `STR: 18 (+4)` |
  | `VAL_STEP_DIE` | `Fight: d8` |
  | `VAL_LADDER` | `Careful: +2 (Fair)` |

- [ ] **5.5 Inject engine config**

  At top of context:
  ```
  # GAME SYSTEM: D&D 5th Edition
  
  **Dice:** 1d20
  **Resolution:** Roll d20 + modifier vs Difficulty Class
  **Success:** Meet or beat DC
  **Critical:** Natural 20 = auto-hit + double damage dice
  ```

- [ ] **5.6 Inject active procedure**

  Based on `game_session.game_mode`:
  ```python
  if game_mode == "combat":
	  context += f"\n# COMBAT PROCEDURE\n{manifest.procedures['combat']}"
  ```

- [ ] **5.7 Reduce overall context size**

  Targets:
  - State summary: <500 tokens
  - Path hints: <300 tokens
  - Tool examples: <200 tokens
  - Engine + procedure: <300 tokens
  - Total dynamic: <1500 tokens (leave room for history)

- [ ] **5.8 Fallback for legacy sessions**

  If `manifest` is None:
  ```python
  if self.manifest:
	  return self._build_manifest_context(...)
  else:
	  return self._build_legacy_context(...)  # Current behavior
  ```

### Acceptance Criteria

- [ ] Context includes path hints with prefab descriptions
- [ ] Context includes 4+ tool examples
- [ ] State renders pools as "current/max", tracks as dots
- [ ] Total dynamic context <2000 tokens
- [ ] Legacy sessions still work

---

## Task 6: Write Classifier Prompt

### What

Create the LLM prompts for classifying rulebook mechanics into prefab selections:
- Prefab reference (what each type means)
- Classification instructions (what to output)
- Few-shot examples (complete input→output)
- Multi-shot structure (for small models)

### Why

Current extraction asks AI to **generate** structures. Classification asks AI to **select** from a menu. This is multiple choice vs. essay—dramatically better accuracy on small models.

### File Structure

```
app/prompts/
├── classifier.py        # Classification prompts
└── templates.py         # Updated (remove generative prompts)

app/setup/
└── manifest_extractor.py  # New extraction using classification
```

### Subtasks

- [ ] **6.1 Write prefab reference section**

  Clear, concise descriptions of each prefab:

  ```
  ## PREFAB TYPES
  
  ### Values (rarely change)
  - VAL_INT: Simple number with optional min/max.
	Examples: Strength, Level, Armor Class
  
  - VAL_COMPOUND: Score + derived modifier.
	Examples: D&D Attributes (18 → +4)
  
  - VAL_STEP_DIE: Die type from a chain.
	Examples: Savage Worlds Traits (d4→d6→d8→d10→d12)
  
  ### Resources (fluctuate during play)
  - RES_POOL: Current and maximum values.
	Examples: Hit Points, Mana, Sanity
  
  - RES_TRACK: Sequential boxes to fill.
	Examples: Stress, Death Saves, Wound Levels
  
  - RES_COUNTER: Simple counter, no maximum.
	Examples: XP, Gold, Fate Points
  
  ### Containers (lists)
  - CONT_LIST: List of items with properties.
	Examples: Inventory, Spell List, Abilities
  
  - CONT_TAGS: Simple list of strings.
	Examples: Languages, Proficiencies, Keywords
  ```

- [ ] **6.2 Write classification instructions**

  ```
  ## TASK
  
  Analyze the game rules below. Identify the main character sheet fields.
  
  For each field, output:
  - path: Where it lives (e.g., "resources.hp", "attributes.str")
  - label: Display name (e.g., "Hit Points", "Strength")
  - prefab: Type from the list above
  - config: Configuration (min, max, length, etc.)
  - category: One of: identity, attributes, skills, resources, features, inventory, progression, status
  
  Focus on CORE fields that appear on every character sheet.
  Skip optional rules, variant rules, class-specific features.
  Limit to 20-30 most important fields.
  ```

- [ ] **6.3 Write few-shot examples**

  At least 2 complete examples:

  **Example 1: D&D-style**
  ```
  INPUT:
  "Characters have six ability scores from 1-20: Strength, Dexterity, 
  Constitution, Intelligence, Wisdom, Charisma. Hit Points represent 
  health, starting at 10 + Constitution modifier."
  
  OUTPUT:
  [
	{"path": "attributes.str", "label": "Strength", "prefab": "VAL_INT", 
	 "config": {"min": 1, "max": 20}, "category": "attributes"},
	{"path": "resources.hp", "label": "Hit Points", "prefab": "RES_POOL",
	 "config": {"min": 0}, "category": "resources"}
  ]
  ```

  **Example 2: Percentile-style**
  ```
  INPUT:
  "Skills are rated 1-99. Roll d100 under your skill to succeed.
  Sanity starts equal to POW × 5 and decreases when seeing horrors."
  
  OUTPUT:
  [
	{"path": "skills.spot_hidden", "label": "Spot Hidden", "prefab": "VAL_INT",
	 "config": {"min": 0, "max": 99}, "category": "skills"},
	{"path": "resources.sanity", "label": "Sanity", "prefab": "RES_POOL",
	 "config": {"min": 0}, "category": "resources"}
  ]
  ```

- [ ] **6.4 Write engine classification prompt**

  ```
  ## RESOLUTION ENGINE
  
  Which pattern best matches this game's core resolution?
  
  - DC_OVER: Roll + modifier ≥ target (D&D, Pathfinder)
  - TN_UNDER: Roll ≤ stat/skill (Call of Cthulhu, GURPS)
  - POOL_COUNT: Roll Xd6, count successes (Shadowrun, WoD)
  - POOL_READ: Roll 2d6, read result tier (PbtA, BitD)
  - STEP_DIE: Roll die type based on stat (Savage Worlds)
  
  Output:
  {
	"engine": "DC_OVER",
	"dice": "1d20",
	"success_text": "Roll + mod meets or beats DC",
	"crit_text": "Natural 20 = critical hit"
  }
  ```

- [ ] **6.5 Design multi-shot structure (for small models)**

  Break into phases for <8B models:

  **Phase 1: Identification**
  ```
  "List the main character stats/resources you see in these rules.
   Just names, one per line."
  
  Output: "Strength\nDexterity\nHit Points\nStress\n..."
  ```

  **Phase 2: Classification**
  ```
  "For each stat below, what prefab type is it?
   
   - Strength: ???
   - Hit Points: ???
   
   Options: VAL_INT, RES_POOL, RES_TRACK, RES_COUNTER"
  
  Output: "Strength: VAL_INT\nHit Points: RES_POOL\n..."
  ```

  **Phase 3: Configuration**
  ```
  "For each classified field, what are the bounds/limits?
   
   Strength (VAL_INT): min=???, max=???
   Hit Points (RES_POOL): min=???"
  ```

- [ ] **6.6 Create `ManifestExtractor` service**

  ```python
  class ManifestExtractor:
	  def __init__(self, llm: LLMConnector):
		  self.llm = llm
	  
	  def extract(self, rules_text: str, multi_shot: bool = True) -> SystemManifest:
		  if multi_shot:
			  return self._extract_multi_shot(rules_text)
		  else:
			  return self._extract_single_shot(rules_text)
  ```

- [ ] **6.7 Add validation of classifier output**

  Check:
  - All prefab IDs are valid
  - All category names are valid
  - No duplicate paths
  - Required config present (length for tracks, etc.)
  - Reasonable number of fields (5-50)

- [ ] **6.8 Add confidence indicators (optional)**

  Ask model for confidence:
  ```
  "Rate your confidence in each classification (high/medium/low)"
  ```
  
  Flag low-confidence for user review in Setup Wizard.

### Acceptance Criteria

- [ ] Classifier prompt <2000 tokens (excluding rules)
- [ ] Includes 2+ complete few-shot examples
- [ ] Multi-shot structure defined for small models
- [ ] Extracted manifests pass validation
- [ ] Higher accuracy than current vocabulary extraction

---

## Task 7: Add Manifest Storage

### What

Store manifests in database for persistence and sharing:
- Database table for manifests
- Repository with CRUD operations
- Seed built-in manifests on first launch
- Link sessions to manifests

### Why

Manifests need to:
- Persist across app restarts
- Be selected in Setup Wizard
- Be shared/imported by users
- Allow user customization (future)

### File Structure

```
app/database/repositories/
└── manifest_repository.py

app/services/
└── manifest_service.py
```

### Subtasks

- [ ] **7.1 Create `manifests` table**

  ```sql
  CREATE TABLE manifests (
	  id INTEGER PRIMARY KEY AUTOINCREMENT,
	  system_id TEXT NOT NULL UNIQUE,
	  name TEXT NOT NULL,
	  data_json TEXT NOT NULL,
	  is_builtin BOOLEAN DEFAULT FALSE,
	  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

- [ ] **7.2 Create `ManifestRepository`**

  ```python
  class ManifestRepository(BaseRepository):
	  def create_table(self): ...
	  def create(self, manifest: SystemManifest, is_builtin: bool = False) -> int: ...
	  def get_by_id(self, manifest_id: int) -> Optional[SystemManifest]: ...
	  def get_by_system_id(self, system_id: str) -> Optional[SystemManifest]: ...
	  def get_all(self) -> List[Dict[str, Any]]: ...  # For dropdowns
	  def update(self, manifest_id: int, manifest: SystemManifest): ...
	  def delete(self, manifest_id: int): ...
  ```

- [ ] **7.3 Add to DBManager**

  ```python
  class DBManager:
	  self.manifests: Optional[ManifestRepository] = None
  ```

- [ ] **7.4 Seed built-in manifests**

  On first launch or app update:
  ```python
  def seed_builtin_manifests(db: DBManager):
	  for json_file in Path("app/data/manifests").glob("*.json"):
		  manifest = manifest_from_file(json_file)
		  existing = db.manifests.get_by_system_id(manifest.id)
		  if not existing:
			  db.manifests.create(manifest, is_builtin=True)
  ```

- [ ] **7.5 Link sessions to manifests**

  Option A: New column
  ```sql
  ALTER TABLE sessions ADD COLUMN manifest_id INTEGER REFERENCES manifests(id);
  ```

  Option B: In setup_phase_data JSON (less migration)
  ```json
  {"manifest_id": 5, ...}
  ```

  Recommend Option B for easier rollout.

- [ ] **7.6 Update Setup Wizard**

  Add system selection:
  ```python
  with ui.step("Game System"):
	  manifests = db.manifests.get_all()
	  options = {m["id"]: m["name"] for m in manifests}
	  options["_custom"] = "Create from rules text..."
	  
	  ui.select(options, label="Choose System").bind_value(self, "manifest_id")
	  
	  # Only show extraction if custom selected
	  with ui.column().bind_visibility_from(self, "is_custom"):
		  ui.textarea(label="Paste game rules...")
  ```

- [ ] **7.7 Load manifest in gameplay**

  ```python
  def load_game(self, session_id: int):
	  session = db.sessions.get_by_id(session_id)
	  setup_data = json.loads(session.setup_phase_data)
	  
	  manifest_id = setup_data.get("manifest_id")
	  if manifest_id:
		  self.manifest = db.manifests.get_by_id(manifest_id)
	  else:
		  self.manifest = None  # Legacy mode
  ```

- [ ] **7.8 Add export/import**

  ```python
  def export_manifest(manifest_id: int) -> str:
	  manifest = db.manifests.get_by_id(manifest_id)
	  return manifest_to_json(manifest)
  
  def import_manifest(json_str: str) -> int:
	  manifest = manifest_from_json(json_str)
	  return db.manifests.create(manifest, is_builtin=False)
  ```

### Acceptance Criteria

- [ ] Manifests table created on first launch
- [ ] Built-in manifests seeded automatically
- [ ] Setup Wizard shows manifest dropdown
- [ ] Sessions correctly load linked manifest
- [ ] Export/import works for sharing

---

## Task 8: Entity Validation Pipeline

### What

Create the unified validation pipeline that applies prefab validation and formula computation to entities:
- Validate entity against manifest fields
- Compute derived values (formulas)
- Clamp values via prefab validators
- Handle cross-field constraints (max_formula)

### Why

Validation currently happens in:
- `entity_update.py` handler
- `invariant_validator.py` service
- `math_engine.py` for derived stats

This consolidates into one pipeline that runs on every entity update.

### File Structure

```
app/prefabs/
└── validation.py        # Main validation pipeline
```

### Subtasks

- [ ] **8.1 Create entity validation function**

  ```python
  def validate_entity(
	  entity: Dict[str, Any],
	  manifest: SystemManifest,
	  changed_paths: Optional[List[str]] = None
  ) -> Tuple[Dict[str, Any], List[str]]:
	  """
	  Validate entity against manifest.
	  
	  Returns:
		  (corrected_entity, list_of_corrections)
	  """
  ```

- [ ] **8.2 Implement formula context building**

  ```python
  def build_formula_context(entity: dict, manifest: SystemManifest) -> Dict[str, float]:
	  """
	  Flatten entity values + resolve aliases for formula evaluation.
	  
	  Result: {"attributes_str": 18, "str_mod": 4, "progression_level": 5}
	  """
  ```

- [ ] **8.3 Implement derived field computation**

  For fields with `formula`:
  ```python
  if field.formula:
	  computed = evaluate(field.formula, context)
	  set_path(entity, field.path, computed)
  ```

- [ ] **8.4 Implement max_formula for pools**

  For `RES_POOL` fields with `max_formula`:
  ```python
  if field.prefab == "RES_POOL" and field.max_formula:
	  max_val = evaluate(field.max_formula, context)
	  pool = get_path(entity, field.path)
	  pool["max"] = int(max_val)
  ```

- [ ] **8.5 Apply prefab validation**

  ```python
  prefab = PREFABS[field.prefab]
  value = get_path(entity, field.path)
  corrected = prefab.validate(value, field.config)
  if corrected != value:
	  corrections.append(f"{field.path}: {value} → {corrected}")
	  set_path(entity, field.path, corrected)
  ```

- [ ] **8.6 Handle validation order**

  Order matters for derived values:
  1. Compute base values (non-derived)
  2. Build context with base values
  3. Compute derived values
  4. Validate all through prefabs

  May need dependency ordering for complex formulas.

- [ ] **8.7 Integrate into tool handlers**

  After any entity modification:
  ```python
  entity, corrections = validate_entity(entity, manifest)
  save_entity(entity)
  return {"changes": corrections, ...}
  ```

- [ ] **8.8 Add validation to entity load**

  Optional: Validate on load to fix corrupted data:
  ```python
  def get_entity(...):
	  entity = db.game_state.get_entity(...)
	  if manifest:
		  entity, _ = validate_entity(entity, manifest)
	  return entity
  ```

### Acceptance Criteria

- [ ] Validation pipeline handles all prefab types
- [ ] Formulas evaluate correctly with entity context
- [ ] Cross-field constraints (max_formula) work
- [ ] Corrections are logged and returned
- [ ] No exceptions on malformed data

---

## Implementation Order

```
Week 1: Foundation
├── Task 1: Prefab Catalog (validators + AI hints)
└── Task 2: Manifest Data Structures (FieldDef, SystemManifest)

Week 2: Content
├── Task 3: Example Manifests (D&D, CoC, BitD)
└── Task 7: Manifest Storage (database + seeding)

Week 3: Integration
├── Task 4: Tool Schemas (6 atomic tools)
├── Task 8: Entity Validation Pipeline
└── Task 5: Context Builder (path hints + examples)

Week 4: Extraction
└── Task 6: Classifier Prompt (for new systems)
```

### Dependency Graph

```
Task 1 (Prefabs) ───┬──> Task 2 (Manifest Structures)
					│
					├──> Task 3 (Example Manifests) ──> Task 7 (Storage)
					│
					├──> Task 4 (Tools) ──> Task 8 (Validation)
					│
					└──> Task 5 (Context) ──> Task 6 (Classifier)
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing sessions | Keep legacy codepaths, manifest is optional |
| Prefabs don't cover edge case | Start with essentials, expand based on feedback |
| Small models still struggle | Multi-shot prompting, more examples |
| Formula complexity | Start simple, add functions as needed |
| Migration effort | Additive changes, no destructive migrations |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Tool success rate | ~80% | >95% |
| Classification accuracy | N/A | >90% |
| Context size (tokens) | ~3500 | <2000 |
| Setup time (built-in systems) | 60s | <5s |
| Setup time (new systems) | 60s | <30s |
| Lines of validation code | ~500 | <200 |

---

## Appendix: Prefab Quick Reference

| ID | Shape | Validator Summary | Widget |
|----|-------|-------------------|--------|
| `VAL_INT` | `int` | Clamp min/max | `number` |
| `VAL_COMPOUND` | `{score, mod}` | Clamp score, compute mod | `compound` |
| `VAL_STEP_DIE` | `str` | Must be in chain | `die_selector` |
| `VAL_LADDER` | `{value, label}` | Clamp value, lookup label | `ladder` |
| `VAL_BOOL` | `bool` | Coerce to bool | `toggle` |
| `RES_POOL` | `{current, max}` | current ≤ max, ≥ min | `progress_bar` |
| `RES_COUNTER` | `int` | ≥ min (usually 0) | `counter` |
| `RES_TRACK` | `[bool...]` | Fixed length, sequential | `checkbox_row` |
| `CONT_LIST` | `[{...}...]` | Must be list | `item_list` |
| `CONT_TAGS` | `[str...]` | Must be string list | `tag_list` |
| `CONT_WEIGHTED` | `[{..., wt}]` | Sum vs capacity | `weighted_list` |