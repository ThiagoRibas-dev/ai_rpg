# TODO: Chat History Management (Reroll & Delete)

## Overview

Add two new chat control features:
1. **Reroll Last Response**: Delete the last assistant message and regenerate it
2. **Delete Last N Messages**: Remove recent messages and continue from an earlier point

---

## Architecture Design

### UI Layout

Add a toolbar above the input box with history control buttons:

```
┌─────────────────────────────────────┐
│  [🔄 Reroll] [🗑️ Delete Last] [✂️ Trim...] │  ← New toolbar
├─────────────────────────────────────┤
│  User Input Box                     │
│                                     │
└─────────────────────────────────────┘
│  [Send]  [Stop]                     │
```

### State Management

**Affected Components:**
- `Session.history` - Remove messages
- `GameSession.session_data` - Persist changes
- `ChatBubbleManager.bubble_labels` - Remove UI widgets
- Database - Update session

---

## Implementation Steps

### Step 1: Create History Manager

**New File:** `app/gui/managers/history_manager.py`

```python
"""
Manages chat history manipulation (reroll, delete, trim).
"""
import logging
from typing import Optional
from app.models.game_session import GameSession

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Handles chat history editing operations.
    
    Responsibilities:
    - Delete last N messages from Session.history
    - Update GameSession in database
    - Clear corresponding UI bubbles
    - Trigger regeneration for reroll
    """
    
    def __init__(self, orchestrator, db_manager, bubble_manager):
        """
        Args:
            orchestrator: Orchestrator instance (has Session)
            db_manager: Database manager
            bubble_manager: ChatBubbleManager for UI updates
        """
        self.orchestrator = orchestrator
        self.db_manager = db_manager
        self.bubble_manager = bubble_manager
    
    def can_reroll(self) -&gt; bool:
        """
        Check if reroll is possible (last message is from assistant).
        
        Returns:
            True if last message is from assistant
        """
        if not self.orchestrator.session:
            return False
        
        history = self.orchestrator.session.get_history()
        if not history:
            return False
        
        return history[-1].role == "assistant"
    
    def can_delete(self, n: int = 1) -&gt; bool:
        """
        Check if deletion is possible.
        
        Args:
            n: Number of messages to delete
        
        Returns:
            True if there are at least n messages
        """
        if not self.orchestrator.session:
            return False
        
        history = self.orchestrator.session.get_history()
        return len(history) &gt;= n
    
    def reroll_last_response(self, game_session: GameSession) -&gt; Optional[str]:
        """
        Delete the last assistant message and return the user message to resend.
        
        Args:
            game_session: Current game session
        
        Returns:
            The user message to resend, or None if reroll not possible
        """
        if not self.can_reroll():
            logger.warning("Cannot reroll: last message is not from assistant")
            return None
        
        session = self.orchestrator.session
        history = session.get_history()
        
        # Find the last user message (should be second-to-last)
        user_message = None
        if len(history) &gt;= 2 and history[-2].role == "user":
            user_message = history[-2].content
        
        # Delete last assistant message from Session
        logger.info(f"🔄 Rerolling: Removing last assistant message")
        session.history.pop()  # Remove last message
        
        # Delete last bubble from UI
        self.bubble_manager.bubble_labels.pop()  # Remove widget reference
        
        # Find and destroy the last bubble widget
        chat_widgets = self.bubble_manager.chat_frame.winfo_children()
        if chat_widgets:
            chat_widgets[-1].destroy()
        
        # Update database
        game_session.session_data = session.to_json()
        self.db_manager.update_session(game_session)
        
        logger.info(f"✅ Reroll prepared, returning user message for regeneration")
        return user_message
    
    def delete_last_n_messages(self, game_session: GameSession, n: int) -&gt; bool:
        """
        Delete the last N messages from history and UI.
        
        Args:
            game_session: Current game session
            n: Number of messages to delete
        
        Returns:
            True if deletion succeeded
        """
        if not self.can_delete(n):
            logger.warning(f"Cannot delete {n} messages: not enough messages in history")
            return False
        
        session = self.orchestrator.session
        
        logger.info(f"🗑️ Deleting last {n} messages")
        
        # Delete from Session history
        for _ in range(n):
            if session.history:
                session.history.pop()
        
        # Delete from UI
        for _ in range(n):
            if self.bubble_manager.bubble_labels:
                self.bubble_manager.bubble_labels.pop()
            
            chat_widgets = self.bubble_manager.chat_frame.winfo_children()
            if chat_widgets:
                chat_widgets[-1].destroy()
        
        # Update database
        game_session.session_data = session.to_json()
        self.db_manager.update_session(game_session)
        
        logger.info(f"✅ Deleted {n} messages")
        
        # Show confirmation in chat
        self.bubble_manager.add_message("system", f"🗑️ Deleted last {n} message(s)")
        
        return True
    
    def get_history_length(self) -&gt; int:
        """Get current history length."""
        if not self.orchestrator.session:
            return 0
        return len(self.orchestrator.session.get_history())
```

