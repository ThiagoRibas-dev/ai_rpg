# TODO - Dynamic AI-Defined Game Mechanics

**Project Goal:** Evolve the AI-RPG engine from fixed rules to dynamic, AI-defined mechanics through collaborative "Session Zero" worldbuilding, combined with async UX improvements and robust schema validation.

---

## 📊 Progress Overview

- [x] **Phase 1:** Foundation (Hybrid Schema + Session Zero) - 12/12 tasks
- [x] **Phase 2:** Async UX (Responsive UI) - 8/8 tasks
- [ ] **Phase 3:** High-Level Tools (Schema-Aware Operations) - 0/10 tasks
- [ ] **Phase 4:** Polish (Export, Validation, UI) - 0/8 tasks


---

## 🎯 Success Criteria

### Milestone 1: Working Session Zero (Phase 1)
- [ ] Can start a new game and enter "SETUP" mode
- [ ] AI can define a custom property (e.g., "Sanity: 0-100")
- [ ] Property is stored in database and persists across restarts
- [ ] Mode switches to "GAMEPLAY" after `schema.finalize`
- [ ] Custom property appears in system prompt during gameplay
- [ ] AI uses the custom property in narrative and mechanics

### Milestone 2: Responsive UI (Phase 2)
- [ ] Main window never freezes during AI turns (can resize, interact)
- [ ] Loading indicator shows during background processing
- [ ] Can cancel mid-turn without crashing
- [ ] Thought bubbles, tool calls, and narrative appear progressively

### Milestone 3: Validated Tools (Phase 3)
- [ ] `character.update` validates property types against schema
- [ ] Invalid updates (wrong type, out of range) fail gracefully
- [ ] State inspector displays custom properties dynamically
- [ ] Game logic hooks fire correctly (e.g., death at 0 HP)

### Milestone 4: Community Features (Phase 4)
- [ ] Can export schema to JSON file
- [ ] Can import schema into a new session
- [ ] Schema validation warns about potential issues
- [ ] Includes 3 example schemas (Fantasy, Horror, Cyberpunk)

---

## 📋 PHASE 1: Foundation

**Goal:** Implement hybrid schema system and Session Zero mode.

### Data Models & Schema Storage

#### Task 1.1: Create Entity Models with Properties Field
- [x] **Create** `app/models/entities.py`
  - [x] Define `CharacterAttributes` Pydantic model
    ```python
    class CharacterAttributes(BaseModel):
        hp_current: int
        hp_max: int
        # Add other core stats as needed
    ```
  - [x] Define `Character` Pydantic model with `properties: Dict[str, Any]`
    ```python
    class Character(BaseModel):
        key: str
        name: str
        attributes: CharacterAttributes
        conditions: List[str] = Field(default_factory=list)
        location_key: str
        inventory_key: str
        properties: Dict[str, Any] = Field(default_factory=dict)
    ```
  - [x] Define `Item` model with `properties` field
  - [x] Define `Location` model with `properties` field
  
  **Acceptance Criteria:**
  - Models pass Pydantic validation
  - Can instantiate with `properties={"Sanity": 100}`
  - `model_dump()` includes properties dict

  **Estimated Time:** 2-3 hours

---

#### Task 1.2: Create PropertyDefinition Schema
- [x] **Create** `app/models/property_definition.py`
  - [x] Define `PropertyDefinition` Pydantic model
    ```python
    class PropertyDefinition(BaseModel):
        name: str
        type: Literal["integer", "string", "boolean", "enum", "resource"]
        description: str
        default_value: Any
        has_max: bool = False
        min_value: Optional[int] = None
        max_value: Optional[int] = None
        allowed_values: Optional[List[str]] = None  # For enum
        display_category: str = "Custom"
        icon: Optional[str] = None
        display_format: Literal["number", "bar", "badge"] = "number"
        regenerates: bool = False
        regeneration_rate: Optional[int] = None
    ```
  - [x] Add validation logic (e.g., `min_value < max_value`)
  
  **Acceptance Criteria:**
  - Can create definitions for all types (integer, resource, enum, etc.)
  - Validation catches invalid configs (e.g., `min_value > max_value`)
  - JSON serialization works via `model_dump()`

  **Estimated Time:** 1-2 hours

---

#### Task 1.3: Add schema_extensions Table
- [x] **Modify** `app/database/db_manager.py`
  - [x] Add table creation in `create_tables()`:
    ```sql
    CREATE TABLE IF NOT EXISTS schema_extensions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        property_name TEXT NOT NULL,
        definition TEXT NOT NULL,  -- JSON of PropertyDefinition
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
        UNIQUE(session_id, entity_type, property_name)
    )
    ```
  - [x] Add index: `CREATE INDEX IF NOT EXISTS idx_schema_extensions ON schema_extensions(session_id, entity_type)`
  
  **Acceptance Criteria:**
  - Table created on first run
  - Unique constraint prevents duplicate property names per session
  - Foreign key cascade deletes schema when session deleted

  **Estimated Time:** 30 minutes

---

