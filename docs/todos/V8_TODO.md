# V*:TODO: New Game Initial Message, UI Improvements & SETUP Scaffolding

## Implementation Order

Based on dependencies and logical flow:

1. **Phase 1: Database & Model Foundation** ✅ Do First
2. **Phase 2: UI Cleanup (Remove Memory Field)** ✅ Do Second  
3. **Phase 3: New Prompt Dialog (3-Field Form)** ✅ Do Third
4. **Phase 4: Initial Message on New Game** ✅ Do Fourth
5. **Phase 5: SETUP Scaffolding Structure** ✅ Do Last

---

## Phase 1: Database & Model Foundation

**Goal:** Add `initial_message` column to prompts table and update model.

### 1.1 Database Migration

**File:** `app/database/db_manager.py`

**Location:** `_create_prompts_table()` method (around line 250)

```python
def _create_prompts_table(self):
    self.conn.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            initial_message TEXT DEFAULT ''  -- ✅ ADD THIS LINE
        )
    """)
```

**Migration for existing databases:**

Create a new file: `migration_add_initial_message.py`

```python
"""
Migration: Add initial_message column to prompts table
Run once to update existing databases.
"""
import sqlite3

DB_PATH = "ai_rpg.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(prompts)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'initial_message' not in columns:
        cursor.execute("ALTER TABLE prompts ADD COLUMN initial_message TEXT DEFAULT ''")
        conn.commit()
        print("✅ Added initial_message column to prompts table")
    else:
        print("⏭️  Column already exists, skipping migration")
    
    conn.close()

if __name__ == "__main__":
    migrate()
```

### 1.2 Update Prompt Model

**File:** `app/models/prompt.py`

```python
from dataclasses import dataclass

@dataclass
class Prompt:
    id: int
    name: str
    content: str
    initial_message: str = ""  # ✅ ADD THIS LINE
```

### 1.3 Update PromptRepository CRUD

**File:** `app/database/repositories/prompt_repository.py`

**Update `create()` method:**

```python
def create(self, name: str, content: str, initial_message: str = "") -> Prompt:
    '''Create a new prompt.'''
    cursor = self._execute(
        "INSERT INTO prompts (name, content, initial_message) VALUES (?, ?, ?)",
        (name, content, initial_message)  # ✅ ADD initial_message
    )
    self._commit()
    return Prompt(id=cursor.lastrowid, name=name, content=content, initial_message=initial_message)
```

**Update `get_all()` method:**

```python
def get_all(self) -> List[Prompt]:
    '''Get all prompts.'''
    rows = self._fetchall("SELECT id, name, content, initial_message FROM prompts")  # ✅ ADD initial_message
    return [Prompt(**dict(row)) for row in rows]
```

**Update `get_by_id()` method:**

```python
def get_by_id(self, prompt_id: int) -> Prompt | None:
    '''Get a prompt by ID.'''
    row = self._fetchone(
        "SELECT id, name, content, initial_message FROM prompts WHERE id = ?",  # ✅ ADD initial_message
        (prompt_id,)
    )
    return Prompt(**dict(row)) if row else None
```

**Update `update()` method:**

```python
def update(self, prompt: Prompt):
    '''Update a prompt.'''
    self._execute(
        "UPDATE prompts SET name = ?, content = ?, initial_message = ? WHERE id = ?",  # ✅ ADD initial_message
        (prompt.name, prompt.content, prompt.initial_message, prompt.id)
    )
    self._commit()
```

### 1.4 Update DBManager Facade

**File:** `app/database/db_manager.py`

**Update `create_prompt()` wrapper:**

```python
def create_prompt(self, name: str, content: str, initial_message: str = "") -> Prompt:
    with self.conn:
        return self.prompts.create(name, content, initial_message)  # ✅ ADD initial_message
```

---

## Phase 2: UI Cleanup (Remove Memory Field)

**Goal:** Remove the deprecated Memory field from Advanced Context panel.

### 2.1 Remove Memory Widgets from Builder

**File:** `app/gui/builders/control_panel_builder.py`

**Location:** `build()` method, around line 150 (Memory textbox section)

**Action:** **DELETE** these lines:

```python
# Memory textbox
ctk.CTkLabel(context_content, text="Memory:").pack(
    pady=(Theme.spacing.padding_sm, 0), 
    padx=Theme.spacing.padding_sm, 
    anchor="w"
)
memory_textbox = ctk.CTkTextbox(context_content, height=Theme.spacing.textbox_small)
memory_textbox.pack(**pack_config)
```

**Also remove from return dictionary (around line 230):**

```python
return {
    # ... other widgets ...
    'memory_textbox': memory_textbox,  # ✅ DELETE THIS LINE
    # ... other widgets ...
}
```

### 2.2 Remove Memory References from MainView

**File:** `app/gui/main_view.py`

**Delete from `_store_widget_refs()` method:**

```python
def _store_widget_refs(self, main_widgets: dict, control_widgets: dict):
    # ... other widgets ...
    self.memory_textbox = control_widgets['memory_textbox']  # ✅ DELETE THIS LINE
    # ... other widgets ...
```

**Delete from instance variable declarations:**

```python
def __init__(self, db_manager):
    # ... other code ...
    
    # Control panel widgets
    self.memory_textbox = None  # ✅ DELETE THIS LINE
    # ... other widgets ...
```

### 2.3 Remove Memory from SessionManager

**File:** `app/gui/managers/session_manager.py`

**Update `load_context()` method:**

```python
def load_context(self, authors_note_textbox: ctk.CTkTextbox):  # ✅ REMOVE memory_textbox parameter
    """
    Load author's note for the current session.
    
    MIGRATION NOTES:
    - Removed memory textbox (deprecated field)
    """
    if not self._selected_session:
        return
    
    # Load context from database
    context = self.db_manager.get_session_context(self._selected_session.id)
    
    if context:
        # ✅ DELETE memory textbox code
        
        # Populate author's note textbox
        authors_note_textbox.delete("1.0", "end")
        authors_note_textbox.insert("1.0", context.get("authors_note", ""))
```

**Update `save_context()` method:**

```python
def save_context(
    self, 
    authors_note_textbox: ctk.CTkTextbox,  # ✅ REMOVE memory_textbox parameter
    bubble_manager
):
    """
    Save the author's note.
    
    MIGRATION NOTES:
    - Removed memory field (deprecated)
    """
    if not self._selected_session:
        return
    
    # Get content from textbox
    authors_note = authors_note_textbox.get("1.0", "end-1c")
    
    # Save to database (memory field = empty string)
    self.db_manager.update_session_context(
        self._selected_session.id, 
        "",  # ✅ memory field always empty now
        authors_note
    )
    
    # Show confirmation
    bubble_manager.add_message("system", "Context saved")
```

### 2.4 Update Save Context Button Callback

**File:** `app/gui/main_view.py`

**Update `save_context()` method:**

```python
def save_context(self):
    """
    Save author's note.
    """
    if self.session_manager:
        self.session_manager.save_context(
            self.authors_note_textbox,  # ✅ REMOVE self.memory_textbox parameter
            self.bubble_manager
        )
```

---

## Phase 3: New Prompt Dialog (3-Field Form)

**Goal:** Replace simple input dialogs with a proper form for Name, Content, Initial Message.

### 3.1 Create Prompt Dialog Component

**New File:** `app/gui/panels/prompt_dialog.py`