---

### Step 2: Update MainPanelBuilder

**File:** `app/gui/builders/main_panel_builder.py`

**Add history control toolbar above input:**

```python
@staticmethod
def build(parent: ctk.CTk, send_callback: Callable) -&gt; Dict[str, Any]:
    """
    Build the main panel and return widget references.
    """
    # ... existing code for main_panel, game_time_frame, chat_history_frame, etc. ...
    
    # === Choice Button Frame ===
    # (existing code)
    
    # === Loading Indicator ===
    # (existing code)
    
    # ✅ NEW: History Control Toolbar
    history_toolbar = ctk.CTkFrame(main_panel)
    history_toolbar.grid(row=3, column=0, columnspan=2, sticky="ew", 
                         padx=Theme.spacing.padding_sm, 
                         pady=(Theme.spacing.padding_sm, 0))
    history_toolbar.grid_remove()  # Hidden by default, shown when session loaded
    
    reroll_button = ctk.CTkButton(
        history_toolbar,
        text="🔄 Reroll",
        width=80,
        height=28,
        command=None  # Will be wired later
    )
    reroll_button.pack(side="left", padx=2)
    
    delete_last_button = ctk.CTkButton(
        history_toolbar,
        text="🗑️ Delete Last",
        width=100,
        height=28,
        command=None  # Will be wired later
    )
    delete_last_button.pack(side="left", padx=2)
    
    trim_button = ctk.CTkButton(
        history_toolbar,
        text="✂️ Trim...",
        width=80,
        height=28,
        command=None  # Will be wired later
    )
    trim_button.pack(side="left", padx=2)
    
    # History info label (shows message count)
    history_info_label = ctk.CTkLabel(
        history_toolbar,
        text="0 messages",
        font=Theme.fonts.body_small,
        text_color=Theme.colors.text_muted
    )
    history_info_label.pack(side="right", padx=10)
    
    # === User Input ===
    # UPDATED: Changed grid row from 3 to 4
    user_input = ctk.CTkTextbox(main_panel, height=Theme.spacing.input_height)
    user_input.grid(row=4, column=0, sticky="ew", 
                   padx=Theme.spacing.padding_sm, 
                   pady=Theme.spacing.padding_sm)
    
    # === Button Frame ===
    # UPDATED: Changed grid row from 3 to 4
    button_frame = ctk.CTkFrame(main_panel)
    button_frame.grid(row=4, column=1, sticky="ns", 
                     padx=Theme.spacing.padding_sm, 
                     pady=Theme.spacing.padding_sm)
    
    # ... existing send_button and stop_button code ...
    
    # === Return Widget References ===
    return {
        'main_panel': main_panel,
        'game_time_frame': game_time_frame,
        'game_time_label': game_time_label,
        'game_mode_label': game_mode_label,
        'session_name_label': session_name_label,
        'chat_history_frame': chat_history_frame,
        'choice_button_frame': choice_button_frame,
        'loading_frame': loading_frame,
        'loading_label': loading_label,
        'history_toolbar': history_toolbar,  # ✅ NEW
        'reroll_button': reroll_button,  # ✅ NEW
        'delete_last_button': delete_last_button,  # ✅ NEW
        'trim_button': trim_button,  # ✅ NEW
        'history_info_label': history_info_label,  # ✅ NEW
        'user_input': user_input,
        'send_button': send_button,
        'stop_button': stop_button,
    }
```

---

### Step 3: Update MainView

**File:** `app/gui/main_view.py`

**Add widget references in `__init__()`:**

```python
def __init__(self, db_manager):
    super().__init__()
    
    # ... existing code ...
    
    # Manager references (initialized in _init_managers)
    self.history_manager = None  # ✅ NEW
    
    # Widget references (filled by builders in _build_panels)
    # Main panel widgets
    self.main_panel = None
    self.history_toolbar = None  # ✅ NEW
    self.reroll_button = None  # ✅ NEW
    self.delete_last_button = None  # ✅ NEW
    self.trim_button = None  # ✅ NEW
    self.history_info_label = None  # ✅ NEW
    # ... rest of widgets ...
```

**Update `_store_widget_refs()`:**