#### Task 1.4: Implement Schema Extension DB Methods
- [x] **Modify** `app/database/db_manager.py`
  - [x] Add `create_schema_extension(session_id, entity_type, property_name, definition_dict)`
  - [x] Add `get_schema_extensions(session_id, entity_type) -> Dict[str, PropertyDefinition]`
  - [x] Add `delete_schema_extension(session_id, entity_type, property_name)`
  - [x] Add `get_all_schema_extensions(session_id) -> Dict[str, Dict[str, PropertyDefinition]]`
    - Returns `{"character": {"Sanity": {...}}, "item": {...}}`
  
  **Acceptance Criteria:**
  - Can insert, retrieve, and delete schema definitions
  - `get_schema_extensions` returns dict of PropertyDefinition objects
  - Works across sessions (session A's schema doesn't affect session B)

  **Estimated Time:** 2 hours

  **Test:**
  ```python
  # In test_state.py or new test file
  def test_schema_extensions():
      with DBManager(DB_PATH) as db:
          session = db.save_session("Test", "{}", 1)
          
          # Create definition
          sanity_def = PropertyDefinition(
              name="Sanity",
              type="resource",
              description="Mental fortitude",
              default_value=100,
              has_max=True,
              max_value=100
          )
          db.create_schema_extension(session.id, "character", "Sanity", sanity_def.model_dump())
          
          # Retrieve
          schema = db.get_schema_extensions(session.id, "character")
          assert "Sanity" in schema
          assert schema["Sanity"]["max_value"] == 100
  ```

---

### Session Zero Tools & Orchestrator Logic

#### Task 1.5: Create Property Templates
- [x] **Create** `app/tools/builtin/property_templates.py`
  - [x] Define `PROPERTY_TEMPLATES` dict:
    ```python
    PROPERTY_TEMPLATES = {
        "resource": PropertyDefinition(
            type="resource",
            has_max=True,
            min_value=0,
            display_format="bar",
            display_category="Resources"
        ),
        "stat": PropertyDefinition(...),
        "reputation": PropertyDefinition(...),
        "flag": PropertyDefinition(...)
    }
    ```
  - [x] Add helper function `apply_template(template_name: str, overrides: dict) -> PropertyDefinition`

  **Acceptance Criteria:**
  - 4 templates defined (resource, stat, reputation, flag)
  - `apply_template("resource", {"name": "Sanity"})` merges correctly
  
  **Estimated Time:** 1 hour

---

#### Task 1.6: Implement schema.define_property Tool
- [x] **Create** `app/tools/builtin/schema_define_property.py`
  - [x] Define schema dict with parameters
  - [x] Implement handler:
    ```python
    def handler(
        name: str,
        description: str,
        template: Optional[str] = None,
        type: Optional[str] = None,
        default_value: Any = None,
        **overrides,
        **context
    ) -> dict:
        session_id = context["session_id"]
        db = context["db_manager"]
        
        # Apply template if provided
        if template:
            prop_def = apply_template(template, {"name": name, ...})
        else:
            prop_def = PropertyDefinition(name=name, type=type, ...)
        
        # Merge overrides
        ...
        
        # Save to DB
        db.create_schema_extension(session_id, "character", name, prop_def.model_dump())
        
        return {"success": True, "property": prop_def.model_dump()}
    ```
  
  **Acceptance Criteria:**
  - Works with templates: `schema.define_property({"name": "Sanity", "template": "resource"})`
  - Works without templates: `schema.define_property({"name": "CustomProp", "type": "integer", ...})`
  - Validates against PropertyDefinition schema
  - Saves to database

  **Estimated Time:** 3 hours

---

#### Task 1.7: Implement schema.finalize Tool
- [x] **Create** `app/tools/builtin/schema_finalize.py`
  - [x] Simple handler that returns `{"setup_complete": True}`
  - [x] No database changes needed (orchestrator listens for this result)
  
  **Acceptance Criteria:**
  - Returns success flag
  - Registered in tool registry

  **Estimated Time:** 15 minutes

---

#### Task 1.8: Add Pydantic Schemas for New Tools
- [x] **Modify** `app/tools/schemas.py`
  - [x] Add `SchemaDefineProperty(BaseModel)` class
  - [x] Add `SchemaFinalize(BaseModel)` class
  - [x] Update `_TOOL_SCHEMA_MAP` in `app/tools/registry.py`

  **Acceptance Criteria:**
  - Schemas validate tool arguments
  - Tools appear in `registry.get_all_schemas()`

  **Estimated Time:** 1 hour

---

#### Task 1.9: Add game_mode Field to GameSession
- [x] **Modify** `app/models/game_session.py`
  - [x] Add `game_mode: str = "SETUP"` field
  
- [x] **Modify** `app/database/db_manager.py`
  - [x] Add `game_mode` column to sessions table:
    ```sql
    ALTER TABLE sessions ADD COLUMN game_mode TEXT DEFAULT 'SETUP'
    ```
  - [x] Update `load_session()`, `save_session()`, `update_session()` to handle field

  **Acceptance Criteria:**
  - New sessions default to "SETUP"
  - Mode persists across save/load
  - Can query `session.game_mode` in orchestrator

  **Estimated Time:** 1 hour

  **Migration Note:**
  ```python
  # In db_manager.py create_tables()
  # Add migration logic for existing databases
  try:
      cursor = self.conn.execute("SELECT game_mode FROM sessions LIMIT 1")
  except sqlite3.OperationalError:
      # Column doesn't exist, add it
      self.conn.execute("ALTER TABLE sessions ADD COLUMN game_mode TEXT DEFAULT 'SETUP'")
  ```

