from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

# A reusable JSON type to avoid recursion errors with Pydantic's schema generator.
JSONValue = Union[str, int, float, bool, dict, List]


class UpdatePair(BaseModel):
    """A key-value pair for updating attributes or properties."""

    key: str = Field(
        ..., description="The name of the attribute or property to update."
    )
    value: JSONValue = Field(
        ..., description="The new value for the attribute or property."
    )


class MathEval(BaseModel):
    """
    Evaluates a simple mathematical expression.
    **Supported operations:** +, -, *, /, ( )
    **Example:** "2+3*4" → 14
    """

    name: Literal["math.eval"] = "math.eval"
    expression: str = Field(..., description="Math expression, e.g., '2+3*4'")


class MemoryUpsert(BaseModel):
    """
    Create or update a memory entry with automatic deduplication.
    **When to use:**
    - Recording important events (episodic)
    - Storing facts about the world (semantic)
    - Noting lore or backstory (lore)
    - Tracking player preferences (user_pref)
    **Automatic deduplication:**
    If a very similar memory exists, it will be updated instead of creating a duplicate.
    **Priority guide:**
    - 1-2: Minor details, flavor text
    - 3: Normal importance (default)
    - 4: Important events, character development
    - 5: Critical plot points, character-defining moments
    **Example:**
    memory.upsert({
        "kind": "episodic",
        "content": "Defeated the goblin chieftain in single combat, earning respect of the tribe",
        "priority": 4,
        "tags": ["combat", "goblins", "reputation"]
    })
    """

    name: Literal["memory.upsert"] = "memory.upsert"
    kind: str = Field(
        ...,
        description="Memory type: 'episodic' (events), 'semantic' (facts), 'lore' (backstory), 'user_pref' (preferences)",
    )
    content: str = Field(
        ..., description="The memory content (be specific and descriptive)"
    )
    priority: int = Field(
        3, description="Importance rating: 1=trivial, 3=normal, 5=critical", ge=1, le=5
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Tags for categorization (e.g., ['combat', 'magic', 'npc_name'])",
    )


class RagSearch(BaseModel):
    """
    Search the RAG index for lore chunks.
    **When to use:** Retrieving background information or world lore.
    **Timeboxed:** Keep k small (2-4) to avoid overwhelming context.
    """

    name: Literal["rag.search"] = "rag.search"
    query: str = Field(..., description="The search query")
    k: int = Field(2, description="Number of chunks to return (keep small: 2-4)")
    filters: Optional[dict] = Field(
        None, description="Optional filter object, e.g., {'topic': 'ambush'}"
    )


class RngRoll(BaseModel):
    """
    Roll dice using standard RPG notation.
    **Syntax:** NdS±M where N=number of dice, S=sides, M=modifier
    **Examples:**
    - "1d20+5" → Roll d20, add 5
    - "2d6-1" → Roll 2d6, subtract 1
    - "3d8" → Roll 3d8, no modifier
    **Returns:** Total result and individual roll values
    """

    name: Literal["rng.roll"] = "rng.roll"
    dice: Optional[str] = Field(
        None, description="Dice specification (e.g., '1d20+3', '2d6-1')"
    )
    dice_spec: Optional[str] = Field(None, description="Alias for 'dice' parameter")


class Modifier(BaseModel):
    source: str = Field(
        ...,
        description="The reason for the modifier (e.g., 'Player's Tech Skill', 'Magic Item Bonus').",
    )
    value: int = Field(..., description="The value of the modifier.")


class ResolutionPolicy(BaseModel):
    type: str = Field(
        ...,
        description="The type of resolution mechanic. Allowed value: 'skill_check'.",
    )
    dc: int = Field(
        ...,
        description="The final Difficulty Class for the check, as determined by the LLM.",
    )
    base_formula: str = Field(
        ..., description="The base dice roll formula (e.g., '1d20')."
    )
    modifiers: Optional[List[Modifier]] = Field(
        None, description="A list of all modifiers the LLM has decided to apply."
    )