```python
"""
Prompt creation/editing dialog with 3 fields.
"""
import customtkinter as ctk
from typing import Optional
from app.gui.styles import Theme


class PromptDialog(ctk.CTkToplevel):
    """
    Modal dialog for creating or editing prompts.
    
    Fields:
    - Name: Short identifier for the prompt
    - Content: System prompt that defines AI behavior/world
    - Initial Message: First GM message when starting a new game
    """
    
    def __init__(self, parent, title: str = "New Prompt", existing_prompt=None):
        """
        Args:
            parent: Parent window
            title: Dialog title
            existing_prompt: Prompt object to edit (None for new prompt)
        """
        super().__init__(parent)
        
        self.title(title)
        self.geometry("700x600")
        self.resizable(True, True)
        
        self.result = None  # Will store (name, content, initial_message) tuple
        self.existing_prompt = existing_prompt
        
        self._create_widgets()
        self._load_existing_data()
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        self.focus()
    
    def _create_widgets(self):
        """Build the form UI."""
        # Main container with padding
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # === Name Field ===
        ctk.CTkLabel(
            main_frame, 
            text="Prompt Name:",
            font=Theme.fonts.subheading,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.name_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="e.g., 'Cyberpunk Adventure', 'Horror Mystery'",
            height=35,
            font=Theme.fonts.body
        )
        self.name_entry.pack(fill="x", pady=(0, 15))
        
        # === Content Field ===
        ctk.CTkLabel(
            main_frame, 
            text="Prompt Content (System Prompt):",
            font=Theme.fonts.subheading,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(
            main_frame,
            text="Define the AI's role, world, tone, and style. This is the 'identity' of your game.",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.content_textbox = ctk.CTkTextbox(
            main_frame,
            height=200,
            font=Theme.fonts.body,
            wrap="word"
        )
        self.content_textbox.pack(fill="both", expand=True, pady=(0, 15))
        
        # === Initial Message Field ===
        ctk.CTkLabel(
            main_frame, 
            text="Initial Message (GM's Opening):",
            font=Theme.fonts.subheading,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(
            main_frame,
            text="The first message the Game Master will say when starting a new game. Should prompt the player for setup info.",
            font=Theme.fonts.body_small,
            text_color=Theme.colors.text_muted,
            anchor="w",
            wraplength=660,
            justify="left"
        ).pack(fill="x", pady=(0, 5))
        
        self.initial_message_textbox = ctk.CTkTextbox(
            main_frame,
            height=120,
            font=Theme.fonts.body,
            wrap="word"
        )
        self.initial_message_textbox.pack(fill="both", expand=True, pady=(0, 15))
        
        # === Buttons ===
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=120,
            height=35
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Save Prompt",
            command=self._on_save,
            width=120,
            height=35,
            fg_color=Theme.colors.button_default[0]
        ).pack(side="right", padx=5)
    
    def _load_existing_data(self):
        """Load data from existing prompt if editing."""
        if self.existing_prompt:
            self.name_entry.insert(0, self.existing_prompt.name)
            self.content_textbox.insert("1.0", self.existing_prompt.content)
            self.initial_message_textbox.insert("1.0", self.existing_prompt.initial_message or "")
    
    def _on_save(self):
        """Validate and save the prompt."""
        name = self.name_entry.get().strip()
        content = self.content_textbox.get("1.0", "end-1c").strip()
        initial_message = self.initial_message_textbox.get("1.0", "end-1c").strip()
        
        # Validate required fields
        if not name:
            self._show_error("Prompt name is required")
            return
        
        if not content:
            self._show_error("Prompt content is required")
            return
        
        # Note: initial_message is optional (can be empty)
        
        # Store result and close
        self.result = (name, content, initial_message)
        self.grab_release()
        self.destroy()
    
    def _on_cancel(self):
        """Close without saving."""
        self.result = None
        self.grab_release()
        self.destroy()
    
    def _show_error(self, message: str):
        """Show validation error (simple for now)."""
        error_dialog = ctk.CTkInputDialog(
            text=message,
            title="Validation Error"
        )
        error_dialog.get_input()  # Just to show the message
    
    def get_result(self):
        """
        Get the dialog result after it closes.
        
        Returns:
            Tuple of (name, content, initial_message) or None if cancelled
        """
        return self.result
```

### 3.2 Update PromptManager to Use New Dialog

**File:** `app/gui/managers/prompt_manager.py`

**Update `new_prompt()` method:**

```python
def new_prompt(self):
    """
    Create a new prompt via 3-field dialog.
    """
    from app.gui.panels.prompt_dialog import PromptDialog
    
    dialog = PromptDialog(self.prompt_scrollable_frame.winfo_toplevel(), title="New Prompt")
    self.prompt_scrollable_frame.wait_window(dialog)  # Wait for dialog to close
    
    result = dialog.get_result()
    if result:
        name, content, initial_message = result
        
        # Create in database
        self.db_manager.create_prompt(name, content, initial_message)
        
        # Refresh list
        self.refresh_list()
```

**Update `edit_prompt()` method:**

