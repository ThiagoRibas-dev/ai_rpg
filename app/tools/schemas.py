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


class StateApplyPatch(BaseModel):
    """
    Apply low-level JSON Patch operations to ANY game entity.

    **âš ï¸  WARNING:** Use specific tools (like `character.update` or `inventory.add_item`) if possible.
    Only use this for complex data structures or entities without dedicated tools.

    **Example:**
    `state.apply_patch(entity_type="location", key="tavern", patch=[{"op": "replace", "path": "/is_open", "value": false}])`
    """

    name: Literal["state.apply_patch"] = "state.apply_patch"
    entity_type: str = Field(
        ..., description="Type of entity (e.g., 'character', 'scene', 'location')."
    )
    key: str = Field(..., description="Unique key of the entity.")
    patch: List[Patch] = Field(..., description="List of patch operations.")


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


class SchemaUpsertAttribute(BaseModel):
    """
    **SETUP MODE ONLY.** Defines a RULE or CONCEPT in the game system.

    **DO NOT USE** to set a specific character's value (e.g., "Player has 50 Sanity"). Use `character.update` for values.

    **When to use:**
    - "This game uses a stat called Sanity."
    - "There is a resource called Mana."
    - "Define a 'Reputation' track."

    **Example:**
    `schema.upsert_attribute(property_name="Sanity", template="stat", min_value=0, max_value=100, icon="ðŸ§ ")`
    """

    name: Literal["schema.upsert_attribute"] = "schema.upsert_attribute"

    property_name: str = Field(
        ...,
        description="The programmatic name of the property (e.g., 'Sanity', 'Mana', 'Allegiance').",
    )
    description: str = Field(
        ..., description="A human-readable description of what the property represents."
    )
    entity_type: Literal["character", "item", "location"] = Field(
        "character", description="The type of entity this property applies to."
    )
    template: Optional[
        Literal["resource", "stat", "reputation", "flag", "enum", "string"]
    ] = Field(
        None,
        description="Predefined behavior template. 'resource' has current/max, 'stat' is a fixed number, 'enum' is a list of options.",
    )
    default_value: Optional[JSONValue] = Field(
        None, description="Initial value for new entities."
    )
    min_value: Optional[int] = Field(
        None, description="Minimum allowed integer value (for stats/resources)."
    )
    max_value: Optional[int] = Field(
        None, description="Maximum allowed integer value (for stats/resources)."
    )

    # --- Restored Fields ---
    allowed_values: Optional[List[str]] = Field(
        None,
        description="For 'enum' types, the specific list of allowed string options (e.g., ['Novice', 'Veteran', 'Master']).",
    )
    display_category: Optional[str] = Field(
        None,
        description="Grouping header for the UI (e.g., 'Primary Stats', 'Social', 'Inventory').",
    )
    icon: Optional[str] = Field(
        None,
        description="Emoji or short string to use as a visual icon in the UI (e.g., 'â ¤ï¸ ', 'ðŸ›¡ï¸ ').",
    )
    display_format: Optional[
        Literal["number", "bar", "badge", "clock", "checkboxes"]
    ] = Field(
        None,
        description="Visual style hint for the UI. 'bar' for resources, 'clock' for tracks.",
    )
    regenerates: Optional[bool] = Field(
        None,
        description="For 'resource' types, whether it automatically regenerates over time.",
    )
    regeneration_rate: Optional[int] = Field(
        None, description="Amount to regenerate per game turn/rest."
    )


class RequestSetupConfirmation(BaseModel):
    """
    **SETUP MODE ONLY.** Summarize the setup and ask the user to confirm.

    **Usage:**
    You MUST call this tool with a full summary before you can start the game.
    """

    name: Literal["request_setup_confirmation"] = "request_setup_confirmation"
    summary: str = Field(
        ..., description="Full summary of decisions made during the SETUP process of the game."
    )


class EndSetupAndStartGameplay(BaseModel):
    """
    **SETUP MODE ONLY.** Transitions the game to GAMEPLAY mode.

    **Usage:**
    Call this ONLY after the user has explicitly said "Yes" or "Ready" to your confirmation summary.
    """

    name: Literal["end_setup_and_start_gameplay"] = "end_setup_and_start_gameplay"
    reason: str = Field(..., description="Why setup is complete.")


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


class QuestUpdateObjective(BaseModel):
    """
    Complete or un-complete a specific objective within a quest.

    **Example:**
    `quest.update_objective(quest_key="q_main", objective_text="Find the map", is_completed=true)`
    """

    name: Literal["quest.update_objective"] = "quest.update_objective"
    quest_key: str = Field(..., description="Quest ID.")
    objective_text: str = Field(..., description="Exact text of the objective.")
    is_completed: bool = Field(True, description="Completion status.")


class EntityCreate(BaseModel):
    """
    Spawn a new entity (NPC, Item, Location) into the game DB.

    **When to use:**
    - The player enters a new room (Location).
    - A wild monster appears (Character).
    - Loot is generated (Item).

    **Example:**
    `entity.create(entity_type="character", entity_key="goblin_1", data={"name": "Goblin"})`
    """

    name: Literal["entity.create"] = "entity.create"
    entity_type: str = Field(
        ..., description="Type: 'character', 'item', 'location', 'quest'."
    )
    entity_key: str = Field(..., description="Unique ID.")
    template_name: Optional[str] = Field(
        None, description="StatBlockTemplate to use (e.g. 'Monster')."
    )
    data: Dict[str, Any] = Field(..., description="Full entity data dictionary.")


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


class SceneMoveTo(BaseModel):
    """
    Move the entire party (active scene) to a new location.
    Updates the location of all characters currently in the scene.

    **Example:**
    `scene.move_to(new_location_key="dungeon_entrance")`
    """

    name: Literal["scene.move_to"] = "scene.move_to"
    new_location_key: str = Field(..., description="ID of the destination location.")