class RulesResolveAction(BaseModel):
    """
    Resolve an action using a dynamic resolution policy.
    **When to use:** When an action requires a skill check or contested roll.
    **You decide:** DC, modifiers, and resolution type based on context.
    """

    name: Literal["rules.resolve_action"] = "rules.resolve_action"
    action_id: str = Field(
        ..., description="Descriptive label for the action (e.g., 'Open Humming Lock')"
    )
    actor_id: str = Field(..., description="ID of the actor performing the action")
    resolution_policy: ResolutionPolicy = Field(
        ..., description="Complete policy for resolving the action"
    )


class Patch(BaseModel):
    op: str = Field(..., description="Operation: 'add', 'replace', or 'remove'")
    path: str = Field(
        ..., description="JSON path to the value (e.g., '/attributes/hp_current')"
    )
    value: Optional[JSONValue] = Field(
        None, description="The value to use (not needed for 'remove')"
    )


class StateApplyPatch(BaseModel):
    """
    Apply low-level JSON Patch operations to game state.
    **When to use:**
    - Array manipulations (add/remove items from lists)
    - Complex nested updates across multiple paths
    - Bulk changes that don't have a high-level tool
    **When NOT to use:**
    - Simple character updates → use character.update instead
    - Reading state → use state.query instead
    **Example:** Add item to inventory array
    state.apply_patch({
        "entity_type": "inventory",
        "key": "player",
        "patch": [{"op": "add", "path": "/items/-", "value": {"id": "sword_01", "name": "Iron Sword"}}]
    })
    """

    name: Literal["state.apply_patch"] = "state.apply_patch"
    entity_type: str = Field(..., description="Type of entity to modify")
    key: str = Field(..., description="Entity key")
    patch: List[Patch] = Field(..., description="List of JSON Patch operations")


class StateQuery(BaseModel):
    """
    Read any game state entity (characters, inventory, quests, etc.).
    **When to use:**
    - Before making decisions that depend on current state
    - To verify facts (e.g., "Does the player have the key?")
    - To check entity properties before modifying them
    **Common patterns:**
    - Read full character: state.query({"entity_type": "character", "key": "player", "json_path": "."})
    - Read specific property: state.query({"entity_type": "character", "key": "player", "json_path": "attributes.hp_current"})
    - Get all quests: state.query({"entity_type": "quest", "key": "*", "json_path": "."})
    """

    name: Literal["state.query"] = "state.query"
    entity_type: str = Field(
        ...,
        description="Type of entity (e.g., 'character', 'inventory', 'quest', 'location')",
    )
    key: str = Field(
        ..., description="Entity key. Use '*' to get all entities of this type."
    )
    json_path: str = Field(
        ...,
        description="JSONPath expression. Use '.' for root, or 'attributes.hp' for nested properties.",
    )


class TimeNow(BaseModel):
    """
    Get the current real-world timestamp in ISO 8601 format.
    **When to use:** Logging events with real timestamps (rarely needed in gameplay).
    """

    name: Literal["time.now"] = "time.now"


class MemoryQuery(BaseModel):
    """
    Search and retrieve memories based on filters.
    **When to use:**
    - Before making decisions to recall relevant past information
    - To check what the player character knows or has experienced
    - To verify past events or facts
    **Filters:**
    - kind: Filter by memory type
    - tags: Match any of the provided tags
    - query_text: Text search within memory content
    - semantic: Use vector similarity search (slower but more relevant)
    **Example:** Find combat-related memories
    memory.query({"tags": ["combat"], "limit": 5})
    """

    name: Literal["memory.query"] = "memory.query"
    kind: Optional[str] = Field(
        None,
        description="Filter by memory kind: 'episodic', 'semantic', 'lore', or 'user_pref'",
    )
    tags: Optional[List[str]] = Field(
        None, description="Filter by tags (returns memories with any matching tag)"
    )
    query_text: Optional[str] = Field(
        None, description="Search for text within memory content"
    )
    limit: int = Field(
        5, description="Maximum number of memories to return (1-20)", ge=1, le=20
    )
    semantic: Optional[bool] = Field(
        False, description="Use semantic retrieval when true (blended with filters)"
    )
    time_query: Optional[str] = Field(
        None, description="Filter memories by fictional time (e.g., 'Day 1', 'Nightfall')"
    )


