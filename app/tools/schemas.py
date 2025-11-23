from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

# A reusable JSON type to avoid recursion errors with Pydantic's schema generator.
JSONValue = Union[str, int, float, bool, dict, List]


class UpdatePair(BaseModel):
    """A key-value pair for updating attributes or properties."""

    key: str = Field(
        ...,
        description="The name of the attribute or property to update (e.g., 'hp_current', 'strength').",
    )
    value: JSONValue = Field(..., description="The new value to assign.")


class MathEval(BaseModel):
    """
    Evaluates a mathematical expression.
    Use this when you need to perform calculations (damage, currency exchange, XP totals) to ensure accuracy.

    **Example:**
    `math.eval(expression="(3 * 5) + 10")` -> Returns 25
    """

    name: Literal["math.eval"] = "math.eval"
    expression: str = Field(
        ...,
        description="Math expression to evaluate. Supports +, -, *, /, and parentheses.",
    )


class MemoryUpsert(BaseModel):
    """
    Create or update a memory entry. This is the primary way to store long-term information.

    **When to use:**
    - Recording narrative events ("The player met the King").
    - Storing facts ("Goblins hate fire").
    - Noting player preferences ("The player dislikes puzzles").

    **Deduplication:**
    The system will automatically update existing similar memories instead of creating duplicates.

    **Example:**
    `memory.upsert(kind="episodic", content="We explored the dank cave.", priority=3, tags=["cave", "exploration"])`
    """

    name: Literal["memory.upsert"] = "memory.upsert"
    kind: Literal["episodic", "semantic", "lore", "user_pref"] = Field(
        ...,
        description="Category: 'episodic' (events), 'semantic' (facts), 'lore' (world info), 'user_pref' (player likes/dislikes).",
    )
    content: str = Field(..., description="The detailed content of the memory.")
    priority: int = Field(
        3,
        description="Importance: 1 (Trivial) to 5 (Critical/Core Memory).",
        ge=1,
        le=5,
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Keywords for retrieval (e.g., ['npc_name', 'location', 'quest_id']).",
    )


class MemoryUpdate(BaseModel):
    """
    Modify an existing memory.

    **Example:**
    `memory.update(memory_id=123, priority=5, tags=["important", "traitor"])`
    """

    name: Literal["memory.update"] = "memory.update"
    memory_id: int = Field(..., description="ID of the memory.")
    content: Optional[str] = Field(None, description="New text content.")
    priority: Optional[int] = Field(None, description="New priority (1-5).")
    tags: Optional[List[str]] = Field(None, description="New tag list.")


class RagSearch(BaseModel):
    """
    Search the vector database for static lore or background information.

    **When to use:**
    - To look up historical facts, monster descriptions, or world details not currently in context.

    **Example:**
    `rag.search(query="weakness of frost giants", k=2)`
    """

    name: Literal["rag.search"] = "rag.search"
    query: str = Field(..., description="The natural language search query.")
    k: int = Field(
        2,
        description="Number of results to return. Keep small (2-4) to save context window.",
    )
    filters: Optional[dict] = Field(
        None, description="Metadata filters, e.g., {'source': 'monster_manual'}."
    )


class RngRoll(BaseModel):
    """
    Roll dice using standard RPG notation.

    **When to use:**
    - Generating random outcomes for events not covered by specific rules.
    - Rolling for loot tables or random encounters.

    **Example:**
    `rng.roll(dice="2d6+3")` -> Returns total and individual rolls.
    """

    name: Literal["rng.roll"] = "rng.roll"
    dice: Optional[str] = Field(
        None, description="Dice specification (e.g., '1d20', '2d6+4', '3d8-1')."
    )
    dice_spec: Optional[str] = Field(None, description="Alias for 'dice'.")


class Modifier(BaseModel):
    source: str = Field(
        ..., description="Reason for modifier (e.g. 'Strength Bonus', 'Rainy Weather')."
    )
    value: int = Field(..., description="Integer value to add/subtract.")