```python
def _store_widget_refs(self, main_widgets: dict, control_widgets: dict):
    """
    Store widget references from builders.
    """
    # Main panel widgets
    self.main_panel = main_widgets['main_panel']
    self.game_time_label = main_widgets['game_time_label']
    self.game_mode_label = main_widgets['game_mode_label']
    self.session_name_label = main_widgets['session_name_label']
    self.chat_history_frame = main_widgets['chat_history_frame']
    self.choice_button_frame = main_widgets['choice_button_frame']
    self.loading_frame = main_widgets['loading_frame']
    self.loading_label = main_widgets['loading_label']
    self.history_toolbar = main_widgets['history_toolbar']  # ✅ NEW
    self.reroll_button = main_widgets['reroll_button']  # ✅ NEW
    self.delete_last_button = main_widgets['delete_last_button']  # ✅ NEW
    self.trim_button = main_widgets['trim_button']  # ✅ NEW
    self.history_info_label = main_widgets['history_info_label']  # ✅ NEW
    self.user_input = main_widgets['user_input']
    self.send_button = main_widgets['send_button']
    self.stop_button = main_widgets['stop_button']
    
    # ... rest of control panel widgets ...
```

**Initialize HistoryManager in `_init_managers()`:**

```python
def _init_managers(self):
    """
    Initialize all manager instances.
    """
    # Chat bubble manager
    self.bubble_manager = ChatBubbleManager(self.chat_history_frame, self)
    
    # ✅ NEW: History manager (needs bubble_manager)
    # Note: Will set orchestrator in set_orchestrator()
    # (Can't initialize fully here because orchestrator doesn't exist yet)
    
    # ... rest of managers ...
```

**Wire HistoryManager in `set_orchestrator()`:**

```python
def set_orchestrator(self, orchestrator):
    """
    Wire orchestrator to all managers.
    """
    self.orchestrator = orchestrator
    
    # ✅ NEW: Initialize history manager (needs orchestrator)
    from app.gui.managers.history_manager import HistoryManager
    self.history_manager = HistoryManager(
        orchestrator,
        self.db_manager,
        self.bubble_manager
    )
    
    # ... existing session_manager initialization ...
    
    # ... existing UI queue handler initialization ...
    
    # ... existing inspector wiring ...
    
    # ✅ NEW: Wire history control buttons
    self.reroll_button.configure(command=self.handle_reroll)
    self.delete_last_button.configure(command=self.handle_delete_last)
    self.trim_button.configure(command=self.handle_trim_history)
    
    # Start UI queue polling
    self.ui_queue_handler.start_polling()
    
    # Wire state viewer button
    self._wire_state_viewer_button()
```

**Add handler methods:**

```python
def handle_reroll(self):
    """
    Reroll the last assistant response.
    """
    if not self.session_manager or not self.session_manager.selected_session:
        self.bubble_manager.add_message("system", "⚠️ Please load a game session first")
        return
    
    if not self.history_manager.can_reroll():
        self.bubble_manager.add_message("system", "⚠️ Cannot reroll: last message is not from assistant")
        return
    
    # Get the user message to resend
    user_message = self.history_manager.reroll_last_response(
        self.session_manager.selected_session
    )
    
    if user_message:
        # Add user message back to UI (it was already in history before the assistant response)
        # We don't need to add it again, just trigger regeneration
        
        # Disable send button during regeneration
        self.send_button.configure(state="disabled")
        
        # Clear any existing choices
        for widget in self.choice_button_frame.winfo_children():
            widget.destroy()
        self.choice_button_frame.grid_remove()
        
        # Trigger regeneration
        self.orchestrator.plan_and_execute(self.session_manager.selected_session)
    
    # Update history info
    self._update_history_info()

def handle_delete_last(self):
    """
    Delete the last message pair (user + assistant).
    """
    if not self.session_manager or not self.session_manager.selected_session:
        self.bubble_manager.add_message("system", "⚠️ Please load a game session first")
        return
    
    # Delete last 2 messages (user + assistant pair)
    success = self.history_manager.delete_last_n_messages(
        self.session_manager.selected_session,
        n=2
    )
    
    if success:
        self._update_history_info()

def handle_trim_history(self):
    """
    Open dialog to delete last N messages.
    """
    if not self.session_manager or not self.session_manager.selected_session:
        self.bubble_manager.add_message("system", "⚠️ Please load a game session first")
        return
    
    current_length = self.history_manager.get_history_length()
    
    if current_length == 0:
        self.bubble_manager.add_message("system", "⚠️ No messages to delete")
        return
    
    # Simple input dialog for now
    dialog = ctk.CTkInputDialog(
        text=f"How many messages to delete? (1-{current_length})",
        title="Trim History"
    )
    result = dialog.get_input()
    
    if result:
        try:
            n = int(result)
            if n &lt; 1 or n &gt; current_length:
                self.bubble_manager.add_message("system", f"⚠️ Please enter a number between 1 and {current_length}")
                return
            
            success = self.history_manager.delete_last_n_messages(
                self.session_manager.selected_session,
                n=n
            )
            
            if success:
                self._update_history_info()
        
        except ValueError:
            self.bubble_manager.add_message("system", "⚠️ Please enter a valid number")

def _update_history_info(self):
    """
    Update the history info label with current message count.
    """
    if self.history_manager:
        count = self.history_manager.get_history_length()
        self.history_info_label.configure(text=f"{count} messages")
```