---

#### Task 1.10: Implement Mode-Switching in Orchestrator
- [x] **Modify** `app/core/orchestrator.py`
  - [x] In `plan_and_execute()`, add mode check:
    ```python
    if session.game_mode == "SETUP":
        system_prompt = self._build_session_zero_prompt()
        available_tools = self._filter_tools(["schema.define_property", "schema.finalize"])
    else:  # GAMEPLAY
        system_prompt = self._build_gameplay_prompt(session)
        available_tools = self.tool_registry.get_all_schemas()
    ```
  - [x] Listen for `schema.finalize` in tool results:
    ```python
    for result in tool_results:
        if result["tool_name"] == "schema.finalize":
            session.game_mode = "GAMEPLAY"
            self.db_manager.update_session(session)
            self.view.add_message_bubble("system", "✅ Session Zero complete! Game starting...")
    ```

  **Acceptance Criteria:**
  - SETUP mode limits tools to schema.* only
  - GAMEPLAY mode has full tool access
  - Transition happens after `schema.finalize`
  - Mode change persists to database

  **Estimated Time:** 2 hours

---

### Context Injection & Testing

#### Task 1.11: Create Session Zero System Prompt
- [x] **Modify** `app/core/llm/prompts.py`
  - [x] Add `SESSION_ZERO_TEMPLATE`:
    ```python
    SESSION_ZERO_TEMPLATE = """
    You are a collaborative Game Master helping design a custom RPG system.
    
    # YOUR ROLE
    Work with the player to establish:
    1. Genre and setting (fantasy, sci-fi, horror, etc.)
    2. Core themes and tone
    3. Special mechanics unique to this world
    
    # CUSTOM PROPERTIES
    Use templates to define game mechanics efficiently:
    
    **TEMPLATES:**
    - "resource": HP-like attributes (current/max, regenerates)
      Example: Sanity, Mana, Stamina
    - "stat": Ability scores (1-20 range)
      Example: Strength, Intelligence
    - "reputation": Faction standing (-100 to +100)
      Example: Guild Reputation, Street Cred
    - "flag": Boolean states
      Example: Is Infected, Has Clearance
    
    **EXAMPLES:**
    
    Horror Game:
    schema.define_property({
        "name": "Sanity",
        "template": "resource",
        "description": "Mental fortitude against cosmic horrors",
        "max_value": 100,
        "icon": "🧠",
        "regenerates": true,
        "regeneration_rate": 5
    })
    
    Cyberpunk:
    schema.define_property({
        "name": "Humanity",
        "template": "resource",
        "description": "Decreases with cyberware implants",
        "max_value": 10,
        "icon": "💙"
    })
    
    Fantasy:
    schema.define_property({
        "name": "Mana",
        "template": "resource",
        "description": "Magical energy for spellcasting",
        "max_value": 50,
        "icon": "✨",
        "regenerates": true
    })
    
    # WORKFLOW
    1. Ask player about their desired genre/setting
    2. Suggest 3-5 custom properties that fit the theme
    3. Define each using schema.define_property
    4. Ask if player wants to add/modify anything
    5. When ready, call schema.finalize to begin the adventure
    
    Available tools: {tool_schemas}
    """
    ```

  **Acceptance Criteria:**
  - Clear instructions for AI
  - Includes all template types with examples
  - Has concrete workflow steps

  **Estimated Time:** 1 hour

---

#### Task 1.12: Inject Custom Rules into Gameplay Prompts
- [x] **Modify** `app/core/context/context_builder.py`
  - [x] Add method `_get_formatted_custom_rules(session_id) -> str`
    ```python
    def _get_formatted_custom_rules(self, session_id: int) -> str:
        if not session_id:
            return ""
        
        schema_extensions = self.db.get_all_schema_extensions(session_id)
        if not schema_extensions:
            return ""
        
        lines = ["# CUSTOM GAME MECHANICS", ""]
        for entity_type, properties in schema_extensions.items():
            if not properties:
                continue
            
            lines.append(f"## {entity_type.title()}")
            for prop_name, prop_def in properties.items():
                icon = prop_def.get("icon", "")
                desc = prop_def.get("description", "")
                type_str = prop_def.get("type", "")
                
                # Format based on type
                if prop_def.get("has_max"):
                    range_str = f"(0-{prop_def.get('max_value', '?')})"
                elif prop_def.get("min_value") is not None or prop_def.get("max_value") is not None:
                    min_v = prop_def.get("min_value", "?")
                    max_v = prop_def.get("max_value", "?")
                    range_str = f"({min_v} to {max_v})"
                else:
                    range_str = ""
                
                lines.append(f"- **{icon} {prop_name}** {range_str}: {desc}")
            
            lines.append("")
        
        return "\n".join(lines)
    ```
  
  - [x] Modify `assemble()` to inject rules after base template:
    ```python
    def assemble(self, base_template: str, session, chat_history):
        sections = [base_template]
        
        # Inject custom rules FIRST (high priority)
        if session.id:
            custom_rules = self._get_formatted_custom_rules(session.id)
            if custom_rules:
                sections.append(custom_rules)
        
        # ... rest of context (state, memories, etc.)
    ```

  **Acceptance Criteria:**
  - Custom rules appear in every GAMEPLAY turn's system prompt
  - Formatted clearly with icons and descriptions
  - Empty string if no custom properties defined

  **Estimated Time:** 2 hours