```python
def edit_prompt(self):
    """
    Edit the selected prompt via 3-field dialog.
    """
    if not self._selected_prompt:
        return
    
    from app.gui.panels.prompt_dialog import PromptDialog
    
    dialog = PromptDialog(
        self.prompt_scrollable_frame.winfo_toplevel(), 
        title="Edit Prompt",
        existing_prompt=self._selected_prompt
    )
    self.prompt_scrollable_frame.wait_window(dialog)  # Wait for dialog to close
    
    result = dialog.get_result()
    if result:
        name, content, initial_message = result
        
        # Update prompt object
        self._selected_prompt.name = name
        self._selected_prompt.content = content
        self._selected_prompt.initial_message = initial_message
        
        # Save to database
        self.db_manager.update_prompt(self._selected_prompt)
        
        # Refresh list
        self.refresh_list()
```

### 3.3 Create panels Package

**New File:** `app/gui/panels/__init__.py`

```python
"""
GUI Panel components (dialogs, complex widgets).
"""

from app.gui.panels.prompt_dialog import PromptDialog

__all__ = [
    'PromptDialog',
]
```

---

## Phase 4: Initial Message on New Game

**Goal:** When starting a new game, add the prompt's initial_message as the first GM message.

### 4.1 Update SessionManager.new_game()

**File:** `app/gui/managers/session_manager.py`

**Update `new_game()` method:**

```python
def new_game(self, selected_prompt):
    """
    Create a new game session with initial GM message.
    
    UPDATED:
    - Adds initial_message from prompt as first assistant message
    - Displays it in chat immediately
    """
    if not selected_prompt:
        return

    # Generate timestamped session name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    session_name = f"{timestamp}_{selected_prompt.name}"

    # Create session via orchestrator
    self.orchestrator.new_session(selected_prompt.content)
    
    # ✅ NEW: Add initial message if it exists
    if selected_prompt.initial_message and selected_prompt.initial_message.strip():
        self.orchestrator.session.add_message("assistant", selected_prompt.initial_message)
    
    self.orchestrator.save_game(session_name, selected_prompt.id)
    
    # Refresh session list to show new session
    self.refresh_session_list(selected_prompt.id)
```

### 4.2 Update SessionManager.load_game()

**File:** `app/gui/managers/session_manager.py`

**Current implementation already handles this correctly** - it replays all history including the initial message:

```python
def load_game(self, session_id: int, bubble_manager):
    """
    Load a saved game session.
    """
    # Load session via orchestrator
    self.orchestrator.load_game(session_id)
    
    # Clear existing chat
    bubble_manager.clear_history()
    
    # Replay history (✅ will include initial_message)
    history = self.orchestrator.session.get_history()
    for message in history:
        if message.role == "user":
            bubble_manager.add_message("user", message.content)
        elif message.role == "assistant":
            bubble_manager.add_message("assistant", message.content)
        elif message.role == "system":
            bubble_manager.add_message("system", message.content)
```

**No changes needed here!**

### 4.3 Example Initial Messages

Add helpful examples to the UI hint or documentation:

**For Fantasy Adventure:**
```
Greetings, traveler! Before we begin your adventure, I need to know a bit about your character and the world you'd like to explore.

Please tell me:
1. What kind of character are you? (race, class, background)
2. What tone should this adventure have? (heroic, dark, comedic, realistic)
3. Are there any specific mechanics you'd like? (custom stats, resources, conditions)
4. Anything else I should know about your preferences?

Once you share these details, I'll set up the game framework and we can begin!
```

**For Sci-Fi:**
```
Welcome to the stars, Commander. Before we launch, I need some intel.

Tell me about:
1. Your character (background, skills, implants/augmentations)
2. The setting (hard sci-fi, space opera, cyberpunk, post-apocalyptic)
3. Any custom systems you'd like (reputation, ship resources, cyberpsychosis)
4. Your preferred playstyle (combat-heavy, social, exploration, mystery)

Give me the details and I'll initialize the game framework!
```

---

## Phase 5: SETUP Scaffolding Structure

**Goal:** Provide initial JSON scaffolding when game_mode == "SETUP" to help the AI bootstrap the game structure.