class ResolutionPolicy(BaseModel):
    type: str = Field(..., description="Type of check (e.g., 'skill_check', 'save').")
    dc: int = Field(..., description="The Target Number / Difficulty Class.")
    base_formula: str = Field(
        ..., description="The dice to roll (e.g., '1d20', '3d6')."
    )
    modifiers: Optional[List[Modifier]] = Field(
        None, description="List of modifiers applying to this check."
    )


class RulesResolveAction(BaseModel):
    """
    Resolves a complex action using a dynamic policy.

    **When to use:**
    - When the player attempts something risky (climbing a wall, persuading a guard).
    - You determine the DC and modifiers based on the current situation.

    **Example:**
    `rules.resolve_action(action_id="Pick Lock", actor_id="player", resolution_policy={...})`
    """

    name: Literal["rules.resolve_action"] = "rules.resolve_action"
    action_id: str = Field(
        ..., description="Descriptive name of action (e.g., 'Climb Wall')."
    )
    actor_id: str = Field(..., description="Key of the entity acting (e.g., 'player').")
    resolution_policy: ResolutionPolicy = Field(
        ..., description="The logic for the dice roll."
    )


class Patch(BaseModel):
    op: Literal["add", "replace", "remove"] = Field(
        ..., description="JSON Patch operation."
    )
    path: str = Field(..., description="JSON path (e.g., '/attributes/hp').")
    value: Optional[JSONValue] = Field(None, description="Value to add or replace.")


class StateQuery(BaseModel):
    """
    Read data from the game state.

    **When to use:**
    - Checking a player's stats before a roll.
    - verifying if an item exists.
    - checking quest status.

    **Example:**
    `state.query(entity_type="character", key="player", json_path="vitals.hp")`
    """

    name: Literal["state.query"] = "state.query"
    entity_type: str = Field(
        ..., description="Entity type (character, inventory, quest, location, scene)."
    )
    key: str = Field(
        ..., description="Entity key. Use '*' to get ALL entities of that type."
    )
    json_path: str = Field(
        ..., description="JSONPath to specific data. Use '.' for the whole object."
    )


class TimeNow(BaseModel):
    """
    Get the current real-world UTC timestamp.

    **When to use:**
    - Rarely needed for gameplay. Use `time.advance` for fictional time.
    """

    name: Literal["time.now"] = "time.now"


class MemoryQuery(BaseModel):
    """
    Retrieve memories based on filters.

    **When to use:**
    - Recalling past interactions with an NPC.
    - Checking what the player knows about a topic.

    **Example:**
    `memory.query(tags=["npc_gorn", "trust"], limit=5)`
    """

    name: Literal["memory.query"] = "memory.query"
    kind: Optional[str] = Field(
        None, description="Filter by kind (episodic, semantic, etc)."
    )
    tags: Optional[List[str]] = Field(None, description="Filter by tags.")
    query_text: Optional[str] = Field(None, description="Search content text.")
    limit: int = Field(5, description="Max results.", ge=1, le=20)
    semantic: Optional[bool] = Field(
        False, description="Enable vector/semantic search."
    )
    time_query: Optional[str] = Field(
        None, description="Filter by fictional time string."
    )


class MemoryDelete(BaseModel):
    """
    Permanently delete a memory.
    """

    name: Literal["memory.delete"] = "memory.delete"
    memory_id: int = Field(..., description="ID of the memory.")


class TimeAdvance(BaseModel):
    """
    Advance the FICTIONAL game time.

    **When to use:**
    - Traveling, sleeping, or waiting.
    - Transitioning between scenes.

    **Example:**
    `time.advance(description="You sleep through the night.", new_time="Day 2, Morning")`
    """

    name: Literal["time.advance"] = "time.advance"
    description: str = Field(..., description="Narrative description of time passing.")
    new_time: str = Field(..., description="The new formatted time string.")