class MemoryUpdate(BaseModel):
    """
    Update an existing memory's content, priority, or tags.
    **When to use:** When information changes or becomes more/less important.
    **Example:** Increase priority of a memory that became relevant
    memory.update({"memory_id": 42, "priority": 5})
    """

    name: Literal["memory.update"] = "memory.update"
    memory_id: int = Field(..., description="The ID of the memory to update")
    content: Optional[str] = Field(None, description="New content for the memory")
    priority: Optional[int] = Field(None, description="New priority (1-5)", ge=1, le=5)
    tags: Optional[List[str]] = Field(None, description="New tags list")


class MemoryDelete(BaseModel):
    """
    Delete a memory that is no longer relevant or was incorrect.
    **When to use:** Sparingly - updating is usually better than deleting.
    **Caution:** Deleted memories cannot be recovered.
    """

    name: Literal["memory.delete"] = "memory.delete"
    memory_id: int = Field(..., description="The ID of the memory to delete")


class TimeAdvance(BaseModel):
    """
    Advance the fictional game time.
    **When to use:**
    - Scene transitions ("several hours later", "the next morning")
    - Rest/sleep periods
    - Travel montages
    - Any narrative time skip
    **Updates:**
    - Session game_time field (displayed in UI)
    - Can trigger memory associations with fictional_time
    **Example:** Skip to next day
    time.advance({
        "description": "You rest until dawn",
        "new_time": "Day 2, Morning"
    })
    """

    name: Literal["time.advance"] = "time.advance"
    description: str = Field(
        ...,
        description="Human-readable time passage (e.g., '3 hours', 'until dawn', 'to the next day')",
    )
    new_time: str = Field(
        ...,
        description="New fictional time (e.g., 'Day 2, Afternoon', 'Hour 12 of the siege')",
    )


class SchemaUpsertAttribute(BaseModel):
    """
        Creates or updates a new basic attribute for game entities during SETUP mode (Session Zero).
        **Entity types:** 'character', 'item', 'location'
        **Example:** Define a Points resource
        {
            "property_name": "Points",
            "template": "resource",
            "description": "Points than can be spent",
            "max_value": 100,
            "icon": "P",
            "regenerates": true
        }
    """

    name: Literal["schema.upsert_attribute"] = "schema.upsert_attribute"
    property_name: str = Field(
        ...,
        description="The programmatic name of the property (e.g., 'Sanity', 'Mana')",
    )
    description: str = Field(
        ..., description="A human-readable description of what the property represents"
    )
    entity_type: Literal["character", "item", "location"] = Field(
        "character", description="The type of entity this property applies to"
    )
    template: Optional[
        Literal["resource", "stat", "reputation", "flag", "enum", "string"]
    ] = Field(None, description="Predefined template to use")
    type: Optional[Literal["integer", "string", "boolean", "enum", "resource"]] = Field(
        None, description="Data type (required if no template)"
    )
    default_value: Optional[JSONValue] = Field(
        None, description="Initial value (required if no template)"
    )
    has_max: Optional[bool] = Field(
        None, description="For 'resource' types, whether there's a maximum value"
    )
    min_value: Optional[int] = Field(None, description="Minimum allowed integer value")
    max_value: Optional[int] = Field(None, description="Maximum allowed integer value")
    allowed_values: Optional[List[str]] = Field(
        None, description="For 'enum' types, list of allowed string values"
    )
    display_category: Optional[str] = Field(
        None, description="Category for UI display (e.g., 'Resources', 'Stats')"
    )
    icon: Optional[str] = Field(
        None, description="Emoji or short string to use as an icon in the UI"
    )
    display_format: Optional[Literal["number", "bar", "badge"]] = Field(
        None, description="How to display in the UI"
    )
    regenerates: Optional[bool] = Field(
        None, description="For 'resource' types, whether it regenerates over time"
    )
    regeneration_rate: Optional[int] = Field(
        None, description="For 'resource' types, regeneration rate per game turn"
    )