### 5.1 Define Scaffolding Templates

**New File:** `app/core/scaffolding_templates.py`

```python
"""
Initial scaffolding templates for Session Zero (SETUP mode).

These provide a starting structure for the AI to populate and extend,
rather than creating everything from scratch.
"""
from typing import Dict, Any


def get_setup_scaffolding() -> Dict[str, Any]:
    """
    Returns the initial scaffolding structure for a new game in SETUP mode.
    
    This structure:
    - Provides placeholder entities for the AI to fill in
    - Demonstrates the expected schema format
    - Can be customized per genre/tone
    
    Returns:
        Dictionary of initial game state entities
    """
    return {
        "character": {
            "player": {
                "key": "player",
                "name": "[To be defined]",
                "race": "[To be defined]",
                "class": "[To be defined]",
                "level": 1,
                "attributes": {
                    "hp_current": 100,
                    "hp_max": 100
                },
                "conditions": [],
                "location": "starting_location",
                "inventory_key": "inventory:player",
                "properties": {
                    # Custom properties will be added here by schema.define_property
                    # Example: "Sanity": 100, "Mana": 50
                }
            }
        },
        "inventory": {
            "player": {
                "owner": "player",
                "items": [
                    # Example starting item (AI can modify/remove)
                    {
                        "id": "starter_item_01",
                        "name": "[Starting Equipment]",
                        "description": "Basic gear to get started",
                        "quantity": 1,
                        "equipped": False,
                        "properties": {}
                    }
                ],
                "currency": {
                    "gold": 0
                },
                "slots_used": 1,
                "slots_max": 10
            }
        },
        "location": {
            "starting_location": {
                "key": "starting_location",
                "name": "[Starting Location]",
                "description": "Where the adventure begins.",
                "properties": {
                    # Custom location properties
                    # Example: "DangerLevel": 1, "Weather": "Clear"
                }
            }
        }
    }


def get_genre_specific_scaffolding(genre: str) -> Dict[str, Any]:
    """
    Returns genre-specific scaffolding with suggested custom properties.
    
    This is OPTIONAL - the AI can ignore these suggestions if the player
    describes something different.
    
    Args:
        genre: Detected or specified genre (fantasy, scifi, horror, etc.)
    
    Returns:
        Scaffolding with genre-appropriate suggestions
    """
    base_scaffolding = get_setup_scaffolding()
    
    # Genre-specific property suggestions (these are just hints, not enforced)
    genre_suggestions = {
        "fantasy": {
            "character_properties": {
                "Mana": 50,
                "Faith": 100
            },
            "currency": {
                "gold": 10,
                "silver": 50
            }
        },
        "scifi": {
            "character_properties": {
                "Energy": 100,
                "Radiation": 0,
                "Cybernetics": 0
            },
            "currency": {
                "credits": 100
            }
        },
        "horror": {
            "character_properties": {
                "Sanity": 100,
                "Stress": 0,
                "Insight": 1
            },
            "currency": {
                "dollars": 50
            }
        },
        "cyberpunk": {
            "character_properties": {
                "Street_Cred": 0,
                "Heat": 0,
                "Augmentation_Slots": 3
            },
            "currency": {
                "eddies": 200
            }
        }
    }
    
    # Apply genre suggestions if available
    if genre.lower() in genre_suggestions:
        suggestions = genre_suggestions[genre.lower()]
        
        # Merge character properties
        if "character_properties" in suggestions:
            base_scaffolding["character"]["player"]["properties"].update(
                suggestions["character_properties"]
            )
        
        # Update currency
        if "currency" in suggestions:
            base_scaffolding["inventory"]["player"]["currency"] = suggestions["currency"]
    
    return base_scaffolding


# Optional: Detect genre from prompt content
def detect_genre_from_prompt(prompt_content: str) -> str:
    """
    Simple heuristic to detect genre from prompt content.
    Returns 'generic' if no clear match.
    """
    prompt_lower = prompt_content.lower()
    
    if any(word in prompt_lower for word in ["cyberpunk", "cyber", "netrunner", "chrome"]):
        return "cyberpunk"
    elif any(word in prompt_lower for word in ["horror", "lovecraft", "cosmic", "sanity", "terror"]):
        return "horror"
    elif any(word in prompt_lower for word in ["sci-fi", "scifi", "space", "starship", "alien"]):
        return "scifi"
    elif any(word in prompt_lower for word in ["fantasy", "magic", "dragon", "sword", "wizard"]):
        return "fantasy"
    else:
        return "generic"
```