class Deliberate(BaseModel):
    """
    Do nothing / Think.

    **When to use:**
    - You need to deliberate but no game state needs changing.
    - You are waiting for user input.
    """

    name: Literal["deliberate"] = "deliberate"


class CharacterUpdate(BaseModel):
    """
    Updates specific values on a character sheet.

    **When to use:**
    - Taking damage or healing ("hp_current").
    - Changing a stat ("strength", "gold").
    - **DO NOT USE** to define new rules (use `schema.upsert_attribute`).

    **Example:**
    `character.update(character_key="player", updates=[{"key": "hp_current", "value": 15}])`
    """

    name: Literal["character.update"] = "character.update"
    character_key: str = Field(..., description="Character ID (usually 'player').")
    updates: List[UpdatePair] = Field(..., description="List of keys and new values.")


class SchemaQuery(BaseModel):
    """
    Look up game rules/mechanics.

    **When to use:**
    - "What does the 'Acrobatics' skill do?"
    - "How does the 'Fatigued' condition work?"
    """

    name: Literal["schema.query"] = "schema.query"
    query_type: Literal[
        "attribute", "resource", "skill", "action_economy", "class", "race", "all"
    ]
    specific_name: Optional[str] = Field(
        None, description="Name of the item to look up."
    )


class NpcAdjustRelationship(BaseModel):
    """
    Adjust NPC relationship metrics (Trust, Attraction, Fear).

    **When to use:**
    - After social interactions.
    - When the player helps or harms an NPC.

    **Example:**
    `npc.adjust_relationship(npc_key="guard", subject_key="player", trust_change=2)`
    """

    name: Literal["npc.adjust_relationship"] = "npc.adjust_relationship"
    npc_key: str = Field(..., description="The NPC having the feeling.")
    subject_key: str = Field(
        ..., description="The target of the feeling (e.g. 'player')."
    )
    trust_change: Optional[int] = Field(
        None, description="Add/Subtract trust (-10 to 10)."
    )
    attraction_change: Optional[int] = Field(
        None, description="Add/Subtract attraction (-10 to 10)."
    )
    fear_change: Optional[int] = Field(None, description="Add/Subtract fear (0 to 10).")
    tags_to_add: Optional[List[str]] = Field(
        None, description="Add tags (e.g., 'rival', 'friend')."
    )
    tags_to_remove: Optional[List[str]] = Field(None, description="Remove tags.")


class InventoryAddItem(BaseModel):
    """
    Add an item to inventory. Handles quantity increments automatically.

    **Example:**
    `inventory.add_item(owner_key="player", item_name="Potion", quantity=1)`
    """

    name: Literal["inventory.add_item"] = "inventory.add_item"
    owner_key: str = Field(..., description="Inventory owner.")
    item_name: str = Field(..., description="Name of item.")
    quantity: int = Field(1, description="Count to add.", gt=0)
    description: Optional[str] = Field(None, description="Item description (if new).")
    properties: Optional[Dict[str, Any]] = Field(None, description="Custom properties.")


class InventoryRemoveItem(BaseModel):
    """
    Remove or decrement an item.

    **Example:**
    `inventory.remove_item(owner_key="player", item_name="Potion", quantity=1)`
    """

    name: Literal["inventory.remove_item"] = "inventory.remove_item"
    owner_key: str = Field(..., description="Inventory owner.")
    item_name: str = Field(..., description="Name of item.")
    quantity: int = Field(1, description="Count to remove.", gt=0)


class QuestUpdateStatus(BaseModel):
    """
    Change the overall status of a quest.

    **Example:**
    `quest.update_status(quest_key="q_main", new_status="completed")`
    """

    name: Literal["quest.update_status"] = "quest.update_status"
    quest_key: str = Field(..., description="Quest ID.")
    new_status: Literal["active", "completed", "failed", "hidden"] = Field(
        ..., description="New status."
    )


class SceneAddMember(BaseModel):
    """
    Add a character to the active scene context.
    Use this when an NPC enters the area so they are included in context retrieval.
    """

    name: Literal["scene.add_member"] = "scene.add_member"
    character_key: str = Field(..., description="Character ID to add.")