---

#### Task 1.13: End-to-End Session Zero Test
- [x] **Create** `tests/test_session_zero.py`
  - [x] Test creates new session
  - [x] Verifies `game_mode == "SETUP"`
  - [x] Calls `schema.define_property` with "Sanity" resource
  - [x] Verifies definition saved to DB
  - [x] Calls `schema.finalize`
  - [x] Verifies `game_mode == "GAMEPLAY"`
  - [x] Verifies custom rules appear in next prompt

  **Acceptance Criteria:**
  - All steps pass without errors
  - Custom property persists across session reload
  - Prompt injection verified

  **Estimated Time:** 2 hours

---

## 📋 PHASE 2: Async UX 

**Goal:** Make UI responsive during AI processing using background threads and message queues.

### Threading Infrastructure

#### Task 2.1: Add UI Queue to Orchestrator
- [x] **Modify** `app/core/orchestrator.py`
  - [x] Import `import queue, threading`
  - [x] Add in `__init__`: `self.ui_queue = queue.Queue()`
  - [x] Replace direct UI calls with queue messages:
    ```python
    # OLD:
    self.view.add_thought_bubble(plan.thought)
    
    # NEW:
    self.ui_queue.put({"type": "thought_bubble", "content": plan.thought})
    ```
  - [x] Define message types: `thought_bubble`, `tool_call`, `tool_result`, `narrative`, `choices`, `error`, `turn_complete`

  **Acceptance Criteria:**
  - All UI updates go through queue
  - No direct `self.view.*` calls in `plan_and_execute()`

  **Estimated Time:** 2 hours

---

#### Task 2.2: Refactor Orchestrator for Thread-Local DB
- [x] **Modify** `app/core/orchestrator.py`
  - [x] Change `__init__` signature:
    ```python
    def __init__(self, view: MainView, db_path: str):  # Store path, not manager
        self.view = view
        self.db_path = db_path
        self.ui_queue = queue.Queue()
        # ... services that don't need DB ...
    ```
  - [x] Create `_background_execute()`:
    ```python
    def _background_execute(self, session_snapshot):
        try:
            # Thread-local DB connection
            with DBManager(self.db_path) as thread_db:
                # Recreate services with thread DB
                context = {
                    "session_id": session_snapshot.id,
                    "db_manager": thread_db,
                    "vector_store": self.vector_store,  # Thread-safe
                    ...
                }
                
                # Run turn logic
                self._plan_and_execute_impl(session_snapshot, context)
                
        except Exception as e:
            logger.error(f"Turn failed: {e}", exc_info=True)
            self.ui_queue.put({"type": "error", "message": str(e)})
        finally:
            self.ui_queue.put({"type": "turn_complete"})
    ```

  **Acceptance Criteria:**
  - Each thread creates its own DBManager context
  - No shared DB connections between threads
  - Errors are caught and sent to UI queue

  **Estimated Time:** 3 hours

  **⚠️ CRITICAL:** Test with multiple rapid turns to verify no DB locking

---