### 5.2 Inject Scaffolding on New Game

**File:** `app/gui/managers/session_manager.py`

**Update `new_game()` method:**

```python
def new_game(self, selected_prompt):
    """
    Create a new game session with initial GM message and scaffolding.
    
    UPDATED:
    - Adds initial_message from prompt as first assistant message
    - Injects SETUP scaffolding into game state
    - Displays initial message in chat immediately
    """
    if not selected_prompt:
        return

    # Generate timestamped session name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    session_name = f"{timestamp}_{selected_prompt.name}"

    # Create session via orchestrator
    self.orchestrator.new_session(selected_prompt.content)
    
    # Add initial message if it exists
    if selected_prompt.initial_message and selected_prompt.initial_message.strip():
        self.orchestrator.session.add_message("assistant", selected_prompt.initial_message)
    
    # Save to get session ID
    self.orchestrator.save_game(session_name, selected_prompt.id)
    
    # ✅ NEW: Inject SETUP scaffolding
    if self.orchestrator.session.id:
        self._inject_setup_scaffolding(self.orchestrator.session.id, selected_prompt.content)
    
    # Refresh session list to show new session
    self.refresh_session_list(selected_prompt.id)

def _inject_setup_scaffolding(self, session_id: int, prompt_content: str):
    """
    Inject initial scaffolding structure for SETUP mode.
    
    Args:
        session_id: Current session ID
        prompt_content: The prompt content (used for genre detection)
    """
    from app.core.scaffolding_templates import get_setup_scaffolding, detect_genre_from_prompt, get_genre_specific_scaffolding
    
    # Detect genre and get appropriate scaffolding
    genre = detect_genre_from_prompt(prompt_content)
    
    if genre != "generic":
        scaffolding = get_genre_specific_scaffolding(genre)
    else:
        scaffolding = get_setup_scaffolding()
    
    # Inject scaffolding into database
    for entity_type, entities in scaffolding.items():
        for entity_key, entity_data in entities.items():
            self.db_manager.set_game_state_entity(
                session_id, 
                entity_type, 
                entity_key, 
                entity_data
            )
    
    logger.info(f"Injected {genre} scaffolding for session {session_id}")
```

**Add import at top of file:**

```python
import logging

logger = logging.getLogger(__name__)
```

### 5.3 Update SESSION_ZERO_TEMPLATE Prompt

**File:** `app/core/llm/prompts.py`

**Update `SESSION_ZERO_TEMPLATE`:**