class EndSetupAndStartGameplay(BaseModel):
    """
    Signal the end of the SETUP game mode (Session Zero) and start the game (GAMEPLAY mode).
    **When to use:** Only when the player has explicitly requested or agreed to start the game.
    **Effect:** Transitions game mode from SETUP to GAMEPLAY and starts the game.
    """

    name: Literal["end_setup_and_start_gameplay"] = "end_setup_and_start_gameplay"
    reason: str = Field(
        ...,
        description="A brief justification for why the setup is considered complete and gameplay should begin.",
    )


class Deliberate(BaseModel):
    """
    A no-op tool that allows the AI to think or reflect without taking a concrete action.
    **When to use:**
    - When you need to consider the next step without making any changes.
    - If no other tool is appropriate for the current turn.
    - To signal that you are waiting for more information from the player.
    """

    name: Literal["deliberate"] = "deliberate"


class CharacterUpdate(BaseModel):
    """
    Update character attributes and properties with automatic validation and game logic.
    **When to use:**
    - Modifying HP, stats, conditions, or custom properties
    - Any character data changes (damage, healing, stat adjustments)
    - **Preferred over state.apply_patch** for character updates
    **Example:** Update HP and custom Sanity property
    character.update({
        "character_key": "player",
        "updates": [
            {"key": "hp_current", "value": 25},
            {"key": "sanity", "value": 80}
        ]
    })
    """

    name: Literal["character.update"] = "character.update"
    character_key: str = Field(
        ..., description="Character ID (e.g., 'player', 'npc_goblin_chief')"
    )
    updates: List[UpdatePair] = Field(
        ...,
        description="List of key-value pairs for updates. Supports core attributes (hp_current, hp_max, conditions, etc) and custom properties (str, dex, skill_spot, etc).",
    )


class SchemaQuery(BaseModel):
    """
    Query detailed information about game mechanics.
    Use this when you need to know:
    - What a specific attribute/skill/class does
    - What actions are available in combat
    - Details about game mechanics
    """

    name: Literal["schema.query"] = "schema.query"
    query_type: Literal[
        "attribute", "resource", "skill", "action_economy", "class", "race", "all"
    ]
    specific_name: Optional[str] = Field(
        None,
        description="Name of specific item to query. Leave blank for all of that type.",
    )

class NpcAdjustRelationship(BaseModel):
    """
    Adjust the relationship metrics between an NPC and another entity (usually the player).
    Use this to reflect the social outcomes of a conversation or action.
    **Example:** After a successful persuasion, increase the NPC's trust.
    npc.adjust_relationship({
        "npc_key": "town_guard_captain",
        "subject_key": "player",
        "trust_change": 2,
        "tags_to_add": ["helpful"]
    })
    """
    name: Literal["npc.adjust_relationship"] = "npc.adjust_relationship"
    npc_key: str = Field(..., description="The entity key of the NPC whose feelings are changing.")
    subject_key: str = Field(..., description="The entity key of the subject of these feelings (e.g., 'player').")
    trust_change: Optional[int] = Field(None, description="The amount to add or subtract from the trust score.")
    attraction_change: Optional[int] = Field(None, description="The amount to add or subtract from the attraction score.")
    fear_change: Optional[int] = Field(None, description="The amount to add or subtract from the fear score.")
    tags_to_add: Optional[List[str]] = Field(None, description="A list of relationship tags to add.")
    tags_to_remove: Optional[List[str]] = Field(None, description="A list of relationship tags to remove.")