#### Task 2.3: Create plan_and_execute Wrapper
- [x] **Modify** `app/core/orchestrator.py`
  - [x] Refactor existing logic into `_plan_and_execute_impl(session, context)`
  - [x] New public method:
    ```python
    def plan_and_execute(self, session):
        # Create snapshot (avoid shared state issues)
        session_snapshot = Session.from_json(session.to_json())
        session_snapshot.id = session.id
        
        # Start background thread
        thread = threading.Thread(
            target=self._background_execute,
            args=(session_snapshot,),
            daemon=True,
            name=f"Turn-{session.id}"
        )
        thread.start()
    ```

  **Acceptance Criteria:**
  - Returns immediately (doesn't block)
  - Thread runs in background
  - Session snapshot prevents race conditions

  **Estimated Time:** 1 hour

---

#### Task 2.4: Update Main Entry Point
- [x] **Modify** `main.py`
  - [x] Change orchestrator initialization:
    ```python
    # OLD:
    orchestrator = Orchestrator(view, db_manager)
    
    # NEW:
    orchestrator = Orchestrator(view, DB_PATH)
    ```

  **Acceptance Criteria:**
  - App launches without errors
  - Orchestrator receives path, not manager

  **Estimated Time:** 5 minutes

---

### UI Queue Processing & Feedback

#### Task 2.5: Implement UI Queue Polling
- [x] **Modify** `app/gui/main_view.py`
  - [x] Add method:
    ```python
    def _process_ui_queue(self):
        try:
            while True:  # Process all pending messages
                msg = self.orchestrator.ui_queue.get_nowait()
                self._handle_ui_message(msg)
        except queue.Empty:
            pass
        finally:
            # Re-schedule polling
            self.after(100, self._process_ui_queue)
    ```
  - [x] Start polling in `__init__`:
    ```python
    def __init__(self, db_manager):
        super().__init__()
        # ... setup ...
        self.after(100, self._process_ui_queue)  # Start polling
    ```

  **Acceptance Criteria:**
  - Polling starts on app launch
  - Processes all queued messages before sleeping
  - Re-schedules itself

  **Estimated Time:** 1 hour

---

#### Task 2.6: Implement Message Handler
- [x] **Modify** `app/gui/main_view.py`
  - [x] Add method:
    ```python
    def _handle_ui_message(self, msg: dict):
        msg_type = msg.get("type")
        
        if msg_type == "thought_bubble":
            self.add_thought_bubble(msg["content"])
        
        elif msg_type == "tool_call":
            self.add_tool_call(msg["name"], msg["args"])
        
        elif msg_type == "tool_result":
            self.add_tool_result(msg["result"], msg.get("is_error", False))
        
        elif msg_type == "narrative":
            self.add_message_bubble("assistant", msg["content"])
        
        elif msg_type == "choices":
            self.display_action_choices(msg["choices"])
        
        elif msg_type == "error":
            self.add_message_bubble("system", f"❌ Error: {msg['message']}")
        
        elif msg_type == "turn_complete":
            self.send_button.configure(state="normal")  # Re-enable
        
        else:
            logger.warning(f"Unknown UI message type: {msg_type}")
    ```

  **Acceptance Criteria:**
  - All message types handled
  - Unknown types logged but don't crash

  **Estimated Time:** 1 hour

---

#### Task 2.7: Add Turn State Management
- [x] **Modify** `app/gui/main_view.py`
  - [x] Modify `handle_send_button`:
    ```python
    def handle_send_button(self):
        if not self.selected_session:
            return
        
        # Disable to prevent concurrent turns
        self.send_button.configure(state="disabled")
        
        # Clear previous choices
        for widget in self.choice_button_frame.winfo_children():
            widget.destroy()
        self.choice_button_frame.grid_remove()
        
        # Start turn (non-blocking)
        self.orchestrator.plan_and_execute(self.selected_session)
    ```

  **Acceptance Criteria:**
  - Send button disabled during turn
  - Re-enabled on `turn_complete` message
  - Can't trigger concurrent turns

  **Estimated Time:** 30 minutes

---

#### Task 2.8: Add Loading Indicator
- [x] **Modify** `app/gui/main_view.py`
  - [x] Add to `__init__`:
    ```python
    self.loading_frame = ctk.CTkFrame(self.main_panel, fg_color=Theme.colors.bg_tertiary)
    self.loading_label = ctk.CTkLabel(
        self.loading_frame,
        text="🤔 AI is thinking...",
        font=Theme.fonts.subheading
    )
    self.loading_label.pack(pady=10)
    # Don't pack frame yet - show/hide on demand
    ```
  
  - [x] Modify `_handle_ui_message`:
    ```python
    if msg_type == "thought_bubble":
        self.loading_frame.pack(fill="x", pady=5)  # Show loading
        self.add_thought_bubble(msg["content"])
    
    elif msg_type == "turn_complete":
        self.loading_frame.pack_forget()  # Hide loading
        self.send_button.configure(state="normal")
    ```

  **Acceptance Criteria:**
  - Loading indicator appears when turn starts
  - Disappears when turn completes
  - Visually distinct from chat bubbles

  **Estimated Time:** 1 hour

---

#### Task 2.9: Test Responsiveness
- [x] **Manual Testing**
  - [x] Start a turn, try to resize window (should be smooth)
  - [x] Start a turn, try to scroll chat history (should work)
  - [x] Start a turn, try to switch sessions (should be prevented or warned)
  - [x] Trigger error mid-turn, verify error message appears
  - [x] Send 3 rapid turns, verify they don't overlap

  **Acceptance Criteria:**
  - Window never freezes
  - All UI interactions work during AI processing
  - No crashes or DB lock errors

  **Estimated Time:** 2 hours

---

## 📋 PHASE 3: High-Level Tools

**Goal:** Create schema-aware, validated tools that protect core state.

### Character Update Tool

#### Task 3.1: Implement character.update Schema
- [ ] **Modify** `app/tools/schemas.py`
  - [ ] Add class:
    ```python
    class CharacterUpdate(BaseModel):
        """Update character attributes and properties with validation."""
        name: Literal["character.update"] = "character.update"
        character_key: str = Field(..., description="Character ID (e.g., 'player')")
        updates: Dict[str, Any] = Field(..., description="Fields to update. Can include core attributes (hp_current) or custom properties (Sanity).")
    ```

  **Acceptance Criteria:**
  - Schema validates correctly
  - Updates dict accepts any structure

  **Estimated Time:** 15 minutes

---

#### Task 3.2: Implement character.update Handler
- [ ] **Create** `app/tools/builtin/character_update.py`
  - [ ] Implement handler with validation:
    ```python
    def handler(character_key: str, updates: Dict[str, Any], **context) -> dict:
        session_id = context["session_id"]
        db = context["db_manager"]
        
        # Load entity
        from app.tools.builtin._state_storage import get_entity, set_entity
        char_data = get_entity(session_id, db, "character", character_key)
        
        if not char_data:
            raise ValueError(f"Character '{character_key}' not found")
        
        # Load into Pydantic model for validation
        from app.models.entities import Character
        try:
            char = Character(**char_data)
        except Exception as e:
            raise ValueError(f"Invalid character data: {e}")
        
        # Load schema definitions
        schema_defs = db.get_schema_extensions(session_id, "character")
        
        # Apply updates with validation
        for key, value in updates.items():
            if _is_core_attribute(char, key):
                _update_core_attribute(char, key, value)
            else:
                _update_custom_property(char, key, value, schema_defs)
        
        # Game logic hooks
        _apply_game_logic(char)
        
        # Save back
        version = set_entity(session_id, db, "character", character_key, char.model_dump())
        
        return {
            "success": True,
            "character_key": character_key,
            "updated_fields": list(updates.keys()),
            "version": version
        }
    ```
  
  - [ ] Implement helper functions:
    ```python
    def _is_core_attribute(char: Character, key: str) -> bool:
        # Check if it's a field in Character or CharacterAttributes
        return key in char.__fields__ or key in char.attributes.__fields__
    
    def _update_core_attribute(char: Character, key: str, value: Any):
        if key in char.attributes.__fields__:
            setattr(char.attributes, key, value)
        else:
            setattr(char, key, value)
    
    def _update_custom_property(char: Character, key: str, value: Any, schema_defs: dict):
        if key not in schema_defs:
            # Unknown property - allow but warn
            logger.warning(f"Setting undefined custom property: {key}")
            char.properties[key] = value
            return
        
        prop_def = schema_defs[key]
        
        # Type validation
        expected_type = _get_python_type(prop_def["type"])
        if not isinstance(value, expected_type):
            raise TypeError(f"{key} must be {prop_def['type']}, got {type(value).__name__}")
        
        # Range validation
        if "min_value" in prop_def and value < prop_def["min_value"]:
            raise ValueError(f"{key} cannot be less than {prop_def['min_value']}")
        
        if "max_value" in prop_def and value > prop_def["max_value"]:
            raise ValueError(f"{key} cannot exceed {prop_def['max_value']}")
        
        # Enum validation
        if prop_def["type"] == "enum" and value not in prop_def["allowed_values"]:
            raise ValueError(f"{key} must be one of {prop_def['allowed_values']}")
        
        char.properties[key] = value
    
    def _get_python_type(type_str: str) -> type:
        return {
            "integer": int,
            "string": str,
            "boolean": bool,
            "enum": str,
            "resource": int
        }.get(type_str, object)
    
    def _apply_game_logic(char: Character):
        # Death detection
        if char.attributes.hp_current <= 0:
            if "unconscious" not in char.conditions:
                char.conditions.append("unconscious")
            if char.attributes.hp_current <= -char.attributes.hp_max:
                if "dead" not in char.conditions:
                    char.conditions.append("dead")
        else:
            # Remove death conditions if healed
            char.conditions = [c for c in char.conditions if c not in ("unconscious", "dead")]
    ```

  **Acceptance Criteria:**
  - Can update core attributes: `{"hp_current": 25}`
  - Can update custom properties: `{"Sanity": 80}`
  - Type validation works (rejects `{"hp_current": "lots"}`)
  - Range validation works (rejects `{"Sanity": 999}` if max is 100)
  - Death detection adds "unconscious" condition at 0 HP

  **Estimated Time:** 4 hours

---

#### Task 3.3: Register character.update Tool
- [ ] **Modify** `app/tools/registry.py`
  - [ ] Add to `_TOOL_SCHEMA_MAP`: `"character.update": tool_schemas.CharacterUpdate`

  **Acceptance Criteria:**
  - Tool appears in registry
  - Schema transforms correctly for LLM

  **Estimated Time:** 5 minutes

---

#### Task 3.4: Add Tool Usage Guidelines to Prompts
- [ ] **Modify** `app/core/llm/prompts.py`
  - [ ] Add section to `PLAN_TEMPLATE`:
    ```python
    TOOL_USAGE_GUIDELINES = """
    # TOOL SELECTION GUIDE
    
    **Prefer high-level tools for common operations:**
    - character.update - Modify HP, stats, conditions, or custom properties
      Example: character.update({"character_key": "player", "updates": {"hp_current": 25, "Sanity": 80}})
    
    - state.query - Read any game state
      Example: state.query({"entity_type": "character", "key": "player", "json_path": "."})
    
    **Use low-level tools only for complex operations:**
    - state.apply_patch - Batch updates, array manipulations, nested paths
      Example: Adding item to inventory array
    
    **Validation:**
    High-level tools validate types and ranges automatically. Use them to prevent errors!
    """
    ```

  **Acceptance Criteria:**
  - Guidelines are clear and concise
  - Include concrete examples

  **Estimated Time:** 30 minutes

---

### Additional High-Level Tools

#### Task 3.5: Implement character.move Tool
- [ ] **Create** `app/tools/builtin/character_move.py`
  - [ ] Handler updates `location_key` field
  - [ ] Triggers location-based events (entering/leaving)
  - [ ] Returns old and new locations

  **Acceptance Criteria:**
  - `character.move({"character_key": "player", "destination": "ancient_library"})` works
  - Character's location_key updated in DB

  **Estimated Time:** 2 hours

---

#### Task 3.6: Implement item.transfer Tool
- [ ] **Create** `app/tools/builtin/item_transfer.py`
  - [ ] Handler moves items between inventories
  - [ ] Validates item exists in source
  - [ ] Checks destination capacity
  - [ ] Updates both inventory entities

  **Acceptance Criteria:**
  - Can move item from player to container
  - Validates source has item
  - Respects inventory slot limits

  **Estimated Time:** 3 hours

---

#### Task 3.7: Implement character.add_condition Tool
- [ ] **Create** `app/tools/builtin/character_add_condition.py`
  - [ ] Handler adds to conditions array
  - [ ] Prevents duplicates
  - [ ] Optional duration tracking

  **Acceptance Criteria:**
  - `character.add_condition({"character_key": "player", "condition": "poisoned"})` works
  - Duplicate conditions prevented

  **Estimated Time:** 1 hour

---

### State Inspector Updates

#### Task 3.8: Update Character Inspector for Properties
- [ ] **Modify** `app/gui/state_inspector_views.py` → `CharacterInspectorView`
  - [ ] Add section after core attributes:
    ```python
    # Custom properties section
    properties = self.character_data.get("properties", {})
    if properties:
        prop_frame = ctk.CTkFrame(self.scroll_frame)
        prop_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            prop_frame,
            text="⚙️ Custom Properties",
            font=Theme.fonts.body,
            anchor="w"
        ).pack(fill="x", padx=5, pady=5)
        
        for key, value in properties.items():
            self._add_key_value(prop_frame, key, str(value))
    ```

  **Acceptance Criteria:**
  - Custom properties appear in dedicated section
  - Uses same display style as core attributes

  **Estimated Time:** 1 hour

---

#### Task 3.9: Create Schema Viewer Tab
- [ ] **Modify** `app/gui/main_view.py`
  - [ ] Add "Schema" tab to `game_state_inspector_tabs`
  - [ ] Create `SchemaInspectorView` class:
    ```python
    class SchemaInspectorView(ctk.CTkFrame):
        def refresh(self):
            if not self.orchestrator or not self.orchestrator.session:
                return
            
            session_id = self.orchestrator.session.id
            
            # Load all schema extensions
            with DBManager(self.orchestrator.db_path) as db:
                all_schemas = db.get_all_schema_extensions(session_id)
            
            # Display by entity type
            for entity_type, properties in all_schemas.items():
                self._render_entity_schema(entity_type, properties)
        
        def _render_entity_schema(self, entity_type, properties):
            # Show property cards with icon, type, range, description
            ...
    ```

  **Acceptance Criteria:**
  - Shows all defined custom properties
  - Displays type, range, icon, description
  - Updates when schema changes

  **Estimated Time:** 3 hours

---

#### Task 3.10: Test Tool Validation
- [ ] **Create** `tests/test_character_update.py`
  - [ ] Test valid update succeeds
  - [ ] Test type mismatch fails gracefully
  - [ ] Test range violation fails gracefully
  - [ ] Test enum violation fails gracefully
  - [ ] Test death logic triggers correctly

  **Acceptance Criteria:**
  - All validation cases covered
  - Error messages are clear
  - No crashes on invalid input

  **Estimated Time:** 2 hours

---

## 📋 PHASE 4: Polish

**Goal:** Export/import, validation warnings, UI polish.

### Schema Export/Import

#### Task 4.1: Implement Schema Export
- [ ] **Create** `app/tools/builtin/schema_export.py` (or add to `schema_management.py`)
  - [ ] Function:
    ```python
    def export_schema(session_id: int, db_manager) -> dict:
        all_schemas = db_manager.get_all_schema_extensions(session_id)
        
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "schemas": all_schemas
        }
        
        return export_data
    ```

  **Acceptance Criteria:**
  - Returns JSON-serializable dict
  - Includes version and timestamp

  **Estimated Time:** 1 hour

---

#### Task 4.2: Implement Schema Import
- [ ] **Create** import function:
    ```python
    def import_schema(session_id: int, db_manager, schema_data: dict):
        if schema_data.get("version") != "1.0":
            raise ValueError("Incompatible schema version")
        
        schemas = schema_data.get("schemas", {})
        
        for entity_type, properties in schemas.items():
            for prop_name, prop_def in properties.items():
                db_manager.create_schema_extension(
                    session_id, entity_type, prop_name, prop_def
                )
    ```

  **Acceptance Criteria:**
  - Can import exported schemas
  - Validates version compatibility
  - Handles conflicts gracefully

  **Estimated Time:** 1 hour

---

#### Task 4.3: Add Export/Import UI
- [ ] **Modify** `app/gui/main_view.py` (or create dialog)
  - [ ] Add buttons to control panel or schema inspector
  - [ ] Export triggers file save dialog
  - [ ] Import triggers file open dialog

  **Acceptance Criteria:**
  - Can export to `.json` file
  - Can import from file
  - Shows success/error messages

  **Estimated Time:** 2 hours

---

#### Task 4.4: Create Example Schemas
- [ ] **Create** `examples/schemas/` directory
  - [ ] `fantasy.json` - HP, Mana, Stamina
  - [ ] `horror.json` - Sanity, Corruption, Fear
  - [ ] `cyberpunk.json` - Humanity, Street Cred, Heat, Neural Load

  **Acceptance Criteria:**
  - 3 complete example schemas
  - Each has 4-6 custom properties
  - Well-documented with descriptions

  **Estimated Time:** 2 hours

---

### Validation & Final Testing

#### Task 4.5: Implement Schema Validation
- [ ] **Create** `app/tools/builtin/schema_validate.py`
  - [ ] Function checks for:
    - Name collisions with core schema
    - Orphaned `has_max` properties
    - Unreasonable ranges (e.g., max > 10000)
    - Missing required fields
  - [ ] Returns list of warnings

  **Acceptance Criteria:**
  - Detects all validation issues
  - Returns actionable warnings

  **Estimated Time:** 2 hours

---

#### Task 4.6: Add Validation to Session Zero
- [ ] **Modify** `app/core/orchestrator.py`
  - [ ] After `schema.finalize`, run validation:
    ```python
    if result["tool_name"] == "schema.finalize":
        # Validate before finalizing
        warnings = validate_schema(db.get_all_schema_extensions(session.id, "character"))
        
        if warnings:
            self.ui_queue.put({
                "type": "system_message",
                "content": "⚠️ Schema Warnings:\n" + "\n".join(warnings)
            })
    ```

  **Acceptance Criteria:**
  - Warnings shown before game starts
  - Doesn't block finalization (just warns)

  **Estimated Time:** 1 hour

---

#### Task 4.7: Add Mid-Game Property Definition (Optional)
- [ ] **Modify** `app/core/orchestrator.py`
  - [ ] Allow `schema.define_property` in GAMEPLAY mode
  - [ ] Require player confirmation via dialog
  - [ ] Add to context builder for future turns

  **Acceptance Criteria:**
  - AI can propose new properties mid-game
  - Player must approve before adding
  - Works seamlessly once approved

  **Estimated Time:** 3 hours

---

#### Task 4.8: Comprehensive Integration Test
- [ ] **Create** `tests/test_integration_session_zero.py`
  - [ ] Full flow test:
    1. Create new session
    2. AI defines 3 custom properties in Session Zero
    3. Player approves and finalizes
    4. Gameplay turn uses custom properties
    5. character.update validates against schema
    6. Export schema to file
    7. Create new session and import schema
    8. Verify imported schema works

  **Acceptance Criteria:**
  - All steps pass
  - Exported/imported schema identical
  - Validation works across sessions

  **Estimated Time:** 4 hours

---

## ✅ Definition of Done

A task is considered complete when:
- [ ] Code is written and follows project conventions
- [ ] Manual testing passes (or automated test created)
- [ ] No console errors or warnings
- [ ] Code is committed to git with clear message
- [ ] Related documentation updated (if applicable)

---

## 🐛 Bug Tracking

Use this section to track issues discovered during implementation:

### Known Issues
- [ ] _None yet_

### Future Enhancements
- [ ] Computed properties (formulas)
- [ ] Property dependencies (one affects another)
- [ ] Session Zero wizard UI (guided setup)
- [ ] Property templates marketplace (community sharing)

---

## 📝 Notes & Decisions

**Key Architectural Decisions:**
1. **Per-session schemas** - Each session has isolated custom properties
2. **Thread-local DB** - Each background thread creates its own connection
3. **Queue-based UI** - 100ms polling prevents race conditions
4. **High + Low level tools** - Keep both for flexibility
5. **Templates over free-form** - Guides AI to create consistent properties

**Dependencies:**
- Pydantic for schema validation
- Threading module (stdlib)
- Queue module (stdlib)
- No new external dependencies needed

**Performance Targets:**
- Session Zero should complete in 1-2 minutes
- Property validation adds <50ms overhead
- UI should remain responsive at <100ms latency

---

## 🎓 Learning Resources

If you get stuck:
- **Threading basics:** https://docs.python.org/3/library/threading.html
- **Queue patterns:** https://docs.python.org/3/library/queue.html
- **Pydantic validation:** https://docs.pydantic.dev/latest/concepts/validators/
- **SQLite thread safety:** https://docs.python.org/3/library/sqlite3.html#sqlite3-threadsafety

---

## 🚀 Quick Start Checklist

Before starting Phase 1:
- [ ] Create feature branch: `git checkout -b feature/session-zero`
- [ ] Back up current database: `cp ai_rpg.db ai_rpg.db.backup`
- [ ] Review current code structure
- [ ] Set up testing environment
- [ ] Read through all of Phase 1 tasks

---

**Last Updated:** _[Date]_  
**Current Focus:** _[Task you're working on]_  
**Blockers:** _[Any issues preventing progress]_