```python
SESSION_ZERO_TEMPLATE = """
Okay. The game is in SETUP mode, the system and world-building phase, similar to the pre-game session or Session Zero in tabletop RPGs where rules, tone, and custom mechanics are collaboratively defined before gameplay begins.

IMPORTANT: Initial scaffolding has already been created for you. You can see the current structure by using state.query tools. You don't need to create entities from scratch - update what exists or add to it.

Here's how I'll approach this turn:

1. **Understand the player's message.**
   - I'll read what the player wrote in the last turn to understand what genre, tone, setting, properties, mechanical ideas, etc, they described or confirmed.

2. **Evaluate what's missing.**
   - I'll use state.query to check the current scaffolding (character, inventory, location templates).
   - I'll compare their message with the current setup and identify which aspects of the world, rules, properties, etc, are still undefined or incomplete.

3. **Use tools to update the setup.**
   - If the player confirmed a mechanic or idea, I'll record it with `schema.define_property`.
   - If they want to modify character details, I'll use `state.apply_patch` to update the scaffolding.
   - If they indicated that setup is complete and they're ready to play, I'll call `schema.finalize({"confirm": true})` to finalize SETUP mode and move to GAMEPLAY mode so that the game can finally begin.
   - Otherwise, I'll add or adjust properties as needed to keep building the framework.

4. **Plan my next interaction.**
   - Once I've made any necessary tool calls, I'll outline what I'll want to talk about next time – for example, asking follow-up questions, suggesting new systems, or inviting feedback.

There are a variety of examples I can take inspiration from for my suggestions:
 - **Fantasy Adventure:** *Dungeons & Dragons*, *Pathfinder*, *The Elder Scrolls*, *Zork*, *King's Quest* → Stats like Strength, Intelligence, Mana, Hit Points, Alignment, Encumbrance.
 - **Horror & Investigation:** *Call of Cthulhu*, *World of Darkness*, *Sunless Sea*, *Anchorhead* → Sanity, Stress, Willpower, Clue Points, Fear, Insight.
 - **Sci-Fi & Space Opera:** *Traveller*, *Starfinder*, *Mass Effect*, *Fallen London*, *Eventide* → Oxygen, Energy, Engineering, Reputation, Ship Integrity, Morale.
 - **Cyberpunk & Dystopia:** *Shadowrun*, *Cyberpunk 2020/RED*, *Deus Ex*, *AI Dungeon* → Augmentation Level, Cred, Street Rep, Heat, Cyberpsychosis.
 - **Mystery / Noir:** *GUMSHOE*, *Blades in the Dark*, *The Case of the Golden Idol*, *80 Days* → Clues, Reputation, Vice, Stress, Insight.
 - **Lighthearted / Slice of Life:** *Honey Heist*, *Pokémon Tabletop*, *Animal Crossing*, *80 Days*, *A Dark Room* → Friendship, Charm, Luck, Creativity, Chaos Meter.
Etc.

During this planning phase, I'm not speaking to the player yet. I'm quietly reasoning, using tools, and preparing for the next narrative response where I'll summarize progress and ask for input.
"""
```

### 5.4 Update SETUP_RESPONSE_TEMPLATE

**File:** `app/core/llm/prompts.py`

**Update `SETUP_RESPONSE_TEMPLATE`:**

```python
SETUP_RESPONSE_TEMPLATE = """
Since we are still in the SETUP game mode (Session Zero phase), I'll acknowledge any new or updated properties and explain what each represents, how it might work in play, and how it fits the genre or tone we've been developing.

I have access to the existing scaffolding via state.query tools. I can see what's already defined and build upon it.

If appropriate, I'll suggest optional refinements – like adding modifiers, linking properties to dice mechanics, or expanding narrative consequences – but I'll keep the focus collaborative.

There are a variety of examples I can take inspiration from for my suggestions:
 - **Fantasy Adventure:** *Dungeons & Dragons*, *Pathfinder*, *The Elder Scrolls*, *Zork*, *King's Quest* → Stats like Strength, Intelligence, Mana, Hit Points, Alignment, Encumbrance.
 - **Horror & Investigation:** *Call of Cthulhu*, *World of Darkness*, *Sunless Sea*, *Anchorhead* → Sanity, Stress, Willpower, Clue Points, Fear, Insight.
 - **Sci-Fi & Space Opera:** *Traveller*, *Starfinder*, *Mass Effect*, *Fallen London*, *Eventide* → Oxygen, Energy, Engineering, Reputation, Ship Integrity, Morale.
 - **Cyberpunk & Dystopia:** *Shadowrun*, *Cyberpunk 2020/RED*, *Deus Ex*, *AI Dungeon* → Augmentation Level, Cred, Street Rep, Heat, Cyberpsychosis.
 - **Mystery / Noir:** *GUMSHOE*, *Blades in the Dark*, *The Case of the Golden Idol*, *80 Days* → Clues, Reputation, Vice, Stress, Insight.
 - **Lighthearted / Slice of Life:** *Honey Heist*, *Pokémon Tabletop*, *Animal Crossing*, *80 Days*, *A Dark Room* → Friendship, Charm, Luck, Creativity, Chaos Meter.
Etc.

I'll summarize what's been defined so far in a clear, friendly tone that matches the chosen style (fantasy, sci-fi, horror, comedy, etc.), then ask what the player would like to do next: refine, add, or finalize the setup.

The idea is to get as much information as possible about the desired world, rules, tone, mechanics, etc, of the game's system or framework, efficiently. I should encourage the player to provide detailed information in their responses.
"""
```