class InventoryAddItem(BaseModel):
    """
    Adds an item to an entity's inventory. **Preferred over `state.apply_patch` for adding items.**
    This tool is intelligent: if the item already exists, it will increment the quantity. If not, it will create a new item entry.
    **Example:** Give the player a health potion.
    inventory.add_item({
        "owner_key": "player",
        "item_name": "Health Potion",
        "quantity": 1
    })
    """
    name: Literal["inventory.add_item"] = "inventory.add_item"
    owner_key: str = Field(..., description="The entity key of the inventory's owner (e.g., 'player', 'shopkeeper').")
    item_name: str = Field(..., description="The name of the item to add.")
    quantity: int = Field(1, description="The number of items to add.", gt=0)
    description: Optional[str] = Field(None, description="A brief description for the item if it's new.")
    properties: Optional[Dict[str, Any]] = Field(None, description="A dictionary of custom properties for the item.")


class InventoryRemoveItem(BaseModel):
    """
    Removes an item from an entity's inventory. **Preferred over `state.apply_patch` for removing items.**
    This tool is intelligent: it will decrease the item's quantity and will only remove the item entry if the quantity reaches zero.
    **Example:** The player drinks a health potion.
    inventory.remove_item({
        "owner_key": "player",
        "item_name": "Health Potion",
        "quantity": 1
    })
    """
    name: Literal["inventory.remove_item"] = "inventory.remove_item"
    owner_key: str = Field(..., description="The entity key of the inventory's owner (e.g., 'player').")
    item_name: str = Field(..., description="The name of the item to remove.")
    quantity: int = Field(1, description="The number of items to remove.", gt=0)


class QuestUpdateStatus(BaseModel):
    """
    Updates the overall status of a quest. **Preferred over `state.apply_patch` for quest status changes.**
    **Example:** The player completes the main quest.
    quest.update_status({
        "quest_key": "main_quest_01",
        "new_status": "completed"
    })
    """
    name: Literal["quest.update_status"] = "quest.update_status"
    quest_key: str = Field(..., description="The unique key of the quest to update.")
    new_status: Literal["active", "completed", "failed", "hidden"] = Field(..., description="The new status for the quest.")


class QuestUpdateObjective(BaseModel):
    """
    Updates the completion status of a specific quest objective. **Preferred over `state.apply_patch` for objective changes.**
    The tool finds the objective based on its descriptive text.
    **Example:** Mark the 'Find the goblin camp' objective as complete.
    quest.update_objective({
        "quest_key": "main_quest_01",
        "objective_text": "Find the goblin camp",
        "is_completed": true
    })
    """
    name: Literal["quest.update_objective"] = "quest.update_objective"
    quest_key: str = Field(..., description="The unique key of the quest to update.")
    objective_text: str = Field(..., description="The descriptive text of the objective to update. Must be an exact match.")
    is_completed: bool = Field(True, description="The new completion status for the objective.")


class EntityCreate(BaseModel):
    """
    Dynamically creates a new entity in the game world.
    Use this to introduce new characters (NPCs), items, locations, or quests that don't exist yet.
    The `data` provided MUST conform to the schema established during the SETUP phase.
    **Example:** Create a new goblin NPC that the player encounters.
    entity.create({
        "entity_type": "character",
        "entity_key": "goblin_scout_01",
        "data": {
            "name": "Gribble",
            "attributes": {"hp_current": 7, "hp_max": 7},
            "location_key": "whispering_woods_path"
        }
    })
    """
    name: Literal["entity.create"] = "entity.create"
    entity_type: str = Field(..., description="The type of the entity to create (e.g., 'character', 'item', 'location', 'quest').")
    entity_key: str = Field(..., description="A unique key for the new entity (e.g., 'goblin_scout_01', 'potion_of_healing_3').")
    data: Dict[str, Any] = Field(..., description="A dictionary containing the full data for the new entity.")