class SceneRemoveMember(BaseModel):
    """
    Remove a character from the active scene.
    Use this when an NPC leaves, dies, or the player moves away.
    """

    name: Literal["scene.remove_member"] = "scene.remove_member"
    character_key: str = Field(..., description="Character ID to remove.")


class LocationNeighbor(BaseModel):
    """A connection to an adjacent location."""
    target_key: str = Field(..., description="ID of the existing location to connect to.")
    direction: str = Field(..., description="Direction/Method TO the neighbor (e.g., 'North', 'Up', 'Gate').")


class LocationCreate(BaseModel):
    """
    Create a new location in the world database.
    Use this to define distinct areas (rooms, clearings, streets).
    
    **MAP GRANULARITY:** Create distinct nodes for Rooms, Buildings, or Landmarks. Do not create nodes for furniture.
    """
    name: Literal["location.create"] = "location.create"
    key: str = Field(..., description="Unique ID (e.g., 'crypt_entrance').")
    name_display: str = Field(..., description="Display name (e.g., 'The Crypt Mouth').")
    description_visual: str = Field(..., description="Visuals: lighting, architecture, layout.")
    description_sensory: str = Field(..., description="Smell, sound, temperature.")
    type: Literal["indoor", "outdoor", "dungeon", "city"] = Field(..., description="General environment type.")
    neighbors: List[LocationNeighbor] = Field(
        default_factory=list, 
        description="List of connections to EXISTING locations. The system will automatically create bidirectional links."
    )


class LocationConnect(BaseModel):
    """
    Connect two existing locations in the world graph.
    Usually creates a two-way connection unless 'one_way' is True.
    """
    name: Literal["location.connect"] = "location.connect"
    from_key: str = Field(..., description="ID of the starting location.")
    to_key: str = Field(..., description="ID of the destination location.")
    direction: str = Field(..., description="Direction/Method (e.g., 'north', 'up', 'portal').")
    back_direction: Optional[str] = Field(None, description="Return direction (e.g., 'south'). Required if not one_way.")
    display_name: str = Field(..., description="Narrative name of the exit (e.g. 'Heavy Iron Door').")
    is_hidden: bool = Field(False, description="If true, exit is not immediately obvious.")
    is_locked: bool = Field(False, description="If true, requires a key or check to open.")
    one_way: bool = Field(False, description="If true, connection is one-way only.")


class CharacterApplyDamage(BaseModel):
    """
    Apply damage to a character's Vital (usually HP).
    Handles math and checks for death/unconscious state automatically.
    """
    name: Literal["character.apply_damage"] = "character.apply_damage"
    target_key: str = Field(..., description="Key of the character taking damage.")
    amount: int = Field(..., description="Amount of damage to deal.")
    vital_name: str = Field("HP", description="The vital to reduce (e.g. 'HP', 'Sanity', 'Stamina').")
    damage_type: Literal["physical", "fire", "cold", "poison", "psychic", "magic"] = Field("physical", description="Source of damage.")
    explanation: str = Field(..., description="Narrative reason (e.g. 'Hit by goblin arrow').")


class CharacterRestoreVital(BaseModel):
    """
    Heal or restore a character's Vital (HP, Mana, etc).
    Automatically clamps to the maximum value defined in the character's sheet.
    """
    name: Literal["character.restore_vital"] = "character.restore_vital"
    target_key: str = Field(..., description="Key of the character being restored.")
    vital_name: str = Field("HP", description="The vital to restore.")
    amount: int = Field(..., description="Amount to restore.")


class CharacterModifyStat(BaseModel):
    """
    Buff or Debuff a core attribute temporarily or permanently.
    Use this for spells, potions, or narrative consequences.
    """
    name: Literal["character.modify_stat"] = "character.modify_stat"
    target_key: str = Field(..., description="Key of the character.")
    stat_name: str = Field(..., description="Name of the stat (e.g. 'Strength', 'Agility').")
    amount: int = Field(..., description="Value to add (positive) or subtract (negative).")
    duration: Literal["permanent", "scene", "turn"] = Field(..., description="How long the effect lasts.")


