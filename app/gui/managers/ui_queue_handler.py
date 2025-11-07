"""
Handles UI queue processing and message routing.

MIGRATION SOURCE: main_view.py lines 181-280
Extracted methods:
- _process_ui_queue() → _process_queue() (lines 181-195)
- _handle_ui_message() → _handle_message() (lines 196-280)
- after(100, self._process_ui_queue) startup (line 112)

New responsibilities:
- Poll UI queue on main thread
- Route messages to appropriate handlers
- Coordinate loading states, choices, inspector refreshes
- Update game time/mode labels
"""

import queue
import logging
from typing import Dict, Any
import customtkinter as ctk
from app.gui.utils.ui_helpers import create_choice_buttons, get_mode_display

logger = logging.getLogger(__name__)


class UIQueueHandler:
    """
    Processes messages from the orchestrator's UI queue.
    
    MIGRATION NOTES:
    - Extracted from: MainView (UI queue methods lines 181-280)
    - Polling loop moved from MainView.__init__ (line 112)
    - Message routing logic centralized here
    """
    
    def __init__(
        self,
        orchestrator,
        bubble_manager,
        tool_viz_manager,
        loading_frame: ctk.CTkFrame,
        loading_label: ctk.CTkLabel,
        choice_button_frame: ctk.CTkFrame,
        send_button: ctk.CTkButton,
        game_time_label: ctk.CTkLabel,
        game_mode_label: ctk.CTkLabel,
        inspectors: Dict[str, Any]
    ):
        """
        Initialize the UI queue handler.
        
        MIGRATION NOTES:
        - All parameters previously accessed via self.* in MainView
        - orchestrator: Previously self.orchestrator
        - bubble_manager: New (extracted from MainView)
        - tool_viz_manager: New (extracted from MainView)
        - inspectors: Previously accessed via self.character_inspector, etc.
        
        Args:
            orchestrator: Orchestrator instance
            bubble_manager: ChatBubbleManager instance
            tool_viz_manager: ToolVisualizationManager instance
            loading_frame: Loading indicator frame
            loading_label: Loading indicator label
            choice_button_frame: Frame for action choice buttons
            send_button: Send button to enable/disable
            game_time_label: Label for game time updates
            game_mode_label: Label for game mode updates
            inspectors: Dictionary of inspector instances
        """
        self.orchestrator = orchestrator
        self.bubble_manager = bubble_manager
        self.tool_viz_manager = tool_viz_manager
        self.loading_frame = loading_frame
        self.loading_label = loading_label
        self.choice_button_frame = choice_button_frame
        self.send_button = send_button
        self.game_time_label = game_time_label
        self.game_mode_label = game_mode_label
        self.inspectors = inspectors
        
        # Callback for choice selection (set externally by MainView)
        # MIGRATION NOTE: Previously self.select_choice
        self.on_choice_selected = None
    
    def start_polling(self):
        """
        Start polling the UI queue.
        
        MIGRATION NOTES:
        - Extracted from: MainView.__init__() line 112
        - Original: self.after(100, self._process_ui_queue)
        - Changed: Uses orchestrator.view instead of self
        """
        self._process_queue()
    
    def _process_queue(self):
        """
        Process messages from the orchestrator's UI queue.
        
        MIGRATION NOTES:
        - Extracted from: MainView._process_ui_queue() lines 181-195
        - Changed: self.orchestrator.ui_queue → self.orchestrator.ui_queue (no change)
        - Changed: self.after → self.orchestrator.view.after
        """
        try:
            processed = 0
            while True:  # Process all pending messages
                msg = self.orchestrator.ui_queue.get_nowait()
                self._handle_message(msg)
                processed += 1
        except queue.Empty:
            pass
        finally:
            if processed > 0:
                logger.debug(f"📬 Processed {processed} UI messages")
            # Re-schedule polling
            # CHANGED: Use orchestrator's view for after() call
            self.orchestrator.view.after(100, self._process_queue)
    
    def _handle_message(self, msg: Dict[str, Any]):
        """
        Handle a single UI message from the orchestrator.
        
        MIGRATION NOTES:
        - Extracted from: MainView._handle_ui_message() lines 196-280
        - Changed: Direct method calls → delegate to managers
        - Changed: self.add_message_bubble → self.bubble_manager.add_message
        - Changed: self.add_tool_call → self.tool_viz_manager.add_tool_call
        - Changed: display_action_choices logic → create_choice_buttons
        
        Message routing table:
        - thought_bubble → bubble_manager.add_message
        - message_bubble → bubble_manager.add_message
        - tool_call → tool_viz_manager.add_tool_call
        - tool_result → tool_viz_manager.add_tool_result
        - choices → create_choice_buttons (ui_helpers)
        - error → bubble_manager.add_message (as system)
        - turn_complete → inspectors refresh + enable send button
        - refresh_memory_inspector → memory_inspector.refresh_memories
        - update_game_time → game_time_label update
        - update_game_mode → game_mode_label update
        
        Args:
            msg: Message dictionary with 'type' and type-specific fields
        """
        msg_type = msg.get("type")
        logger.debug(f"📨 UI message received: {msg_type}")
        
        # === Thought Bubble ===
        # MIGRATED FROM: lines 201-204
        if msg_type == "thought_bubble":
            # Show loading frame
            self.loading_frame.grid(row=2, column=0, columnspan=2, sticky="ew", 
                                   padx=5, pady=5)
            # CHANGED: self.add_message_bubble → self.bubble_manager.add_message
            self.bubble_manager.add_message("thought", msg["content"])
        
        # === Message Bubble ===
        # MIGRATED FROM: lines 206-207
        elif msg_type == "message_bubble":
            # CHANGED: self.add_message_bubble → self.bubble_manager.add_message
            self.bubble_manager.add_message(msg["role"], msg["content"])
        
        # === Tool Call ===
        # MIGRATED FROM: lines 209-211
        elif msg_type == "tool_call":
            logger.debug(f"🔧 Adding tool call to panel: {msg.get('name')}")
            # CHANGED: self.add_tool_call → self.tool_viz_manager.add_tool_call
            self.tool_viz_manager.add_tool_call(msg["name"], msg["args"])
        
        # === Tool Result ===
        # MIGRATED FROM: lines 213-214
        elif msg_type == "tool_result":
            # CHANGED: self.add_tool_result → self.tool_viz_manager.add_tool_result
            self.tool_viz_manager.add_tool_result(msg["result"], msg.get("is_error", False))
        
        # === Choices ===
        # MIGRATED FROM: lines 216-219
        elif msg_type == "choices":
            if self.on_choice_selected:
                # CHANGED: self.display_action_choices → create_choice_buttons (ui_helpers)
                create_choice_buttons(
                    self.choice_button_frame, 
                    msg["choices"], 
                    self.on_choice_selected
                )
        
        # === Error ===
        # MIGRATED FROM: lines 221-222
        elif msg_type == "error":
            # CHANGED: self.add_message_bubble → self.bubble_manager.add_message
            self.bubble_manager.add_message("system", f"❌ Error: {msg['message']}")
        
        # === Turn Complete ===
        # MIGRATED FROM: lines 224-234
        elif msg_type == "turn_complete":
            self.loading_frame.grid_remove()  # Hide loading
            self.send_button.configure(state="normal")  # Re-enable
            
            # Refresh inspectors if needed
            # CHANGED: Direct inspector access → via inspectors dict
            if 'character' in self.inspectors and self.inspectors['character']:
                self.inspectors['character'].refresh()
            if 'inventory' in self.inspectors and self.inspectors['inventory']:
                self.inspectors['inventory'].refresh()
            if 'quest' in self.inspectors and self.inspectors['quest']:
                self.inspectors['quest'].refresh()
        
        # === Refresh Memory Inspector ===
        # MIGRATED FROM: lines 236-238
        elif msg_type == "refresh_memory_inspector":
            if 'memory' in self.inspectors and self.inspectors['memory']:
                self.inspectors['memory'].refresh_memories()
        
        # === Update Game Time ===
        # MIGRATED FROM: lines 240-241
        elif msg_type == "update_game_time":
            self.game_time_label.configure(text=f"🕐 {msg['new_time']}")
        
        # === Update Game Mode ===
        # MIGRATED FROM: lines 243-245
        elif msg_type == "update_game_mode":
            # CHANGED: self._get_mode_display → get_mode_display (ui_helpers)
            mode_text, mode_color = get_mode_display(msg['new_mode'])
            self.game_mode_label.configure(text=mode_text, text_color=mode_color)
        
        # === Tool Event (Legacy) ===
        # MIGRATED FROM: lines 247-250
        elif msg_type == "tool_event":
            logger.info(f"Tool Event: {msg['message']}")
            # Optionally display this in a specific debug area or log
        
        # === Unknown Message Type ===
        # MIGRATED FROM: lines 252-253
        else:
            logger.warning(f"Unknown UI message type: {msg_type}")