---

### Step 4: Show/Hide Toolbar on Session Load

**File:** `app/gui/managers/session_manager.py`

**Update `on_session_select()` to show toolbar:**

```python
def on_session_select(self, session: GameSession, bubble_manager, inspectors: dict):
    """
    Handle session selection.
    """
    self._selected_session = session
    self.load_game(session.id, bubble_manager)
    self.send_button.configure(state="normal")
    
    # Update header with session info
    self.session_name_label.configure(text=session.name)
    self.game_time_label.configure(text=f"🕐 {session.game_time}")
    
    # Update game mode indicator
    mode_text, mode_color = get_mode_display(session.game_mode)
    self.game_mode_label.configure(text=mode_text, text_color=mode_color)
    
    # Load context (Author's Note)
    self.load_context(self.authors_note_textbox)
    
    # ✅ NEW: Show history toolbar (needs to be passed as parameter or accessed via orchestrator.view)
    # This will be handled in MainView after this method returns
    
    # ... rest of method ...
```

**Better approach - Add callback parameter:**

**File:** `app/gui/managers/session_manager.py`

```python
def __init__(
    self,
    orchestrator,
    db_manager,
    session_scrollable_frame: ctk.CTkScrollableFrame,
    session_name_label: ctk.CTkLabel,
    game_time_label: ctk.CTkLabel,
    game_mode_label: ctk.CTkLabel,
    send_button: ctk.CTkButton,
    session_collapsible,
    authors_note_textbox: ctk.CTkTextbox,
    on_session_loaded_callback: Callable = None  # ✅ NEW
):
    # ... existing code ...
    self.on_session_loaded_callback = on_session_loaded_callback  # ✅ NEW
```

**Call callback in `on_session_select()`:**

```python
def on_session_select(self, session: GameSession, bubble_manager, inspectors: dict):
    """
    Handle session selection.
    """
    # ... existing code ...
    
    # ✅ NEW: Notify MainView that session was loaded
    if self.on_session_loaded_callback:
        self.on_session_loaded_callback()
```

**Wire callback in MainView:**

```python
def set_orchestrator(self, orchestrator):
    """
    Wire orchestrator to all managers.
    """
    self.orchestrator = orchestrator
    
    # ... existing history_manager initialization ...
    
    # Initialize session manager (needs orchestrator)
    self.session_manager = SessionManager(
        orchestrator,
        self.db_manager,
        self.session_scrollable_frame,
        self.session_name_label,
        self.game_time_label,
        self.game_mode_label,
        self.send_button,
        self.session_collapsible,
        self.authors_note_textbox,
        on_session_loaded_callback=self._on_session_loaded  # ✅ NEW
    )
    
    # ... rest of method ...

def _on_session_loaded(self):
    """
    Called when a session is successfully loaded.
    Shows history toolbar and updates info.
    """
    # Show history toolbar
    self.history_toolbar.grid()
    
    # Update history info
    self._update_history_info()
```

---

### Step 5: Update managers __init__.py

**File:** `app/gui/managers/__init__.py`

```python
from app.gui.managers.chat_bubble_manager import ChatBubbleManager
from app.gui.managers.tool_visualization_manager import ToolVisualizationManager
from app.gui.managers.ui_queue_handler import UIQueueHandler
from app.gui.managers.session_manager import SessionManager
from app.gui.managers.prompt_manager import PromptManager
from app.gui.managers.inspector_manager import InspectorManager
from app.gui.managers.history_manager import HistoryManager  # ✅ NEW

__all__ = [
    'ChatBubbleManager',
    'ToolVisualizationManager',
    'UIQueueHandler',
    'SessionManager',
    'PromptManager',
    'InspectorManager',
    'HistoryManager',  # ✅ NEW
]
```