class NpcSpawn(BaseModel):
    """
    Create a new NPC and add them to the current location and active scene.
    Use this when a new character enters the story.
    """
    name: Literal["npc.spawn"] = "npc.spawn"
    key: str = Field(..., description="Unique ID (e.g. 'goblin_grunt_1').")
    name_display: str = Field(..., description="Name shown to player (e.g. 'Goblin Grunt').")
    visual_description: str = Field(..., description="Physical appearance for UI tooltip.")
    stat_template: str = Field(..., description="Name of the StatBlockTemplate to use (e.g. 'Monster', 'Commoner').")
    initial_disposition: Literal["hostile", "neutral", "friendly"] = Field("neutral", description="Starting attitude toward player.")
    location_key: Optional[str] = Field(None, description="Location ID. If omitted, uses current active scene location.")


class SceneMoveTo(BaseModel):
    """
    Move the entire party (active scene) to a new location.
    Updates the location of all characters currently in the scene.

    **Example:**
    `scene.move_to(new_location_key="dungeon_entrance")`
    """

    name: Literal["scene.move_to"] = "scene.move_to"
    new_location_key: str = Field(..., description="ID of the destination location.")


class SceneDefineZones(BaseModel):
    """
    Define or update the zones within the current active scene.
    Use this when a new scene begins or its layout changes significantly.
    """
    name: Literal["scene.define_zones"] = "scene.define_zones"
    zones: List[Dict[str, Any]] = Field(
        ...,
        description="List of zone dictionaries. Each dict must have 'id' (unique key), 'name' (display name), and optionally 'x', 'y' (grid coordinates)."
    )
    layout_type: Optional[str] = Field(
        "grid",
        description="Layout style (e.g., 'grid', 'abstract', 'linear'). Defaults to 'grid'."
    )

class SceneMoveActor(BaseModel):
    """
    Move a character (actor) to a different zone within the current active scene.
    """
    name: Literal["scene.move_actor"] = "scene.move_actor"
    actor_key: str = Field(..., description="Key of the character to move (e.g., 'player', 'npc_goblin').")
    target_zone_id: str = Field(..., description="ID of the zone to move the actor to.")
    is_hidden: bool = Field(False, description="If true, the actor is hidden within the zone (e.g., hiding behind cover).")


class JournalAddEntry(BaseModel):
    """
    Record a plot-relevant event, clue, or quest step in the player's journal.
    Replaces generic memory upserts for tracking story progress.
    """
    name: Literal["journal.add_entry"] = "journal.add_entry"
    title: str = Field(..., description="Short headline (e.g. 'The King's Request').")
    content: str = Field(..., description="Details of the entry.")
    tags: List[str] = Field(default_factory=list, description="Keywords.")
    is_secret: bool = Field(False, description="If true, player doesn't see this immediately (GM note).")

class MapUpdate(BaseModel):
    """
    Manage the tactical battlemap.
    Use algebraic notation (A1, B2) for coordinates.
    
    Operations:
    - 'init': Start a new combat/scene map. Define dimensions.
    - 'move': Move characters to specific squares.
    - 'terrain': Place obstacles.
    """
    name: Literal["map.update"] = "map.update"
    operation: Literal["init", "move", "terrain"] = Field(..., description="Action to perform.")
    width: int = Field(5, description="Grid width (columns A-Z). Used with 'init'.")
    height: int = Field(5, description="Grid height (rows 1-99). Used with 'init'.")
    entities: Optional[Dict[str, str]] = Field(None, description="Map of Entity Key -> Coordinate (e.g. {'player': 'A1'}).")
    terrain: Optional[List[str]] = Field(None, description="List of coordinates that are blocked/walls (e.g. ['C3', 'C4']).")
